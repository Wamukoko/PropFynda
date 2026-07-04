"""Find listing detail pages for each platform and analyze their structure."""
import json, re, sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ── Property24 Kenya ────────────────────────────────────────────────
print("=== Property24 - search page ===")
url = "https://www.property24.co.ke/property-for-sale"
resp = requests.get(url, headers=headers, timeout=20)
s = BeautifulSoup(resp.text, "lxml")

# Find actual listing URLs
for a in s.find_all("a", href=True):
    h = a["href"]
    if re.search(r"/property-for-sale-\d+", h):
        full = urljoin(url, h)
        print("Listing detail URL:", full)
        # Now inspect that listing page
        detail_resp = requests.get(full, headers=headers, timeout=20)
        detail = BeautifulSoup(detail_resp.text, "lxml")
        print(f"Detail title: {detail.title.string if detail.title else 'none'}")

        # JSON-LD
        for j in detail.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(j.string)
                print(f"JSON-LD types: {data.get('@type')}")
                if isinstance(data, dict):
                    print(f"  name: {data.get('name')}")
                    print(f"  price: {data.get('offers', {}).get('price')}")
            except: pass

        # Extract fields
        h1 = detail.find("h1")
        if h1: print(f"h1: {h1.get_text(strip=True)}")

        price_el = detail.select_one("[class*=price], [id*=price]")
        if price_el: print(f"price: {price_el.get_text(strip=True)[:80]}")

        for sel in ["[class*=bed]", "[class*=bedroom]", "[class*=Bedroom]"]:
            el = detail.select_one(sel)
            if el:
                print(f"bed: {el.get_text(strip=True)[:40]}")
                break

        # Contact info
        phones = re.findall(r"(?:\+?254|0)[17]\d{8}", detail_resp.text)
        if phones:
            print(f"phones in HTML: {phones[:3]}")
        else:
            print("No phone numbers in raw HTML")

        # Gate buttons
        for tag in detail.find_all(["button", "a", "span"]):
            t = tag.get_text(strip=True).lower()
            if any(k in t for k in ["view number", "show number", "phone", "whatsapp", "call"]):
                cls = " ".join(tag.get("class", [])) if tag.get("class") else ""
                print(f"Gate button: <{tag.name} class='{cls}'> {tag.get_text(strip=True)}")
        break

# ── PropertyPro Kenya ───────────────────────────────────────────────
print("\n=== PropertyPro - listing page ===")
url2 = "https://www.propertypro.co.ke/property-for-sale/flat-apartment"
resp2 = requests.get(url2, headers=headers, timeout=20)
s2 = BeautifulSoup(resp2.text, "lxml")

# Find listing cards
for sel in ["[class*=card]", "[class*=listing]", "[class*=property]", "[class*=item]"]:
    cards = s2.select(sel)
    if cards:
        for card in cards[:5]:
            link = card.find("a", href=True)
            if link and link["href"] not in ("#", "") and not link["href"].startswith("tel:"):
                full = urljoin(url2, link["href"])
                if "/property" in full.lower() or "/listing" in full.lower() or re.search(r"/\d+", full):
                    cls = " ".join(card.get("class", [])) if card.get("class") else ""
                    print(f"Card class: {cls}")
                    print(f"Listing link: {full}")

                    # Inspect detail page
                    d2 = requests.get(full, headers=headers, timeout=20)
                    s_detail = BeautifulSoup(d2.text, "lxml")
                    print(f"Detail title: {s_detail.title.string if s_detail.title else 'none'}")

                    for j in s_detail.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(j.string)
                            types = data.get("@type", [])
                            if isinstance(types, list):
                                print(f"JSON-LD types: {types}")
                            else:
                                print(f"JSON-LD type: {types}")
                        except: pass

                    h1 = s_detail.find("h1")
                    if h1: print(f"h1: {h1.get_text(strip=True)[:80]}")

                    phones = re.findall(r"(?:\+?254|0)[17]\d{8}", d2.text)
                    if phones:
                        print(f"phones: {phones[:3]}")
                    else:
                        print("No phones in HTML")

                    for tag in s_detail.find_all(["button", "a", "span"]):
                        t = tag.get_text(strip=True).lower()
                        if any(k in t for k in ["view number", "show number", "phone", "whatsapp", "call"]):
                            cls = " ".join(tag.get("class", [])) if tag.get("class") else ""
                            print(f"Gate: <{tag.name} class='{cls}'> {tag.get_text(strip=True)}")
                    break
        break

# ── Kenya Property Centre ───────────────────────────────────────────
print("\n=== KenyaPropertyCentre - listing page ===")
url3 = "https://kenyapropertycentre.com/for-sale/flats-apartments"
resp3 = requests.get(url3, headers=headers, timeout=20)
s3 = BeautifulSoup(resp3.text, "lxml")

for a in s3.find_all("a", href=True):
    h = a["href"]
    if re.search(r"/for-sale/flats-apartments/", h):
        full3 = urljoin(url3, h)
        print(f"Listing link: {full3}")

        d3 = requests.get(full3, headers=headers, timeout=20)
        s3d = BeautifulSoup(d3.text, "lxml")
        print(f"Detail title: {s3d.title.string if s3d.title else 'none'}")

        for j in s3d.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(j.string)
                t = data.get("@type", [])
                if isinstance(t, list): print(f"JSON-LD types: {t}")
                else: print(f"JSON-LD type: {t}")
            except: pass

        h1 = s3d.find("h1")
        if h1: print(f"h1: {h1.get_text(strip=True)[:80]}")

        phones = re.findall(r"(?:\+?254|0)[17]\d{8}", d3.text)
        if phones:
            print(f"phones: {phones[:3]}")
        else:
            print("No phones in HTML")

        for tag in s3d.find_all(["button", "a", "span"]):
            t = tag.get_text(strip=True).lower()
            if any(k in t for k in ["view number", "show number", "phone", "whatsapp", "call"]):
                cls = " ".join(tag.get("class", [])) if tag.get("class") else ""
                print(f"Gate: <{tag.name} class='{cls}'> {tag.get_text(strip=True)}")
        break
