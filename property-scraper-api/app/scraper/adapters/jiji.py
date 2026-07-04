"""
Dedicated adapter for Jiji Kenya (P5 — JS-rendered platform).

Jiji renders listings client-side and uses aggressive anti-bot protection.
This adapter uses Playwright to render the page and extract listing URLs
and detail data, including phone numbers behind a click-to-reveal gate.

NOTE: Requires `playwright install chromium` to be run first.
"""
import re
from datetime import datetime
from typing import Optional

from app.scraper.base import BaseAdapter, NormalizedListing
from app.scraper.contact import extract_contacts_from_html, reveal_via_playwright
from app.scraper.utils import absolute_url

LISTING_LINK_RE = re.compile(r"/real-estate/[a-z0-9-]+-\d+")


class JijiAdapter(BaseAdapter):
    def discover_listing_urls(self, max_pages: int) -> list[str]:
        urls: set[str] = set()
        for path in self.config.get("listing_paths", []):
            for page_num in range(1, max_pages + 1):
                page_url = absolute_url(self.base_url, path)
                if page_num > 1:
                    sep = "&" if "?" in page_url else "?"
                    page_url = f"{page_url}{sep}page={page_num}"

                import asyncio
                html = asyncio.run(reveal_via_playwright(
                    page_url,
                    {"type": "click_to_reveal", "selector": "body", "wait_timeout_ms": 5000},
                ))
                if not html:
                    break

                for match in LISTING_LINK_RE.finditer(html):
                    urls.add(absolute_url(self.base_url, match.group(0)))

        return list(urls)

    def parse_listing(self, url: str) -> Optional[NormalizedListing]:
        import asyncio

        gate_config = self.config.get("contact_gate", {
            "type": "click_to_reveal",
            "selector": ".show-number, .phone-btn",
            "wait_selector": ".phone-number",
            "use_playwright": True,
            "wait_timeout_ms": 5000,
        })

        html = asyncio.run(reveal_via_playwright(url, gate_config))
        if not html:
            return None

        contacts = extract_contacts_from_html(html, gate_config=gate_config)

        title = None
        price_amount = None
        location_text = None

        m = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
        if m:
            title = m.group(1).strip()

        m = re.search(r"KSh\s*([\d,]+)", html)
        if m:
            try:
                price_amount = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

        m = re.search(r"(Nairobi|Mombasa|Kisumu|Nakuru|Eldoret|Thika|Malindi|Kitale|Nyeri|Machakos)[^<]{0,100}", html)
        if m:
            location_text = m.group(0).strip()

        return NormalizedListing(
            platform_id=self.platform_id,
            platform_name=self.platform_name,
            source_url=url,
            title=title,
            price_amount=price_amount,
            price_currency="KES" if price_amount else None,
            location_text=location_text,
            phone_numbers=contacts["phone_numbers"],
            whatsapp_numbers=contacts["whatsapp_numbers"],
            emails=contacts["emails"],
            contact_reveal_method=contacts["contact_reveal_method"],
        )
