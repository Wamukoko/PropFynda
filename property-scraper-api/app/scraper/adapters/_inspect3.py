"""Deep inspect each platform for specific selectors."""
import json, re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ── Property24 — find listing cards on search page ──────────────────
print("=== Property24 — listing cards ===")
url = "https://www.property24.co.ke/property-for-sale"
resp = requests.get(url, headers=headers, timeout=20)
s = BeautifulSoup(resp.text, "lxml")

# Look for any link that goes to a property detail page
for a in s.find_all("a", href=True):
    h = a["href"]
    if re.search(r"/property-details-", h) or re.search(r"/\d{4,}", h):
        print(f"Prop detail link: {h}")
        cls = " ".join(a.get("class", [])) if a.get("class") else "no-class"
        print(f"  <a class='{cls}'> {a.get_text(strip=True)[:50]}")
        parent = a.parent
        if parent:
            pcls = " ".join(parent.get("class", [])) if parent.get("class") else ""
            print(f"  parent: <{parent.name} class='{pcls}'>")

# Check for general listing patterns
for sel in ["[class*=tile]", "[class*=card]", "[class*=listing]", "[class*=property]", "[class*=result]"]:
    els = s.select(sel)
    if els:
        print(f"'{sel}': {len(els)} elements")
        for el in els[:2]:
            cls = " ".join(el.get("class", [])) if el.get("class") else ""
            link = el.find("a", href=True)
            if link:
                print(f"  <{el.name} class='{cls}'> link: {link['href'][:60]}")

# ── PropertyPro — detailed selectors ─────────────────────────────────
print("\n=== PropertyPro — detail page selectors ===")
url2 = "https://www.propertypro.co.ke/property/2-bedroom-flatapartment-for-sale-near-adams-arcade-kilimani-nairobi-9BQGL"
resp2 = requests.get(url2, headers=headers, timeout=20)
s2 = BeautifulSoup(resp2.text, "lxml")

# Title
h1 = s2.find("h1")
if h1:
    print(f"h1 class: {' '.join(h1.get('class', []))}")
    print(f"h1 text: {h1.get_text(strip=True)[:60]}")

# Price
for sel in ["[class*=price]", "[id*=price]", ".amount", ".value"]:
    el = s2.select_one(sel)
    if el:
        cls = " ".join(el.get("class", []))
        print(f"Price ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Location
for sel in ["[class*=location]", "[class*=address]", "[class*=area]"]:
    el = s2.select_one(sel)
    if el:
        cls = " ".join(el.get("class", []))
        print(f"Location ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Bed/bath/size
for sel in ["[class*=bed]", "[class*=bath]", "[class*=size]", "[class*=sq]"]:
    el = s2.select_one(sel)
    if el:
        cls = " ".join(el.get("class", []))
        print(f"Detail ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Description
desc = s2.find("meta", attrs={"name": "description"}) or s2.find("meta", attrs={"property": "og:description"})
if desc:
    print(f"Meta desc: {desc.get('content', '')[:80]}")
for sel in ["[class*=description]", "[itemprop=description]", "p:has-text"]:
    el = s2.select_one(sel.split(":")[0]) if ":" not in sel else None
    if el:
        cls = " ".join(el.get("class", []))
        print(f"Desc ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Agent
for sel in ["[class*=agent]", "[class*=seller]", "[class*=owner]"]:
    el = s2.select_one(sel)
    if el:
        cls = " ".join(el.get("class", []))
        print(f"Agent ({sel}): <{el.name} class='{cls}'> {el.get_text(strip=True)[:60]}")

# Phone numbers - find their surrounding context
phone_text = s2.get_text()
for m in re.finditer(r"(?:011|07|01|254)\d{8}", phone_text):
    start = max(0, m.start() - 40)
    end = min(len(phone_text), m.end() + 40)
    ctx = phone_text[start:end].replace("\n", " ").strip()
    print(f"Phone context: ...{ctx}...")

# Gate buttons
for tag in s2.find_all(["button", "a", "span", "div"]):
    t = tag.get_text(strip=True).lower()
    if any(k in t for k in ["view number", "show number", "phone", "whatsapp", "call"]):
        cls = " ".join(tag.get("class", [])) if tag.get("class") else ""
        print(f"Gate: <{tag.name} class='{cls}'> {tag.get_text(strip=True)}")

# PropertyPro — search page listing card structure
print("\n=== PropertyPro — search page cards ===")
s2_search = BeautifulSoup(requests.get("https://www.propertypro.co.ke/property-for-sale/flat-apartment", headers=headers, timeout=20).text, "lxml")
for card in s2_search.select(".property-listing"):
    cls_info = {}
    # Price
    p = card.select_one("[class*=price]")
    if p: cls_info["price"] = f"<{p.name} class='{' '.join(p.get('class', []))}'> {p.get_text(strip=True)[:30]}" if p.get("class") else p.get_text(strip=True)[:30]
    # Link
    link = card.find("a", href=True)
    if link:
        lcls = " ".join(link.get("class", [])) if link.get("class") else ""
        cls_info["link"] = f"<a class='{lcls}' href='{link['href'][:50]}'>"
    # Title
    t = card.find(["h2", "h3", "h4"])
    if t:
        tcls = " ".join(t.get("class", [])) if t.get("class") else ""
        cls_info["title"] = f"<{t.name} class='{tcls}'> {t.get_text(strip=True)[:40]}"
    # Location
    loc = card.select_one("[class*=location]")
    if loc:
        lcls = " ".join(loc.get("class", [])) if loc.get("class") else ""
        cls_info["location"] = f"<{loc.name} class='{lcls}'> {loc.get_text(strip=True)[:30]}"
    if cls_info:
        print(f"Card structure: {cls_info}")
        break

# ── Kenya Property Centre — find actual property detail page ────────
print("\n=== KenyaPropertyCentre — search page cards ===")
url3 = "https://kenyapropertycentre.com/for-sale/flats-apartments?bedrooms=1"
resp3 = requests.get(url3, headers=headers, timeout=20)
s3 = BeautifulSoup(resp3.text, "lxml")

# Find listing cards
for sel in ["[class*=card]", "[class*=listing]", "[class*=property]", "article", "[role=article]", "[data-property]"]:
    els = s3.select(sel)
    if els:
        print(f"'{sel}': {len(els)} elements")
        for el in els[:3]:
            cls = " ".join(el.get("class", [])) if el.get("class") else ""
            link = el.find("a", href=True)
            txt = el.get_text(strip=True)[:80]
            if link and len(txt) > 10:
                print(f"  <{el.name} class='{cls}'>")
                print(f"    link: {link['href'][:60]}")
                print(f"    text: {txt}")
                break

# Also check for meta/open graph
og_url = s3.find("meta", property="og:url")
if og_url:
    print(f"og:url: {og_url.get('content')}")
