from datetime import datetime

from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, Text, JSON, UniqueConstraint

from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)

    # Source identity
    platform_id = Column(String(64), index=True, nullable=False)
    platform_name = Column(String(128), nullable=False)
    source_listing_id = Column(String(256), index=True, nullable=True)
    source_url = Column(String(1024), nullable=False)

    # Core listing fields
    title = Column(String(512), nullable=True)
    description = Column(Text, nullable=True)
    listing_type = Column(String(32), nullable=True)
    property_type = Column(String(64), nullable=True)

    price_amount = Column(Float, nullable=True)
    price_currency = Column(String(8), nullable=True)
    price_period = Column(String(32), nullable=True)

    location_text = Column(String(512), nullable=True)
    location = Column(String(128), nullable=True)

    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    size_value = Column(Float, nullable=True)
    size_unit = Column(String(16), nullable=True)

    # Agent / agency
    agent_name = Column(String(256), nullable=True)
    agency_name = Column(String(256), nullable=True)
    agency_url = Column(String(1024), nullable=True)

    # Contact data — extracted from the source page
    phone_numbers = Column(JSON, nullable=True)
    whatsapp_numbers = Column(JSON, nullable=True)
    emails = Column(JSON, nullable=True)
    contact_reveal_method = Column(String(32), nullable=True)

    # Unified fields from kenya_property_listing_schema.json
    street_address = Column(String(512), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    vat_included = Column(Boolean, nullable=True)
    floor_size = Column(Float, nullable=True)
    land_size = Column(Float, nullable=True)
    land_size_unit = Column(String(16), nullable=True)
    parking_spaces = Column(Integer, nullable=True)
    furnishing_status = Column(String(32), nullable=True)

    # occupancy_extras fields
    serviced = Column(Boolean, nullable=True)
    shared = Column(Boolean, nullable=True)
    pet_friendly = Column(Boolean, nullable=True)
    has_garden = Column(Boolean, nullable=True)
    has_pool = Column(Boolean, nullable=True)
    has_flatlet = Column(Boolean, nullable=True)
    security_estate_or_cluster = Column(Boolean, nullable=True)
    on_show = Column(Boolean, nullable=True)
    on_auction = Column(Boolean, nullable=True)
    is_repossessed = Column(Boolean, nullable=True)
    is_retirement_property = Column(Boolean, nullable=True)

    # agent extra fields
    agent_id = Column(String(256), nullable=True)
    agent_type = Column(String(64), nullable=True)
    agent_verified = Column(Boolean, nullable=True)

    # contact actions
    action_call = Column(Boolean, nullable=True)
    action_sms_or_message = Column(Boolean, nullable=True)
    action_in_platform_enquiry_form = Column(Boolean, nullable=True)

    # images list
    images = Column(JSON, nullable=True)

    date_posted = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Deduplication
    duplicate_of_id = Column(Integer, nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("platform_id", "source_url", name="uq_platform_source_url"),
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(String(64), index=True, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False)  # "running" | "ok" | "error" | "skipped"
    listings_found = Column(Integer, default=0)
    listings_saved = Column(Integer, default=0)
    contacts_found = Column(Integer, default=0)
    error = Column(Text, nullable=True)


class PlatformHealth(Base):
    __tablename__ = "platform_health"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(String(64), unique=True, index=True, nullable=False)
    last_scrape_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    is_inactive = Column(Boolean, default=False)
