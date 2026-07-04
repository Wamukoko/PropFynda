from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    platform_id: str
    platform_name: str
    source_url: str

    title: Optional[str] = None
    description: Optional[str] = None
    listing_type: Optional[str] = None
    property_type: Optional[str] = None

    price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    price_period: Optional[str] = None

    location_text: Optional[str] = None
    location: Optional[str] = None

    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_value: Optional[float] = None
    size_unit: Optional[str] = None

    agent_name: Optional[str] = None
    agency_name: Optional[str] = None
    agency_url: Optional[str] = None

    # Contact data
    phone_numbers: list[str] = Field(default_factory=list)
    whatsapp_numbers: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    contact_reveal_method: Optional[str] = None

    # Unified fields from kenya_property_listing_schema.json
    street_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vat_included: Optional[bool] = None
    floor_size: Optional[float] = None
    land_size: Optional[float] = None
    land_size_unit: Optional[str] = None
    parking_spaces: Optional[int] = None
    furnishing_status: Optional[str] = None

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
    agent_type: Optional[str] = None
    agent_verified: Optional[bool] = None

    # contact actions
    action_call: Optional[bool] = None
    action_sms_or_message: Optional[bool] = None
    action_in_platform_enquiry_form: Optional[bool] = None

    # images list
    images: list[str] = Field(default_factory=list)

    date_posted: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime
    duplicate_of_id: Optional[int] = None


class ContactOut(BaseModel):
    phone_numbers: list[str] = Field(default_factory=list)
    whatsapp_numbers: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    contact_reveal_method: Optional[str] = None


class PaginatedListings(BaseModel):
    items: list[ListingOut]
    total_count: int
    has_more: bool
    offset: int
    limit: int


class PlatformOut(BaseModel):
    id: str
    name: str
    base_url: str
    type: str
    active: bool
    scrape_priority: int
    notes: Optional[str] = None


class ScrapeTriggerResult(BaseModel):
    platform_id: str
    status: str
    listings_found: int
    listings_saved: int
    contacts_found: int = 0
    message: Optional[str] = None


class PlatformHealthOut(BaseModel):
    platform_id: str
    last_scrape_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    is_inactive: bool = False


class ContactStatsOut(BaseModel):
    platform_id: str
    total_listings: int
    listings_with_contacts: int
    avg_phones_per_listing: float
    reveal_method_breakdown: dict[str, int]


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    listing_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
