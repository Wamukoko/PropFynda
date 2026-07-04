 Wrote Implemention Plan.md

# Implementation Plan — Kenya Property Listings API

This document is written for a coding agent picking up this repository to
extend and harden it. Read this fully before touching code.

## 0. Core objective

**Build full contact-data extraction for every listing.** This includes agent
phone numbers, WhatsApp numbers, email addresses, and any other contact detail
that a source site may gate behind a user-initiated action (e.g. a "View
Number" click that triggers an AJAX call). The scraper must be able to
programmatically trigger those gates and persist the revealed data.

This is the primary differentiator of this API — consumers get contact
information directly without needing to click through to the source site.
Every adapter, pipeline step, and schema decision should serve this goal.

## 1. Repo orientation — what each file is for

```
property-scraper-api/
├── requirements.txt          # Python deps — install these first
├── .env.example              # copy to .env and adjust before running
├── README.md                 # setup + legal/ethical notes, read alongside this file
├── data/
│   └── platforms.json        # registry of source platforms to scrape
└── app/
    ├── config.py              # all tunables, loaded from env vars
    ├── database.py            # SQLAlchemy engine/session, init_db()
    ├── models.py              # ORM: Listing table (the normalized schema)
    ├── schemas.py             # Pydantic response models for the API
    ├── main.py                # FastAPI app + all HTTP endpoints
    ├── scheduler.py           # APScheduler background job wiring
    └── scraper/
        ├── base.py            # BaseAdapter ABC + NormalizedListing dataclass
        ├── utils.py           # fetch(), get_soup(), robots.txt check, JSON-LD extraction
        ├── registry.py        # loads platforms.json, maps adapter name -> class
        ├── runner.py          # runs one adapter, upserts results into DB
        └── adapters/
            ├── buyrentkenya.py  # working reference adapter (regex + meta tags)
            └── generic.py       # JSON-LD-first adapter, CSS-selector fallback
```

### Setup steps

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Dependencies (already pinned in `requirements.txt` — install via
`pip install -r requirements.txt`):
`fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `requests`,
`beautifulsoup4`, `lxml`, `apscheduler`, `python-dotenv`, `tenacity`,
`playwright` (for JS-rendered platforms and click-to-reveal interaction).

If you add a JS-rendering dependency (Playwright/Selenium) for a specific
platform, add it to `requirements.txt` with a comment noting which
platform(s) require it, so it isn't mistaken for a global requirement.

### How the files connect (data flow)

1. `data/platforms.json` lists platforms and which adapter (`buyrentkenya`,
   `generic`, or a new one you add) handles each.
2. `app/scraper/registry.py` reads that file and instantiates the right
   `BaseAdapter` subclass from `app/scraper/adapters/`.
3. Each adapter's `discover_listing_urls()` + `parse_listing()` (defined per
   `app/scraper/base.py`) must only fetch pages via `app/scraper/utils.py`'s
   `fetch()`/`get_soup()` — never call `requests` directly in an adapter —
   because that's where robots.txt checks and rate limiting live.
4. **Contact extraction** is part of `parse_listing()`. After gathering basic
   listing data from the page HTML/JSON-LD, the adapter must attempt to
   reveal gated contact info:
   - Inspect the page for click-to-reveal elements (buttons, overlays).
   - If found, use Playwright to click the element and wait for the
     AJAX-populated content to appear.
   - Extract phone numbers, WhatsApp links, and email addresses from the
     revealed content.
   - If no interactive gate exists, fall back to scanning the full HTML for
     any phone-number-like patterns (`+254...`, `07...`, `01...`) and
     `mailto:` links.
5. `app/scraper/runner.py` calls `adapter.run(...)`, then upserts each
   `NormalizedListing` into `app/models.py`'s `Listing` table via
   `app/database.py`'s session. Contact fields are persisted alongside all
   other listing data.
6. `app/scheduler.py` calls the runner on a timer; `app/main.py` also exposes
   manual trigger endpoints (`POST /scrape/{platform_id}`, `POST /scrape`).
7. `app/main.py`'s `GET /listings` reads straight from the DB and serializes
   through `app/schemas.py` — contact fields are included in API responses.

When adding a field: update `NormalizedListing` (base.py) →
`Listing` ORM model (models.py) → `ListingOut` schema (schemas.py) →
`runner.py`'s field-copy list → any adapters that can populate it.

## 2. Priority backlog

Work top to bottom; each item is independently shippable.

### P0 — Contact-data schema (foundational — must exist before P1)

Add these fields to the data model immediately, as every adapter needs them:

**`NormalizedListing` (base.py)**

```python
phone_numbers: list[str]      # all detected phone numbers
whatsapp_numbers: list[str]   # numbers specifically linked to WhatsApp
emails: list[str]             # email addresses found on the page
contact_reveal_method: str | None  # how they were obtained: "html_scan" | "click_gate" | "json_ld" | "none"
```

**`Listing` ORM (models.py)** — add columns:

- `phone_numbers` — JSON array of strings
- `whatsapp_numbers` — JSON array of strings  
- `emails` — JSON array of strings
- `contact_reveal_method` — nullable varchar

**`ListingOut` (schemas.py)** — expose the same fields in the response.

### P1 — Get more platforms actually producing data (with contact extraction)

`platforms.json` currently has 20 platforms; only `buyrentkenya` has a
dedicated adapter. For each `"adapter": "generic"` platform marked
"Selectors not yet verified":

1. Fetch a listing page and a listing-detail page.
2. Check for `<script type="application/ld+json">` first — if present with
   a relevant `@type`, verify `generic.py`'s `_from_json_ld` extracts it
   correctly and adjust the `relevant_types` set or field mapping if the
   site uses a schema.org shape not yet handled.
3. If no JSON-LD, add a `"selectors"` block to that platform's entry per the
   README's "Configuring the generic adapter" section — **include selectors
   for phone/WhatsApp/email elements** in addition to basic listing fields.
4. **For every platform, identify how contact info is gated:**
   - Add a `"contact_gate"` section to the platform config in
     `platforms.json` describing the gate mechanism:

     ```json
     "contact_gate": {
       "type": "click_to_reveal",     // "click_to_reveal" | "form_submit" | "scroll_to_reveal" | "none"
       "selector": ".view-number-btn", // CSS selector for the trigger element
       "wait_selector": ".phone-number", // CSS selector for content that appears after trigger
       "use_playwright": true          // true if JS interaction is needed
     }
     ```

   - If the platform reveals numbers without interaction (in HTML source but
     obfuscated), add a `"phone_patterns"` list of regex patterns.
5. Build a **generic contact-reveal utility** in `app/scraper/contact.py`
   that adapters can call:
   - `reveal_via_playwright(url, gate_config)` — launches headless browser,
     navigates to the page, clicks the gate element, waits for reveal, and
     returns the rendered HTML or extracted contact strings.
   - `scan_for_phones(html, patterns)` — regex-based phone/WhatsApp/email
     extraction from raw HTML or text.
   - `decode_obfuscated(html_or_element)` — handle common obfuscation
     techniques (rot13, reversed strings, char-code encoding, etc.).
6. Verify with `POST /scrape/{platform_id}` and check `listings_saved` > 0
   and spot-check a few rows via `GET /listings?platform={id}` — confirm
   `phone_numbers`, `whatsapp_numbers`, and `emails` are populated.
7. Update that platform's `"notes"` field to describe what was verified,
   the contact-gate type, and the date, so drift is easier to diagnose later.

Order by `scrape_priority` in `platforms.json` (1 = do first).

### P2 — Reliability and observability

- Add structured logging (counts per platform per run, error rates, contact
  extraction success rate) — extend `runner.py`'s return dict and persist a
  `ScrapeRun` table (platform_id, started_at, finished_at, status,
  listings_found, listings_saved, contacts_found, error).
- Add a `GET /platforms/{id}/health` endpoint showing last successful scrape
  time and last error, sourced from that table.
- Wrap adapter `run()` calls with per-platform circuit breaking: if a
  platform fails N times in a row, mark it inactive in the DB (not in
  `platforms.json`) and surface that via the health endpoint, rather than
  retrying forever against a site that's blocking you.
- Add `GET /platforms/{id}/contacts/stats` — shows how many listings had
  contact info extracted, average number of phones per listing, breakdown by
  reveal method.

### P3 — Data quality

- Add a `county` normalizer: map free-text `location_text` to Kenya's 47
  counties where possible (simple lookup table), populate `Listing.county`.
- Deduplicate near-identical listings across platforms (same address/price/
  bedroom count posted to multiple sites) — surface as a `duplicate_of_id`
  field rather than silently dropping, so nothing is hidden from the API
  consumer without explanation.
- Add a `is_stale` computed flag or filter based on `last_seen_at` age, so
  listings no longer found on the source site can be excluded from default
  query results without deleting history.
- **Phone number normalization**: strip spaces, dashes, and country-code
  variants so `+254 712 345 678`, `0712345678`, and `254712345678` are
  stored as the same canonical number. Use a shared utility in `contact.py`.

### P4 — API surface

- `GET /listings.csv` — stream the same query as `/listings` as CSV,
  including contact columns.
- `GET /listings/{id}/contacts` — returns just the contact block for a
  single listing (phone_numbers, whatsapp_numbers, emails).
- `GET /search?q=...&phone=0712345678` — search listings by agent phone
  number (useful for finding all listings by a specific agent across
  platforms).
- Pagination metadata (`total_count`, `has_more`) on `/listings`.
- Basic API key auth via header, if this will be exposed publicly rather
  than used internally — see `README.md` "How will this API be used" note;
  ask the project owner if this is still undecided.

### P5 — JS-rendered platforms & advanced contact gates

Some platforms in `platforms.json` (Jiji, OLX) render listings client-side
and may return empty results from `requests`-based fetching. For those:

- Confirm with a raw `curl` or `get_soup()` test that listing links aren't
  in the initial HTML before assuming this.
- If confirmed, build a dedicated adapter using Playwright, following
  `BaseAdapter`'s interface exactly like `buyrentkenya.py` does — the rest
  of the pipeline (runner, DB, API) does not need to change.
- **For platforms with aggressive contact gates** (CAPTCHA before reveal,
  login walls, rate-limited AJAX endpoints):
  - Add retry logic with exponential backoff in the contact-reveal utility.
  - Implement session/cookie persistence across scrape runs so you don't
    re-authenticate every time.
  - If the gate involves a form submission (e.g. "enter your email to see
    the number"), log the interaction pattern needed in the platform config
    `"contact_gate"` section so it can be handled generically.

## 3. Guardrails to preserve while doing all of the above

- Every new adapter must go through `is_allowed()` (robots.txt) before
  fetching, and must respect the delay/backoff behavior in `utils.py`.
- Never lower `MIN_DELAY_BETWEEN_REQUESTS_SECONDS` or raise
  `MAX_LISTINGS_PER_PLATFORM_PER_RUN` without a stated reason — these exist
  to keep this project a well-behaved guest on other people's servers.
- **Contact extraction on your own sites**: since you own the platforms
  being scraped, ensure your own sites' robots.txt and Terms of Service
  reflect that automated contact-data extraction is permitted. For
  third-party platforms you do not own, respect their ToS and robots.txt.
- Store contact data securely — phone numbers and emails are PII. Encrypt
  at rest if the DB is not already encrypted. Do not expose raw contact
  data in server logs.
- If a platform's ToS prohibits scraping (check manually — this isn't
  automated), mark it `"active": false` in `platforms.json` with a note
  explaining why, rather than building around the restriction.
- When using Playwright for click-to-reveal, run headless and with
  minimal fingerprint — do not use a persistent profile that could be
  identified and blocked.
