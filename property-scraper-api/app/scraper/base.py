import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class NormalizedListing:
    """The common schema every adapter must produce, regardless of source site."""

    platform_id: str
    platform_name: str
    source_url: str

    title: Optional[str] = None
    description: Optional[str] = None
    listing_type: Optional[str] = None       # "sale" | "rent"
    property_type: Optional[str] = None      # house, apartment, land, commercial...

    price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    price_period: Optional[str] = None       # "month" for rentals

    location_text: Optional[str] = None
    location: Optional[str] = None

    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_value: Optional[float] = None
    size_unit: Optional[str] = None

    agent_name: Optional[str] = None
    agency_name: Optional[str] = None
    agency_url: Optional[str] = None

    # Contact data — extracted from the source page
    phone_numbers: list[str] = field(default_factory=list)
    whatsapp_numbers: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    contact_reveal_method: Optional[str] = None  # "html_scan" | "click_gate" | "json_ld" | "none"

    date_posted: Optional[datetime] = None
    source_listing_id: Optional[str] = None

    # Unified fields from kenya_property_listing_schema.json
    street_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vat_included: Optional[bool] = None
    floor_size: Optional[float] = None
    land_size: Optional[float] = None
    land_size_unit: Optional[str] = None
    parking_spaces: Optional[int] = None
    furnishing_status: Optional[str] = None  # "furnished" | "unfurnished" | "semi_furnished"
    
    # occupancy_extras fields
    serviced: Optional[bool] = None
    shared: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_flatlet: Optional[bool] = None
    security_estate_or_cluster: Optional[bool] = None
    on_show: Optional[bool] = None
    on_auction: Optional[bool] = None
    is_repossessed: Optional[bool] = None
    is_retirement_property: Optional[bool] = None

    # agent extra fields
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None  # "individual_agent" | "agency" | "developer" | "private_owner"
    agent_verified: Optional[bool] = None

    # contact actions
    action_call: Optional[bool] = None
    action_sms_or_message: Optional[bool] = None
    action_in_platform_enquiry_form: Optional[bool] = None

    # images list
    images: list[str] = field(default_factory=list)

    extra: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """
    One adapter per platform. Implementations should:
    - only use app.scraper.utils.fetch/get_soup (never raw requests.get) so
      robots.txt checks and rate limiting are always applied
    - be defensive: a missing field should become None, not an exception
    - extract contact info (phone/WhatsApp/email) from the page via
      contact.py utilities, including click-gate reveal if configured
    """

    platform_id: str
    platform_name: str
    base_url: str

    def __init__(self, platform_config: dict):
        self.config = platform_config
        self.platform_id = platform_config["id"]
        self.platform_name = platform_config["name"]
        self.base_url = platform_config["base_url"]

    @abstractmethod
    def discover_listing_urls(self, max_pages: int) -> list[str]:
        """Return a list of individual listing detail-page URLs to scrape."""
        raise NotImplementedError

    @abstractmethod
    def parse_listing(self, url: str) -> Optional[NormalizedListing]:
        """Fetch and parse a single listing detail page into NormalizedListing."""
        raise NotImplementedError

    @staticmethod
    def _infer_from_title(listing: NormalizedListing) -> None:
        title = listing.title or ''
        if listing.bedrooms is None:
            m = re.search(r'(\d+)\s*[Bb]ed', title)
            if m:
                listing.bedrooms = int(m.group(1))

    def run(self, max_pages: int, max_listings: int) -> list[NormalizedListing]:
        urls = self.discover_listing_urls(max_pages)[:max_listings]
        results = []
        for url in urls:
            try:
                listing = self.parse_listing(url)
            except Exception:  # noqa: BLE001
                listing = None
            if listing is not None:
                self._infer_from_title(listing)
                results.append(listing)
        return results
