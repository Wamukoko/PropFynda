"""
Data quality utilities: location normalizer, deduplication hints, stale detection.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Listing

# ── Kenya location/area map (area/suburb -> broader area) ──────────────

LOCATION_MAP: dict[str, str] = {
    # Nairobi areas
    "nairobi": "Nairobi",
    "nairobi city": "Nairobi",
    "nairobi west": "Nairobi",
    "nairobi east": "Nairobi",
    "nairobi north": "Nairobi",
    "nairobi south": "Nairobi",
    "dagoretti": "Nairobi",
    "embakasi": "Nairobi",
    "kasarani": "Nairobi",
    "langata": "Nairobi",
    "kamukunji": "Nairobi",
    "starehe": "Nairobi",
    "westlands": "Nairobi",
    "parklands": "Nairobi",
    "kilimani": "Nairobi",
    "kileleshwa": "Nairobi",
    "lavington": "Nairobi",
    "hurlingham": "Nairobi",
    "upper hill": "Nairobi",
    "south b": "Nairobi",
    "south c": "Nairobi",
    "madaraka": "Nairobi",
    "ngara": "Nairobi",
    "pipeline": "Nairobi",
    "donholm": "Nairobi",
    "buruburu": "Nairobi",
    "komarock": "Nairobi",
    "tassia": "Nairobi",
    "runda": "Nairobi",
    "karen": "Nairobi",
    "langata": "Nairobi",
    "nyayo": "Nairobi",
    "highridge": "Nairobi",
    "spring valley": "Nairobi",
    "riverside": "Nairobi",
    "kipande": "Nairobi",
    "muthaiga": "Nairobi",
    "gigiri": "Nairobi",
    "rosemead": "Nairobi",
    "imara daima": "Nairobi",
    "uthiru": "Nairobi",
    "waithaka": "Nairobi",
    "kawangware": "Nairobi",
    "ruaka": "Nairobi",
    # Coastal areas
    "mombasa": "Mombasa",
    "mombasa county": "Mombasa",
    "malindi": "Kilifi",
    "kilifi": "Kilifi",
    "kilifi county": "Kilifi",
    "lamu": "Lamu",
    "lamu county": "Lamu",
    "diani": "Kwale",
    "ukunda": "Kwale",
    "watamu": "Kilifi",
    # Rift Valley areas
    "nakuru": "Nakuru",
    "nakuru county": "Nakuru",
    "naivasha": "Nakuru",
    "eldoret": "Uasin Gishu",
    "uasin gishu": "Uasin Gishu",
    "nanyuki": "Laikipia",
    "laikipia": "Laikipia",
    "kitale": "Trans Nzoia",
    "trans nzoia": "Trans Nzoia",
    "kericho": "Kericho",
    "kericho county": "Kericho",
    "narok": "Narok",
    "narok county": "Narok",
    "baringo": "Baringo",
    "baringo county": "Baringo",
    # Western areas
    "kisumu": "Kisumu",
    "kisumu county": "Kisumu",
    "kakamega": "Kakamega",
    "kakamega county": "Kakamega",
    "kisii": "Kisii",
    "kisii county": "Kisii",
    "busia": "Busia",
    "busia county": "Busia",
    "bungoma": "Bungoma",
    "bungoma county": "Bungoma",
    "siaya": "Siaya",
    "siaya county": "Siaya",
    "homabay": "Homa Bay",
    "homa bay": "Homa Bay",
    "migori": "Migori",
    "migori county": "Migori",
    "nyamira": "Nyamira",
    "nyamira county": "Nyamira",
    # Central areas
    "kiambu": "Kiambu",
    "kiambu county": "Kiambu",
    "ruiru": "Kiambu",
    "thika": "Kiambu",
    "juja": "Kiambu",
    "kikuyu": "Kiambu",
    "limuru": "Kiambu",
    "muranga": "Murang'a",
    "murang'a": "Murang'a",
    "nyeri": "Nyeri",
    "nyeri county": "Nyeri",
    "kirinyaga": "Kirinyaga",
    "kirinyaga county": "Kirinyaga",
    "nyandarua": "Nyandarua",
    "nyandarua county": "Nyandarua",
    # Eastern areas
    "machakos": "Machakos",
    "machakos county": "Machakos",
    "athiriver": "Machakos",
    "mavoko": "Machakos",
    "meru": "Meru",
    "meru county": "Meru",
    "embu": "Embu",
    "embu county": "Embu",
    "kitui": "Kitui",
    "kitui county": "Kitui",
    "makueni": "Makueni",
    "makueni county": "Makueni",
    "tharaka nithi": "Tharaka Nithi",
    "tharaka": "Tharaka Nithi",
    # Rift Valley / North
    "kajiado": "Kajiado",
    "kajiado county": "Kajiado",
    "ngong": "Kajiado",
    "kitengela": "Kajiado",
    "ongata rongai": "Kajiado",
    "kajiado west": "Kajiado",
    "kajiado north": "Kajiado",
    "kajiado east": "Kajiado",
    "kajiado central": "Kajiado",
    "turkana": "Turkana",
    "turkana county": "Turkana",
    "samburu": "Samburu",
    "samburu county": "Samburu",
    "isiolo": "Isiolo",
    "isiolo county": "Isiolo",
    "garissa": "Garissa",
    "garissa county": "Garissa",
    "wajir": "Wajir",
    "wajir county": "Wajir",
    "mandera": "Mandera",
    "mandera county": "Mandera",
    "marsabit": "Marsabit",
    "marsabit county": "Marsabit",
    # Other
    "tana river": "Tana River",
    "tana river county": "Tana River",
    "taita taveta": "Taita Taveta",
    "taveta": "Taita Taveta",
    "voi": "Taita Taveta",
    "west pokot": "West Pokot",
    "pokot": "West Pokot",
    "elgeyo marakwet": "Elgeyo Marakwet",
    "marakwet": "Elgeyo Marakwet",
    "it": "Elgeyo Marakwet",
    "nandi": "Nandi",
    "nandi county": "Nandi",
}

# Extract town/area names in location text for mapping
AREA_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(LOCATION_MAP.keys(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def resolve_location(location_text: Optional[str]) -> Optional[str]:
    """Map free-text location to a canonical area name.

    Uses a lookup of known towns/suburbs/areas mapped to their broader area.
    """
    if not location_text:
        return None

    match = AREA_PATTERN.search(location_text.lower())
    if match:
        return LOCATION_MAP[match.group(1).lower()]
    return None


def normalize_location_fields(db: Session, platform_id: Optional[str] = None):
    """Backfill location for listings that have location_text but no location set."""
    q = db.query(Listing).filter(
        Listing.location.is_(None),
        Listing.location_text.isnot(None),
    )
    if platform_id:
        q = q.filter(Listing.platform_id == platform_id)

    updated = 0
    for listing in q.all():
        loc = resolve_location(listing.location_text)
        if loc:
            listing.location = loc
            updated += 1

    if updated:
        db.commit()
    return updated


# ── Stale detection ────────────────────────────────────────────────────

STALE_DAYS = 30


def is_stale(listing: Listing, max_age_days: int = STALE_DAYS) -> bool:
    """A listing is stale if it hasn't been seen in max_age_days."""
    if listing.last_seen_at is None:
        return True
    return (datetime.utcnow() - listing.last_seen_at) > timedelta(days=max_age_days)


