"""
Reference adapter for BuyRentKenya.

Field extraction strategy, in order of reliability:
1. <meta property="og:*"> and <meta name="description"> tags in <head>
2. Labeled fields in the page body via regex over visible text.
3. The "Contact details" block for agency name.
4. Contact data: scans raw HTML for phone/WhatsApp/email patterns, and
   if a contact_gate is configured in platforms.json, uses Playwright to
   click the "View Number" button and extract the revealed number.
"""
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from app.scraper.base import BaseAdapter, NormalizedListing
from app.scraper.contact import extract_contacts_from_html, reveal_via_playwright
from app.scraper.utils import get_soup, absolute_url

LISTING_HREF_RE = re.compile(r"^/listings/[a-z0-9-]+-\d+$")

BEDROOMS_RE = re.compile(r"Bedrooms:\s*(\d+)")
BATHROOMS_RE = re.compile(r"Bathrooms:\s*(\d+)")
SIZE_RE = re.compile(r"Size:\s*([\d,.]+)\s*(m²|sqft|acres?)", re.IGNORECASE)
CREATED_RE = re.compile(r"Created At:\s*(\d{2} \w+ \d{4})")
PRICE_RE = re.compile(r"KSh\s*([\d,]+)(?:\s*/\s*(month|year))?", re.IGNORECASE)


class BuyRentKenyaAdapter(BaseAdapter):
    def discover_listing_urls(self, max_pages: int) -> list[str]:
        urls: set[str] = set()
        for path in self.config.get("listing_paths", []):
            for page_num in range(1, max_pages + 1):
                sep = "&" if "?" in path else "?"
                page_url = urljoin(self.base_url, path) + (f"{sep}page={page_num}" if page_num > 1 else "")
                soup = get_soup(page_url)
                if soup is None:
                    break
                found_on_page = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if LISTING_HREF_RE.match(href):
                        urls.add(absolute_url(self.base_url, href))
                        found_on_page += 1
                if found_on_page == 0:
                    break
        return list(urls)

    def parse_listing(self, url: str) -> Optional[NormalizedListing]:
        soup = get_soup(url)
        if soup is None:
            return None

        text = soup.get_text(separator="\n")

        title = self._meta(soup, "og:title") or (soup.title.string if soup.title else None)
        description = self._meta(soup, "og:description")

        bedrooms = self._first_int(BEDROOMS_RE, text)
        bathrooms = self._first_int(BATHROOMS_RE, text)

        size_value, size_unit = None, None
        size_match = SIZE_RE.search(text)
        if size_match:
            size_value = self._to_float(size_match.group(1))
            size_unit = size_match.group(2)

        date_posted = None
        created_match = CREATED_RE.search(text)
        if created_match:
            try:
                date_posted = datetime.strptime(created_match.group(1), "%d %B %Y")
            except ValueError:
                pass

        price_amount, price_period = None, None
        price_match = PRICE_RE.search(text)
        if price_match:
            price_amount = self._to_float(price_match.group(1))
            price_period = price_match.group(2)

        listing_type = "rent" if "-for-rent-" in url or price_period else ("sale" if "-for-sale-" in url else None)

        location_text = None
        loc_match = re.search(r"\n([A-Za-z .'-]+, [A-Za-z .'-]+, [A-Za-z .'-]+)\n", text)
        if loc_match:
            location_text = loc_match.group(1).strip()

        agency_name = None
        contact_idx = text.find("Contact details")
        if contact_idx != -1:
            tail = text[contact_idx: contact_idx + 400].splitlines()
            candidates = [line.strip() for line in tail if line.strip()]
            for line in candidates[1:]:
                if line and not line.startswith("+") and "View Number" not in line and "Message" not in line:
                    agency_name = line
                    break

        source_listing_id = url.rstrip("/").split("-")[-1]

        # ── Contact extraction ───────────────────────────────────────
        html = str(soup)
        gate_config = self.config.get("contact_gate")

        contacts = extract_contacts_from_html(html, gate_config=gate_config)

        # If no phones found from HTML scan but gate is configured, try Playwright
        if not contacts["phone_numbers"] and gate_config and gate_config.get("use_playwright"):
            import asyncio
            try:
                rendered = asyncio.run(reveal_via_playwright(url, gate_config))
                if rendered:
                    contacts = extract_contacts_from_html(rendered, gate_config=gate_config)
            except Exception as exc:
                pass

        return NormalizedListing(
            platform_id=self.platform_id,
            platform_name=self.platform_name,
            source_url=url,
            title=title.strip() if title else None,
            description=description.strip() if description else None,
            listing_type=listing_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            size_value=size_value,
            size_unit=size_unit,
            price_amount=price_amount,
            price_currency="KES" if price_amount is not None else None,
            price_period=price_period,
            location_text=location_text,
            agency_name=agency_name,
            date_posted=date_posted,
            source_listing_id=source_listing_id,
            phone_numbers=contacts["phone_numbers"],
            whatsapp_numbers=contacts["whatsapp_numbers"],
            emails=contacts["emails"],
            contact_reveal_method=contacts["contact_reveal_method"],
        )

    @staticmethod
    def _meta(soup, prop: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return tag["content"] if tag and tag.get("content") else None

    @staticmethod
    def _first_int(pattern: re.Pattern, text: str) -> Optional[int]:
        m = pattern.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def _to_float(raw: str) -> Optional[float]:
        try:
            return float(raw.replace(",", ""))
        except (ValueError, AttributeError):
            return None
