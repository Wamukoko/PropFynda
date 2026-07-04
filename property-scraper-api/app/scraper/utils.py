"""
Shared, cross-cutting scraping utilities.

Design goals:
- Never hit a URL that robots.txt disallows for our user agent.
- Always rate-limit and back off on failure - we are guests on these sites.
- Prefer structured data (JSON-LD / schema.org) embedded in the page over
  fragile CSS-selector scraping, since many listing sites emit this for SEO
  and it survives redesigns much better than div/class scraping.
"""
import json
import logging
import time
import urllib.robotparser as robotparser
from typing import Optional
from urllib.parse import urljoin, urlparse

import cloudscraper
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import (
    MIN_DELAY_BETWEEN_REQUESTS_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    RESPECT_ROBOTS_TXT,
    USER_AGENT,
)

_SCRAPER = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

logger = logging.getLogger("scraper")

_robots_cache: dict[str, robotparser.RobotFileParser] = {}
_last_request_time: dict[str, float] = {}


def _domain(url: str) -> str:
    return urlparse(url).netloc


def is_allowed(url: str) -> bool:
    """Check robots.txt for the given URL against our user agent."""
    if not RESPECT_ROBOTS_TXT:
        return True

    domain = _domain(url)
    if domain not in _robots_cache:
        rp = robotparser.RobotFileParser()
        robots_url = urljoin(f"https://{domain}", "/robots.txt")
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch robots.txt for %s (%s); assuming disallowed", domain, exc)
            # Fail closed: if we can't confirm we're allowed, don't scrape.
            _robots_cache[domain] = None
            return False
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    if rp is None:
        return False
    return rp.can_fetch(USER_AGENT, url)


def _throttle(domain: str) -> None:
    last = _last_request_time.get(domain, 0.0)
    elapsed = time.monotonic() - last
    wait = MIN_DELAY_BETWEEN_REQUESTS_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_time[domain] = time.monotonic()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
def fetch(url: str) -> Optional[requests.Response]:
    """Fetch a URL politely: robots.txt check, rate limit, retry with backoff."""
    if not is_allowed(url):
        logger.info("Skipping (robots.txt disallows): %s", url)
        return None

    domain = _domain(url)
    _throttle(domain)

    resp = _SCRAPER.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp


def get_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = fetch(url)
    except Exception:
        logger.warning("Failed to fetch %s; skipping", url, exc_info=True)
        return None
    if resp is None:
        return None
    return BeautifulSoup(resp.text, "lxml")


def extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    """Pull out every JSON-LD block on the page (schema.org structured data)."""
    blocks = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list):
            blocks.extend(data)
        else:
            blocks.append(data)
    return blocks


def absolute_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)
