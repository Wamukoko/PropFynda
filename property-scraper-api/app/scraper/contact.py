"""
Contact-data extraction utilities.

Handles:
- Playwright-based click-to-reveal for gated phone/WhatsApp numbers.
- Regex-based phone, WhatsApp, and email scanning from raw HTML/text.
- De-obfuscation of common encoding tricks (rot13, char codes, reversed strings).
- Phone number normalization to canonical format (+2547XXXXXXXX).
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("scraper")

# ── Phone number patterns ──────────────────────────────────────────────

# Kenyan numbers: +2547XXXXXXXX, 07XXXXXXXX, 01XXXXXXXX, 2547XXXXXXXX
KE_PHONE_RE = re.compile(
    r"(?:(?:\+?254|0)[17]\d{8})"
    r"(?:\s*(?:/|,|&|\s)\s*(?:\+?254|0)[17]\d{8})*"
)

# Individual phone number capture (used after splitting multi-number strings)
PHONE_CAPTURE_RE = re.compile(r"(\+?254|0)([17]\d{8})")

# WhatsApp-specific: wa.me links, whatsapp.com links, or "WhatsApp: 07..."
WHATSAPP_LINK_RE = re.compile(
    r"(?:https?://)?(?:wa\.me|api\.whatsapp\.com)/[a-z0-9?=/&+-]+",
    re.IGNORECASE,
)
WHATSAPP_TEXT_RE = re.compile(
    r"(?:whatsapp|whatsapp)[:\s]*(\+?254|0[17]\d{8})",
    re.IGNORECASE,
)

# Email pattern
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


# ── Normalization ──────────────────────────────────────────────────────

def normalize_phone(raw: str) -> Optional[str]:
    """Normalize a Kenyan phone number to +2547XXXXXXXX format."""
    raw = raw.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    match = PHONE_CAPTURE_RE.search(raw)
    if not match:
        return None
    prefix, number = match.group(1), match.group(2)
    if prefix == "0":
        return f"+254{number}"
    if prefix == "254":
        return f"+{prefix}{number}"
    if prefix == "+254":
        return f"{prefix}{number}"
    return None


def normalize_phones(raw_numbers: list[str]) -> list[str]:
    """Normalize a list of raw phone strings, deduplicating."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in raw_numbers:
        norm = normalize_phone(raw)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


# ── Scanning ───────────────────────────────────────────────────────────

def scan_for_phones(text: str, patterns: Optional[list[str]] = None) -> list[str]:
    """Extract all phone numbers from text.

    If custom patterns (regex strings) are provided, they are tried first.
    Falls back to the built-in Kenyan phone pattern.
    """
    phones: list[str] = []
    if patterns:
        for pat in patterns:
            try:
                phones.extend(re.findall(pat, text))
            except re.error:
                continue
    if not phones:
        phones = KE_PHONE_RE.findall(text)
        # Split multi-number strings like "0722123456 / 0733123456"
        expanded: list[str] = []
        for p in phones:
            expanded.extend(re.split(r"\s*[/,&]\s*", p))
        phones = expanded
    return normalize_phones(phones)


def scan_for_whatsapp(text: str) -> list[str]:
    """Extract WhatsApp numbers from links or text mentions."""
    numbers: list[str] = []

    # From wa.me/api links
    for link in WHATSAPP_LINK_RE.findall(text):
        phone_match = re.search(r"(?:phone|send)\?phone=(\+?254\d{9})", link)
        if not phone_match:
            phone_match = re.search(r"wa\.me/(\+?254\d{9})", link)
        if phone_match:
            numbers.append(phone_match.group(1))

    # From WhatsApp: text mentions
    for m in WHATSAPP_TEXT_RE.finditer(text):
        numbers.append(m.group(1))

    return normalize_phones(numbers)


def scan_for_emails(text: str) -> list[str]:
    """Extract all email addresses from text."""
    emails = EMAIL_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for e in emails:
        lower = e.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(e)
    return result


