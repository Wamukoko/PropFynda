import csv
import io
import logging
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy import String, asc, cast, desc, func
from sqlalchemy.orm import Session

from app.chat import chat as chat_agent
from app.database import get_db, init_db
from app.models import Listing, PlatformHealth, ScrapeRun
from app.scheduler import start_scheduler, stop_scheduler
from app.scraper.registry import get_platform, load_platforms
from app.scraper.runner import scrape_platform, scrape_all_active_platforms
from app.schemas import (
    ChatRequest, ChatResponse, ContactOut, ContactStatsOut, ListingOut,
    PaginatedListings, PlatformHealthOut, PlatformOut, ScrapeTriggerResult,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Kenya Property Listings API",
    description="Aggregates and normalizes property listings scraped from multiple Kenyan real estate platforms.",
    version="0.2.0",
)


@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/")
def root():
    return {
        "title": "Kenya Property Listings API",
        "version": "0.2.0",
        "endpoints": {
            "health": "GET /health",
            "platforms": "GET /platforms",
            "platform_health": "GET /platforms/{id}/health",
            "platform_contact_stats": "GET /platforms/{id}/contacts/stats",
            "listings": "GET /listings",
            "listing_detail": "GET /listings/{id}",
            "listing_contacts": "GET /listings/{id}/contacts",
            "listings_csv": "GET /listings.csv",
            "search": "GET /search",
            "chat": "POST /chat",
            "scrape_one": "POST /scrape/{platform_id}",
            "scrape_all": "POST /scrape",
        },
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Platforms ──────────────────────────────────────────────────────────

@app.get("/platforms", response_model=list[PlatformOut])
def get_platforms():
    return [
        PlatformOut(
            id=p["id"], name=p["name"], base_url=p["base_url"], type=p["type"],
            active=p.get("active", True), scrape_priority=p.get("scrape_priority", 99),
            notes=p.get("notes"),
        )
        for p in load_platforms()
    ]


@app.get("/platforms/{platform_id}/health", response_model=PlatformHealthOut)
def get_platform_health(platform_id: str, db: Session = Depends(get_db)):
    if get_platform(platform_id) is None:
        raise HTTPException(status_code=404, detail="Unknown platform_id")
    health = db.query(PlatformHealth).filter(PlatformHealth.platform_id == platform_id).first()
    if health is None:
        return PlatformHealthOut(platform_id=platform_id, is_inactive=False)
    return PlatformHealthOut(
        platform_id=health.platform_id,
        last_scrape_at=health.last_scrape_at,
        last_error_at=health.last_error_at,
        last_error=health.last_error,
        consecutive_failures=health.consecutive_failures or 0,
        is_inactive=health.is_inactive or False,
    )


@app.get("/platforms/{platform_id}/contacts/stats", response_model=ContactStatsOut)
def get_platform_contact_stats(platform_id: str, db: Session = Depends(get_db)):
    if get_platform(platform_id) is None:
        raise HTTPException(status_code=404, detail="Unknown platform_id")

    total = db.query(func.count(Listing.id)).filter(Listing.platform_id == platform_id).scalar() or 0

    with_contacts = (
        db.query(func.count(Listing.id))
        .filter(
            Listing.platform_id == platform_id,
            Listing.phone_numbers.isnot(None),
            func.json_array_length(Listing.phone_numbers) > 0,
        )
        .scalar() or 0
    )

    avg_phones = 0.0
    if total > 0:
        phone_count = (
            db.query(func.coalesce(func.json_array_length(Listing.phone_numbers), 0))
            .filter(Listing.platform_id == platform_id)
            .all()
        )
        total_phones = sum(r[0] for r in phone_count)
        avg_phones = round(total_phones / total, 2)

    breakdown_rows = (
        db.query(Listing.contact_reveal_method, func.count(Listing.id))
        .filter(Listing.platform_id == platform_id)
        .group_by(Listing.contact_reveal_method)
        .all()
    )
    breakdown = {row[0] or "none": row[1] for row in breakdown_rows}

    return ContactStatsOut(
        platform_id=platform_id,
        total_listings=total,
        listings_with_contacts=with_contacts,
        avg_phones_per_listing=avg_phones,
        reveal_method_breakdown=breakdown,
    )


# ── Listings ───────────────────────────────────────────────────────────

@app.get("/listings", response_model=PaginatedListings)
def get_listings(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None, description="Filter by platform id"),
    listing_type: Optional[str] = Query(None, description="'sale' or 'rent'"),
    location: Optional[str] = Query(None, description="Filter by location (area/suburb e.g. Parklands, Westlands)"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_bedrooms: Optional[int] = Query(None, description="Minimum bedroom count"),
    has_phone: Optional[bool] = Query(None, description="Only listings with phone numbers"),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc)$"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    q = db.query(Listing)

    if platform:
        q = q.filter(Listing.platform_id == platform)
    if listing_type:
        q = q.filter(Listing.listing_type == listing_type)
    if location:
        q = q.filter(Listing.location.ilike(f"%{location}%"))
    if min_price is not None:
        q = q.filter(Listing.price_amount >= min_price)
    if max_price is not None:
        q = q.filter(Listing.price_amount <= max_price)
    if min_bedrooms is not None:
        q = q.filter(Listing.bedrooms >= min_bedrooms)
    if has_phone is True:
        q = q.filter(
            Listing.phone_numbers.isnot(None),
            func.json_array_length(Listing.phone_numbers) > 0,
        )
    elif has_phone is False:
        q = q.filter(
            (Listing.phone_numbers.is_(None)) |
            (func.json_array_length(Listing.phone_numbers) == 0)
        )

    total_count = q.count()

    if sort == "newest":
        q = q.order_by(desc(Listing.date_posted), desc(Listing.first_seen_at))
    elif sort == "price_asc":
        q = q.order_by(asc(Listing.price_amount))
    elif sort == "price_desc":
        q = q.order_by(desc(Listing.price_amount))

    items = q.offset(offset).limit(limit).all()
    has_more = (offset + limit) < total_count

    return PaginatedListings(
        items=[ListingOut.model_validate(item) for item in items],
        total_count=total_count,
        has_more=has_more,
        offset=offset,
        limit=limit,
    )


@app.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@app.get("/listings/{listing_id}/contacts", response_model=ContactOut)
def get_listing_contacts(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return ContactOut(
        phone_numbers=listing.phone_numbers or [],
        whatsapp_numbers=listing.whatsapp_numbers or [],
        emails=listing.emails or [],
        contact_reveal_method=listing.contact_reveal_method,
    )


@app.get("/listings.csv")
def get_listings_csv(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_bedrooms: Optional[int] = Query(None),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc)$"),
    limit: int = Query(500, le=5000),
):
    q = db.query(Listing)
    if platform:
        q = q.filter(Listing.platform_id == platform)
    if listing_type:
        q = q.filter(Listing.listing_type == listing_type)
    if location:
        q = q.filter(Listing.location.ilike(f"%{location}%"))
    if min_bedrooms is not None:
        q = q.filter(Listing.bedrooms >= min_bedrooms)
    if sort == "newest":
        q = q.order_by(desc(Listing.date_posted), desc(Listing.first_seen_at))
    elif sort == "price_asc":
        q = q.order_by(asc(Listing.price_amount))
    elif sort == "price_desc":
        q = q.order_by(desc(Listing.price_amount))

    listings = q.limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "platform_id", "platform_name", "title", "description",
        "listing_type", "property_type", "price_amount", "price_currency",
        "price_period", "location_text", "location", "bedrooms", "bathrooms",
        "size_value", "size_unit", "agent_name", "agency_name", "agency_url",
        "phone_numbers", "whatsapp_numbers", "emails", "contact_reveal_method",
        "source_url", "date_posted", "first_seen_at", "last_seen_at",
    ])
    for l in listings:
        writer.writerow([
            l.id, l.platform_id, l.platform_name, l.title, l.description,
            l.listing_type, l.property_type, l.price_amount, l.price_currency,
            l.price_period, l.location_text, l.location, l.bedrooms, l.bathrooms,
            l.size_value, l.size_unit, l.agent_name, l.agency_name, l.agency_url,
            "; ".join(l.phone_numbers) if l.phone_numbers else "",
            "; ".join(l.whatsapp_numbers) if l.whatsapp_numbers else "",
            "; ".join(l.emails) if l.emails else "",
            l.contact_reveal_method,
            l.source_url,
            l.date_posted.isoformat() if l.date_posted else "",
            l.first_seen_at.isoformat() if l.first_seen_at else "",
            l.last_seen_at.isoformat() if l.last_seen_at else "",
        ])

    return Response(content=output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=listings.csv"})


@app.get("/search")
def search_listings(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Free-text search in title/description"),
    phone: Optional[str] = Query(None, description="Search by phone number"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(Listing)

    if q:
        like = f"%{q}%"
        query = query.filter(
            Listing.title.ilike(like) | Listing.description.ilike(like) | Listing.location_text.ilike(like)
        )
    if phone:
        like = f"%{phone}%"
        query = query.filter(
            cast(Listing.phone_numbers, String).ilike(like) |
            cast(Listing.whatsapp_numbers, String).ilike(like)
        )

    total_count = query.count()
    items = query.order_by(desc(Listing.date_posted), desc(Listing.first_seen_at)) \
        .offset(offset).limit(limit).all()
    has_more = (offset + limit) < total_count

    return PaginatedListings(
        items=[ListingOut.model_validate(item) for item in items],
        total_count=total_count,
        has_more=has_more,
        offset=offset,
        limit=limit,
    )


# ── AI Chat (Agent Eve) ───────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def agent_eve_chat(req: ChatRequest, db: Session = Depends(get_db)):
    listing_context = None
    if req.listing_id:
        listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
        if listing:
            listing_context = (
                f"Title: {listing.title}\n"
                f"Type: {listing.listing_type}\n"
                f"Price: {listing.price_amount} {listing.price_currency or ''} {listing.price_period or ''}\n"
                f"Location: {listing.location_text or ''}, {listing.location or ''}\n"
                f"Bedrooms: {listing.bedrooms}, Bathrooms: {listing.bathrooms}\n"
                f"Size: {listing.size_value} {listing.size_unit or ''}\n"
                f"Agent: {listing.agent_name or ''} ({listing.agency_name or ''})\n"
                f"Description: {listing.description or ''}"
            )

    reply = chat_agent(
        messages=[{"role": m.role, "content": m.content} for m in req.messages],
        listing_context=listing_context,
    )
    return ChatResponse(reply=reply)


# ── Scrape triggers ────────────────────────────────────────────────────

@app.post("/scrape/{platform_id}", response_model=ScrapeTriggerResult)
def trigger_scrape(platform_id: str, db: Session = Depends(get_db)):
    if get_platform(platform_id) is None:
        raise HTTPException(status_code=404, detail="Unknown platform_id")
    result = scrape_platform(db, platform_id)
    return ScrapeTriggerResult(**result)


@app.post("/scrape")
def trigger_scrape_all(background_tasks: BackgroundTasks):
    def _job():
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            scrape_all_active_platforms(db)
        finally:
            db.close()

    background_tasks.add_task(_job)
    return {"status": "started", "message": "Scrape running in background. Poll /listings shortly."}
