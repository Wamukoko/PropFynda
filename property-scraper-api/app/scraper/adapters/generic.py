"""
Generic adapter used by any platform in platforms.json that doesn't have a
dedicated adapter module.

Strategy:
1. Try to read schema.org JSON-LD structured data from the listing page.
2. Fall back to CSS selectors supplied in platforms.json under a "selectors" key.
3. In both paths, extract phone/WhatsApp/email contact data from the page HTML
   and from any configured contact_gate.
"""
import re
from datetime import datetime
from typing import Optional

from app.scraper.base import BaseAdapter, NormalizedListing
from app.scraper.contact import extract_contacts_from_html, reveal_via_playwright
from app.scraper.utils import get_soup, extract_json_ld, absolute_url

PRICE_NUM_RE = re.compile(r"[\d,]+(?:\.\d+)?")


class GenericAdapter(BaseAdapter):
    def discover_listing_urls(self, max_pages: int) -> list[str]:
        selectors = self.config.get("selectors", {})
        link_selector = selectors.get("listing_link", "a")
        href_pattern = selectors.get("listing_href_pattern")
        pattern = re.compile(href_pattern) if href_pattern else None

        urls: set[str] = set()
        for path in self.config.get("listing_paths", []):
            base_page_url = absolute_url(self.base_url, path)
            for page_num in range(1, max_pages + 1):
                page_url = self._paginate(base_page_url, page_num, selectors)
                soup = get_soup(page_url)
                if soup is None:
                    break
                found = 0
                for a in soup.select(link_selector):
                    href = a.get("href")
                    if not href:
                        continue
                    if pattern and not pattern.search(href):
                        continue
                    urls.add(absolute_url(self.base_url, href))
                    found += 1
                if found == 0:
                    break
        return list(urls)

    def parse_listing(self, url: str) -> Optional[NormalizedListing]:
        soup = get_soup(url)
        if soup is None:
            return None

        html = str(soup)
        gate_config = self.config.get("contact_gate")
        phone_patterns = self.config.get("phone_patterns")

        json_ld = extract_json_ld(soup)
        listing = self._from_json_ld(json_ld, url)
        if listing is None:
            listing = self._from_selectors(soup, url)
        if listing is None:
            return None

        # Contact extraction from HTML
        contacts = extract_contacts_from_html(html, gate_config=gate_config, phone_patterns=phone_patterns)

        # If no phones found but gate is configured, try Playwright
        if not contacts["phone_numbers"] and gate_config and gate_config.get("use_playwright"):
            import asyncio
            try:
                rendered = asyncio.run(reveal_via_playwright(url, gate_config))
                if rendered:
                    contacts = extract_contacts_from_html(rendered, gate_config=gate_config, phone_patterns=phone_patterns)
            except Exception:
                pass

        listing.phone_numbers = contacts["phone_numbers"]
        listing.whatsapp_numbers = contacts["whatsapp_numbers"]
        listing.emails = contacts["emails"]
        listing.contact_reveal_method = contacts["contact_reveal_method"]
        return listing

    # -- JSON-LD path -----------------------------------------------------
    def _from_json_ld(self, blocks: list[dict], url: str) -> Optional[NormalizedListing]:
        relevant_types = {
            "Product", "Offer", "House", "Apartment", "SingleFamilyResidence",
            "RealEstateListing", "Residence", "Place",
        }
        for block in blocks:
            block_type = block.get("@type")
            types = block_type if isinstance(block_type, list) else [block_type]
            if not types or not any(t in relevant_types for t in types):
                continue

            offers = block.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            address = block.get("address", {})
            location_text = None
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                ]
                location_text = ", ".join(p for p in parts if p) or None
            elif isinstance(address, str):
                location_text = address

            return NormalizedListing(
                platform_id=self.platform_id,
                platform_name=self.platform_name,
                source_url=url,
                title=block.get("name"),
                description=block.get("description"),
                price_amount=self._to_float(offers.get("price")) if isinstance(offers, dict) else None,
                price_currency=offers.get("priceCurrency") if isinstance(offers, dict) else None,
                location_text=location_text,
                agency_name=self._extract_seller_name(offers),
                date_posted=self._parse_date(block.get("datePosted") or block.get("dateCreated")),
            )
        return None

    @staticmethod
    def _extract_seller_name(offers: dict) -> Optional[str]:
        if not isinstance(offers, dict):
            return None
        seller = offers.get("seller") or offers.get("offeredBy")
        if isinstance(seller, dict):
            return seller.get("name")
        return None

    # -- CSS selector fallback path ----------------------------------------
    def _from_selectors(self, soup, url: str) -> Optional[NormalizedListing]:
        selectors = self.config.get("selectors", {})
        if not selectors:
            return None

        def text_of(key: str) -> Optional[str]:
            sel = selectors.get(key)
            if not sel:
                return None
            el = soup.select_one(sel)
            return el.get_text(strip=True) if el else None

        title = text_of("title")
        description = text_of("description")
        price_text = text_of("price")
        location_text = text_of("location")
        agency_name = text_of("agency_name")

        price_amount = None
        if price_text:
            m = PRICE_NUM_RE.search(price_text)
            price_amount = self._to_float(m.group(0)) if m else None

        if not any([title, description, price_text, location_text]):
            return None

        return NormalizedListing(
            platform_id=self.platform_id,
            platform_name=self.platform_name,
            source_url=url,
            title=title,
            description=description,
            price_amount=price_amount,
            location_text=location_text,
            agency_name=agency_name,
        )

    @staticmethod
    def _paginate(base_page_url: str, page_num: int, selectors: dict) -> str:
        if page_num == 1:
            return base_page_url
        param = selectors.get("page_param", "page")
        sep = "&" if "?" in base_page_url else "?"
        return f"{base_page_url}{sep}{param}={page_num}"

    @staticmethod
    def _to_float(raw) -> Optional[float]:
        if raw is None:
            return None
        try:
            cleaned = str(raw).replace(",", "").replace(" ", "")
            cleaned = re.sub(r"^[A-Za-z\s/]+", "", cleaned)
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _parse_date(raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %B %Y"):
            try:
                return datetime.strptime(raw[: len(fmt) + 5], fmt)
            except ValueError:
                continue
        return None