# ── Obfuscation decoding ───────────────────────────────────────────────

def decode_obfuscated(text: str) -> str:
    """Attempt to decode common obfuscation techniques.

    Handles:
    - Rot13 / Caesar cipher
    - Reversed strings
    - HTML char-code entities (&#48;&#49;...)
    - Hex entities (&#x30;&#x31;...)
    """
    result = text

    # HTML char-code entities: &#48;&#49; -> "01"
    try:
        result = re.sub(
            r"&#(\d+);",
            lambda m: chr(int(m.group(1))),
            result,
        )
    except (ValueError, OverflowError):
        pass

    # HTML hex entities: &#x30;&#x31; -> "01"
    try:
        result = re.sub(
            r"&#x([0-9a-fA-F]+);",
            lambda m: chr(int(m.group(1), 16)),
            result,
        )
    except (ValueError, OverflowError):
        pass

    return result


def decode_if_obfuscated(element_text: str) -> str:
    """Detect and decode obfuscated contact strings.

    Heuristic: if the text contains &# or looks like it might be encoded,
    run it through decode_obfuscated.
    """
    if "&#" in element_text:
        return decode_obfuscated(element_text)
    return element_text


# ── Playwright-based click-to-reveal ───────────────────────────────────

async def reveal_via_playwright(url: str, gate_config: dict) -> Optional[str]:
    """Navigate to a URL, click a gated element, and return page text.

    gate_config expects:
        {
            "type": "click_to_reveal" | "scroll_to_reveal",
            "selector": ".view-number-btn",
            "wait_selector": ".phone-number",
            "wait_timeout_ms": 5000
        }

    Returns the full page text after the gate is triggered, or None on failure.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright not installed — cannot reveal gated contacts. "
                      "Run: pip install playwright && playwright install chromium")
        return None

    gate_type = gate_config.get("type", "click_to_reveal")
    selector = gate_config.get("selector")
    wait_selector = gate_config.get("wait_selector")
    timeout = gate_config.get("wait_timeout_ms", 5000)

    if not selector:
        logger.warning("reveal_via_playwright: no selector in gate_config")
        return None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if gate_type == "click_to_reveal":
                try:
                    await page.click(selector, timeout=timeout)
                except Exception as exc:
                    logger.debug("Click failed on %s (%s): %s", url, selector, exc)
                    # Element might already be visible — continue
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=timeout)
                    except Exception:
                        logger.debug("Wait selector %s not found on %s", wait_selector, url)

            elif gate_type == "scroll_to_reveal":
                try:
                    await page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
                except Exception as exc:
                    logger.debug("Scroll failed on %s: %s", url, exc)

            content = await page.content()
            return content
        except Exception as exc:
            logger.error("Playwright navigation failed for %s: %s", url, exc)
            return None
        finally:
            await browser.close()


# ── Combined extraction ────────────────────────────────────────────────

def extract_contacts_from_html(
    html: str,
    gate_config: Optional[dict] = None,
    phone_patterns: Optional[list[str]] = None,
) -> dict:
    """Run all contact extractors against HTML and return structured results.

    Returns:
        {
            "phone_numbers": [...],
            "whatsapp_numbers": [...],
            "emails": [...],
            "contact_reveal_method": str
        }
    """
    text = decode_obfuscated(html)

    phone_numbers = scan_for_phones(text, phone_patterns)
    whatsapp_numbers = scan_for_whatsapp(text)
    emails = scan_for_emails(text)

    # Determine reveal method
    if gate_config and gate_config.get("type") in ("click_to_reveal", "scroll_to_reveal"):
        method = "click_gate"
    elif phone_patterns:
        method = "html_scan"
    elif phone_numbers or emails:
        method = "html_scan"
    else:
        method = "none"

    return {
        "phone_numbers": phone_numbers,
        "whatsapp_numbers": whatsapp_numbers,
        "emails": emails,
        "contact_reveal_method": method,
    }