def get_stale_listings(db: Session, max_age_days: int = STALE_DAYS) -> list[Listing]:
    """Return listings that haven't been seen recently."""
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    return db.query(Listing).filter(Listing.last_seen_at < cutoff).all()


# ── Deduplication ──────────────────────────────────────────────────────

DEDUP_THRESHOLD = 0.85


def find_duplicates(
    db: Session,
    platform_id: Optional[str] = None,
) -> list[tuple[Listing, Listing]]:
    """Find near-duplicate listings (same price, same bedrooms, similar title).

    Returns pairs of (original, duplicate) where duplicate should be
    marked with duplicate_of_id = original.id.
    """
    from difflib import SequenceMatcher

    q = db.query(Listing).filter(
        Listing.price_amount.isnot(None),
        Listing.bedrooms.isnot(None),
        Listing.title.isnot(None),
    )
    if platform_id:
        q = q.filter(Listing.platform_id == platform_id)

    listings = q.order_by(Listing.price_amount, Listing.bedrooms).all()

    pairs: list[tuple[Listing, Listing]] = []
    for i in range(len(listings)):
        for j in range(i + 1, len(listings)):
            a, b = listings[i], listings[j]
            if a.id == b.id:
                continue
            if a.duplicate_of_id == b.id or b.duplicate_of_id == a.id:
                continue
            if (a.price_amount == b.price_amount and a.bedrooms == b.bedrooms):
                ratio = SequenceMatcher(
                    None,
                    (a.title or "").lower(),
                    (b.title or "").lower(),
                ).ratio()
                if ratio >= DEDUP_THRESHOLD:
                    pairs.append((a, b))

    return pairs


def mark_duplicates(db: Session, pairs: list[tuple[Listing, Listing]]):
    """Mark the second listing in each pair as a duplicate of the first."""
    for original, duplicate in pairs:
        duplicate.duplicate_of_id = original.id
    db.commit()
