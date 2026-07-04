"""Final inspection — verify JSON-LD and selectors."""
import sys, json, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Property24 — full JSON-LD check ─────────────────────────────────
print("=== Property24 — JSON-LD full ===")
resp = requests.get("https://www.property24.co.ke/4-bedroom-apartment-flat-for-sale-in-westlands-117371320", headers=headers, timeout=20)
s = BeautifulSoup(resp.text, "lxml")
for tag in s.find_all("script", type="application/ld+json"):
    data = json.loads(tag.string)
    if data.get("@type") == "Product":
        print(json.dumps(data, indent=2))
        print()
        print("--- Offers ---")
        print(json.dumps(data.get("offers", {}), indent=2))

# ── PropertyPro — detail page selectors ──────────────────────────────
print("\n=== PropertyPro — key selectors ===")
resp2 = requests.get("https://www.propertypro.co.ke/property/2-bedroom-flatapartment-for-sale-near-adams-arcade-kilimani-nairobi-9BQGL", headers=headers, timeout=20)
s2 = BeautifulSoup(resp2.text, "lxml")

# Check for JSON-LD with listing data
for tag in s2.find_all("script", type="application/ld+json"):
    data = json.loads(tag.string)
    if isinstance(data, dict) and data.get("@type") not in ("Organization", "WebSite"):
        print(f"JSON-LD: {json.dumps(data, indent=2)[:500]}")

# Get full page price area
price_el = s2.select_one(".page-heading")
if price_el:
    parent = price_el.parent
    if parent:
        print(f"h1 parent: <{parent.name} class='{' '.join(parent.get('class', [])) if parent.get('class') else ''}'>")
        print(f"h1 parent text: {parent.get_text(strip=True)[:200]}")

# Find description
for sel in [".description", "[class*=description]", "#description", "p:first-of-type"]:
    el = s2.select_one(sel)
    if el and len(el.get_text(strip=True)) > 50:
        cls = " ".join(el.get("class", [])) if el.get("class") else ""
        print(f"Desc ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:80]}")

# Find property details (bed/bath/size)
for sel in ["[class*=detail]", "[class*=spec]", "[class*=meta]", "ul:first-of-type"]:
    el = s2.select_one(sel)
    if el:
        txt = el.get_text(strip=True)
        if any(k in txt.lower() for k in ["bed", "bath", "sq", "m²"]):
            cls = " ".join(el.get("class", [])) if el.get("class") else ""
            print(f"Details ({sel}): <{el.name} class='{cls}'> {txt[:100]}")

# ── KenyaPropertyCentre — detail page ──────────────────────────────
print("\n=== KenyaPropertyCentre — detail page ===")
resp3 = requests.get("https://kenyapropertycentre.com/for-sale/flats-apartments/nairobi/westlands/64972-ready-lux", headers=headers, timeout=20)
s3 = BeautifulSoup(resp3.text, "lxml")
print(f"Title: {s3.title.string if s3.title else 'none'}")

for tag in s3.find_all("script", type="application/ld+json"):
    data = json.loads(tag.string)
    if isinstance(data, dict):
        print(f"JSON-LD type: {data.get('@type')}")
        if data.get("@type") != "Organization":
            print(json.dumps(data, indent=2)[:600])

h1 = s3.find("h1")
if h1: print(f"h1: {h1.get_text(strip=True)[:60]}")

# Find price
for sel in ["[class*=price]", "[class*=amount]", ".cost", ".value"]:
    el = s3.select_one(sel)
    if el and "KSh" in el.get_text():
        cls = " ".join(el.get("class", [])) if el.get("class") else ""
        print(f"Price ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:40]}")

# Find location
for sel in ["[class*=location]", "[class*=address]", ".area"]:
    el = s3.select_one(sel)
    if el and len(el.get_text(strip=True)) > 5:
        cls = " ".join(el.get("class", [])) if el.get("class") else ""
        print(f"Location ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Find contact/agent
for sel in ["[class*=agent]", "[class*=contact]", "[class*=vendor]"]:
    el = s3.select_one(sel)
    if el:
        cls = " ".join(el.get("class", [])) if el.get("class") else ""
        print(f"Contact ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:80]}")

# Phones
phones3 = re.findall(r"(?:\+?254|0)[17]\d{8}", resp3.text)
print(f"Phones in HTML: {phones3}")
