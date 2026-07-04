import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# SQLite by default. Swap for a Postgres URL in production via env var.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'listings.db'}")

PLATFORMS_FILE = os.getenv("PLATFORMS_FILE", str(BASE_DIR / "data" / "platforms.json"))

# How often the background scheduler re-scrapes each platform, in minutes.
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "180"))

# Politeness settings applied to every outbound scrape request.
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
MIN_DELAY_BETWEEN_REQUESTS_SECONDS = float(os.getenv("MIN_DELAY_BETWEEN_REQUESTS_SECONDS", "2.0"))
MAX_PAGES_PER_PLATFORM_PER_RUN = int(os.getenv("MAX_PAGES_PER_PLATFORM_PER_RUN", "3"))
MAX_LISTINGS_PER_PLATFORM_PER_RUN = int(os.getenv("MAX_LISTINGS_PER_PLATFORM_PER_RUN", "60"))

USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "PropertyAggregatorBot/0.1 (+contact: you@yourdomain.com)",
)

# If True, a platform is skipped entirely when robots.txt disallows the paths
# we need. Keep this True unless you have explicit permission from the site.
RESPECT_ROBOTS_TXT = os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"

# Contact extraction
CONTACT_EXTRACTION_ENABLED = os.getenv("CONTACT_EXTRACTION_ENABLED", "true").lower() == "true"
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
PLAYWRIGHT_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "30000"))

# Circuit breaker
MAX_CONSECUTIVE_FAILURES = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))

# Stale listing threshold
STALE_LISTING_DAYS = int(os.getenv("STALE_LISTING_DAYS", "30"))

# AI Provider (OpenAI / OpenRouter)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
