"""Continued deep inspection with encoding handling."""
import sys, json, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ── Property24 — detail page ────────────────────────────────────────
print("=== Property24 — detail page ===")
url = "https://www.property24.co.ke/4-bedroom-apartment-flat-for-sale-in-westlands-117371320"
resp = requests.get(url, headers=headers, timeout=20)
s = BeautifulSoup(resp.text, "lxml")

h1 = s.find("h1")
if h1: print(f"h1: {h1.get_text(strip=True)}")

for j in s.find_all("script", type="application/ld+json"):
    try:
        data = json.loads(j.string)
        print(f"JSON-LD: {json.dumps(data, indent=2)[:500]}")
    except: pass

# Find price
for sel in ["[class*=price]", "[itemprop*=price]", ".amount"]:
    el = s.select_one(sel)
    if el: print(f"Price ({sel}): {el.get_text(strip=True)[:60]}")

# Location  
for sel in ["[class*=location]", "[class*=address]", "[itemprop*=location]"]:
    el = s.select_one(sel)
    if el: print(f"Location ({sel}): {el.get_text(strip=True)[:60]}")

# agent
for sel in ["[class*=agent]", "[class*=seller]", ".name"]:
    el = s.select_one(sel)
    if el: print(f"Agent ({sel}): {el.get_text(strip=True)[:60]}")

# Beds etc
text = s.get_text()
for pat, label in [(r"(\d+)\s*Bed", "bed"), (r"(\d+)\s*Bath", "bath"), (r"(\d+)\s*(?:m[2\u00b2]|sq)", "size")]:
    m = re.search(pat, text, re.IGNORECASE)
    if m: print(f"{label}: {m.group(0)}")

# Phones
phones = re.findall(r"(?:\+?254|0)[17]\d{8}", resp.text)
print(f"Phones in HTML: {phones[:3]}")
# Look for gate
for tag in s.find_all(["button", "a", "span"]):
    t = tag.get_text(strip=True).lower()
    if any(k in t for k in ["view number", "show number", "phone", "whatsapp"]):
        cls = " ".join(tag.get("class", [])) if tag.get("class") else ""
        print(f"Gate: <{tag.name} class='{cls}'> {tag.get_text(strip=True)}")

# ── PropertyPro — search page card selectors ────────────────────────
print("\n=== PropertyPro — search page card structure ===")
url2 = "https://www.propertypro.co.ke/property-for-sale/flat-apartment"
s2 = BeautifulSoup(requests.get(url2, headers=headers, timeout=20).text, "lxml")

card = s2.select_one(".property-listing")
if card:
    print(f"Card HTML: {str(card)[:600]}")
    link = card.find("a", href=True)
    if link: print(f"Listing link: {link['href'][:80]}, class: {' '.join(link.get('class', [])) if link.get('class') else 'none'}")

# ── Kenya Property Centre — find listing cards ──────────────────────
print("\n=== KenyaPropertyCentre — search page ===")
url3 = "https://kenyapropertycentre.com/for-sale/flats-apartments?bedrooms=1"
s3 = BeautifulSoup(requests.get(url3, headers=headers, timeout=20).text, "lxml")

# Look for any element with a link to a property detail
for a in s3.find_all("a", href=True):
    h = a["href"]
    if re.search(r"/property/", h, re.IGNORECASE) or re.search(r"/listing/", h, re.IGNORECASE):
        cls = " ".join(a.get("class", [])) if a.get("class") else ""
        print(f"Property link: <a class='{cls}' href='{h[:60]}'> {a.get_text(strip=True)[:40]}")
        full = urljoin(url3, h)
        # Get detail page
        sd = BeautifulSoup(requests.get(full, headers=headers, timeout=20).text, "lxml")
        print(f"Detail title: {sd.title.string if sd.title else 'none'}")
        for j in sd.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(j.string)
                print(f"JSON-LD: {json.dumps(data, indent=2)[:300]}")
            except: pass
        h1 = sd.find("h1")
        if h1: print(f"h1: {h1.get_text(strip=True)[:60]}")
        phones3 = re.findall(r"(?:\+?254|0)[17]\d{8}", sd.get_text())
        if phones3: print(f"Phones: {phones3[:3]}")
        break

# Also check for card structure in search page
for sel in ["[class*=card]", "[class*=listing]", "[class*=property]", "[class*=tile]", "article"]:
    els = s3.select(sel)
    if els:
        for el in els[:2]:
            link = el.find("a", href=True)
            if link and len(el.get_text(strip=True)) > 20:
                cls = " ".join(el.get("class", [])) if el.get("class") else ""
                print(f"Card: <{el.name} class='{cls}'>")
                print(f"  Link: {link['href'][:60]}")
                print(f"  Text: {el.get_text(strip=True)[:80]}")
                break
