import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import MAX_LISTINGS_PER_PLATFORM_PER_RUN, MAX_PAGES_PER_PLATFORM_PER_RUN
from app.models import Listing, ScrapeRun, PlatformHealth
from app.scraper.registry import build_adapter, get_platform

logger = logging.getLogger("scraper")

CONTACT_FIELDS = ["phone_numbers", "whatsapp_numbers", "emails", "contact_reveal_method"]

LISTING_FIELDS = [
    "title", "description", "listing_type", "property_type",
    "price_amount", "price_currency", "price_period",
    "location_text", "location", "bedrooms", "bathrooms",
    "size_value", "size_unit", "agent_name", "agency_name",
    "agency_url", "date_posted", "source_listing_id",
    # Unified fields from kenya_property_listing_schema.json
    "street_address", "latitude", "longitude", "vat_included",
    "floor_size", "land_size", "land_size_unit", "parking_spaces",
    "furnishing_status", "serviced", "shared", "pet_friendly",
    "has_garden", "has_pool", "has_flatlet", "security_estate_or_cluster",
    "on_show", "on_auction", "is_repossessed", "is_retirement_property",
    "agent_id", "agent_type", "agent_verified",
    "action_call", "action_sms_or_message", "action_in_platform_enquiry_form",
    "images",
] + CONTACT_FIELDS


def _save_scrape_run(db: Session, platform_id: str, status: str,
                     listings_found: int, listings_saved: int,
                     contacts_found: int = 0, error: str = None) -> ScrapeRun:
    run = ScrapeRun(
        platform_id=platform_id,
        finished_at=datetime.utcnow(),
        status=status,
        listings_found=listings_found,
        listings_saved=listings_saved,
        contacts_found=contacts_found,
        error=error,
    )
    db.add(run)
    db.flush()

    health = db.query(PlatformHealth).filter(PlatformHealth.platform_id == platform_id).first()
    if health is None:
        health = PlatformHealth(platform_id=platform_id)
        db.add(health)
        db.flush()

    if status == "ok":
        health.last_scrape_at = datetime.utcnow()
        health.consecutive_failures = 0
        health.is_inactive = False
    elif status == "error":
        health.last_error_at = datetime.utcnow()
        health.last_error = error
        health.consecutive_failures = (health.consecutive_failures or 0) + 1
        if health.consecutive_failures >= 3:
            health.is_inactive = True
            logger.warning("Platform %s marked inactive after %d consecutive failures",
                           platform_id, health.consecutive_failures)
    db.flush()
    return run


def scrape_platform(db: Session, platform_id: str) -> dict:
    platform_config = get_platform(platform_id)
    if platform_config is None:
        _save_scrape_run(db, platform_id, "error", 0, 0, error="unknown platform_id")
        db.commit()
        return {"platform_id": platform_id, "status": "error", "listings_found": 0,
                "listings_saved": 0, "contacts_found": 0, "message": "unknown platform_id"}

    if not platform_config.get("active", True):
        _save_scrape_run(db, platform_id, "skipped", 0, 0)
        db.commit()
        return {"platform_id": platform_id, "status": "skipped", "listings_found": 0,
                "listings_saved": 0, "contacts_found": 0, "message": "platform marked inactive"}

    health = db.query(PlatformHealth).filter(PlatformHealth.platform_id == platform_id).first()
    if health and health.is_inactive:
        logger.info("Skipping %s — platform is inactive due to repeated failures", platform_id)
        return {"platform_id": platform_id, "status": "skipped", "listings_found": 0,
                "listings_saved": 0, "contacts_found": 0, "message": "platform inactive (circuit breaker)"}

    adapter = build_adapter(platform_config)

    try:
        normalized_listings = adapter.run(
            max_pages=MAX_PAGES_PER_PLATFORM_PER_RUN,
            max_listings=MAX_LISTINGS_PER_PLATFORM_PER_RUN,
        )
    except Exception as exc:
        logger.exception("Adapter failed for %s", platform_id)
        _save_scrape_run(db, platform_id, "error", 0, 0, error=str(exc))
        db.commit()
        return {"platform_id": platform_id, "status": "error", "listings_found": 0,
                "listings_saved": 0, "contacts_found": 0, "message": str(exc)}

    saved = 0
    contacts_found = 0
    for nl in normalized_listings:
        existing = (
            db.query(Listing)
            .filter(Listing.platform_id == nl.platform_id, Listing.source_url == nl.source_url)
            .first()
        )
        if existing:
            for field in LISTING_FIELDS:
                setattr(existing, field, getattr(nl, field))
            existing.last_seen_at = datetime.utcnow()
        else:
            kwargs = {field: getattr(nl, field) for field in LISTING_FIELDS}
            kwargs.update(
                platform_id=nl.platform_id,
                platform_name=nl.platform_name,
                source_url=nl.source_url,
            )
            db.add(Listing(**kwargs))
        saved += 1
        if nl.phone_numbers or nl.whatsapp_numbers or nl.emails:
            contacts_found += 1

    db.flush()
    _save_scrape_run(db, platform_id, "ok", len(normalized_listings), saved, contacts_found)
    db.commit()

    return {
        "platform_id": platform_id,
        "status": "ok",
        "listings_found": len(normalized_listings),
        "listings_saved": saved,
        "contacts_found": contacts_found,
        "message": None,
    }


def scrape_all_active_platforms(db: Session) -> list[dict]:
    from app.scraper.registry import load_platforms
    results = []
    for platform in load_platforms():
        if platform.get("active", True):
            results.append(scrape_platform(db, platform["id"]))
    return results
