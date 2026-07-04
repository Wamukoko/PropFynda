# Kenya Property Listings API

Aggregates property listings from multiple Kenyan real estate platforms into
one normalized, queryable REST API — **including agent contact data** (phone
numbers, WhatsApp numbers, emails) extracted from the source listings.

## Architecture

```
platforms.json  →  Adapter (per site)  →  NormalizedListing  →  SQLite DB  →  FastAPI
                         ↑
              APScheduler runs this on a timer
                         ↑
              contact.py — Playwright click-to-reveal, regex phone/email scanning,
                           obfuscation decoding, phone number normalization
```

- **`data/platforms.json`** — registry of source platforms and how to scrape each,
  including `contact_gate` config for each platform.
- **`app/scraper/contact.py`** — contact-data extraction utilities:
  Playwright-based click-to-reveal, regex phone/WhatsApp/email scanning,
  obfuscation decoding, and phone number normalization to `+2547XXXXXXXX`.
- **`app/scraper/adapters/`** — one adapter per site. Each adapter now extracts
  contact data from the page HTML and, if configured, uses Playwright to
  trigger click-to-reveal gates.
- **`app/scraper/runner.py`** — runs an adapter and upserts results into the DB,
  persists `ScrapeRun` records, and implements per-platform circuit breaking.
- **`app/scheduler.py`** — re-runs all active platforms every
  `SCRAPE_INTERVAL_MINUTES` (default 180).
- **`app/data_quality.py`** — county normalizer (maps towns to Kenya's 47 counties),
  near-duplicate detection, and stale listing identification.
- **`app/main.py`** — the API: `/listings`, `/listings.csv`, `/search`,
  `/platforms`, `/platforms/{id}/health`, `/platforms/{id}/contacts/stats`,
  `/scrape`.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # required for click-to-reveal contact extraction
cp .env.example .env
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

### First scrape

The scheduler does **not** scrape on startup. Trigger one manually:

```bash
curl -X POST http://localhost:8000/scrape/buyrentkenya   # single platform, synchronous
curl -X POST http://localhost:8000/scrape                # all active platforms, background
```

Then:

```bash
curl "http://localhost:8000/listings?listing_type=sale&min_bedrooms=3&sort=price_asc"
```

### Contact data endpoints

```bash
# Get contact info for a specific listing
curl "http://localhost:8000/listings/1/contacts"

# Search listings by phone number
curl "http://localhost:8000/search?phone=0712345678"

# CSV export with contact columns
curl "http://localhost:8000/listings.csv" -o listings.csv

# Platform health and contact stats
curl "http://localhost:8000/platforms/buyrentkenya/health"
curl "http://localhost:8000/platforms/buyrentkenya/contacts/stats"

# Filter listings that have phone numbers
curl "http://localhost:8000/listings?has_phone=true"
```

## Contact data extraction

This API extracts agent phone numbers, WhatsApp numbers, and email addresses
from listing pages. Extraction methods, in order:

1. **HTML scan** — regex patterns for Kenyan phone numbers (`+2547...`, `07...`),
   WhatsApp links (`wa.me`, `api.whatsapp.com`), and email addresses.
2. **Obfuscation decode** — decodes `&#48;&#49;` char-code entities and other
   common obfuscation techniques.
3. **Playwright click-to-reveal** — if the platform's `contact_gate` config has
   `"use_playwright": true`, the adapter launches a headless browser, clicks the
   gate element, waits for the AJAX-populated content, and extracts from the
   rendered HTML.

Phone numbers are normalized to canonical `+2547XXXXXXXX` format.

## Configuring the generic adapter for a new platform

For each platform using `"adapter": "generic"` in `platforms.json`:

1. **Check for JSON-LD first** — it needs zero configuration if present.
2. **If there's no JSON-LD**, add a `"selectors"` object.
3. **Configure contact extraction** by adding a `"contact_gate"` section:

   ```json
   "contact_gate": {
     "type": "click_to_reveal",
     "selector": ".view-number-btn",
     "wait_selector": ".phone-number",
     "use_playwright": true,
     "wait_timeout_ms": 5000
   }
   ```

   If phone numbers are visible in HTML but obfuscated, add `"phone_patterns"`:
   ```json
   "phone_patterns": ["(?:\\+?254|0)[17]\\d{8}"]
   ```

4. Test: `curl -X POST http://localhost:8000/scrape/example_platform`
   and inspect `/listings?platform=example_platform`.

## Data model

See `app/models.py` for the full schema. Key additions:
- `phone_numbers`, `whatsapp_numbers`, `emails` — JSON arrays of contact strings.
- `contact_reveal_method` — how the contact was obtained (`html_scan`, `click_gate`, `json_ld`, `none`).
- `duplicate_of_id` — links near-duplicate listings across platforms.
- `ScrapeRun` table — records every scrape attempt with stats.
- `PlatformHealth` table — tracks consecutive failures for circuit breaking.

## Extending

- **Postgres instead of SQLite**: set `DATABASE_URL` env var.
- **New adapter**: copy `buyrentkenya.py`, implement `discover_listing_urls` +
  `parse_listing`, register in `registry.py`.
- **JS-only platforms**: use `contact.py`'s `reveal_via_playwright` or write
  a dedicated Playwright adapter.
