"""Inspect platforms for selectors and contact gates."""
import json, re, sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

sites = [
    ('Property24', 'https://www.property24.co.ke/for-sale'),
    ('PropertyPro', 'https://www.propertypro.co.ke/for-sale'),
    ('KenyaPropertyCentre', 'https://kenyapropertycentre.com/results/sale/all'),
]

def inspect(name, url):
    print(f'\n=== {name} ===')
    print(f'URL: {url}')
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, 'lxml')
        print(f'Status: {resp.status_code}, Size: {len(resp.text)} bytes')
        print(f'Title: {soup.title.string if soup.title else "none"}')

        # Check for JSON-LD
        jsonld = soup.find_all('script', type='application/ld+json')
        print(f'JSON-LD blocks: {len(jsonld)}')
        for j in jsonld[:3]:
            try:
                data = json.loads(j.string or '{}')
                t = data.get('@type', [])
                if isinstance(t, list):
                    types = t
                else:
                    types = [t]
                print(f'  Types: {types}')
            except Exception as e:
                print(f'  Parse error: {e}')

        # Find listing links
        links = set()
        for a in soup.find_all('a', href=True):
            h = a['href']
            full = urljoin(url, h)
            if any(k in full.lower() for k in ['/property', '/listing', '/for-sale/', '/rent/', '-for-sale', '-for-rent']):
                if h not in ('#', '') and not h.startswith('tel:') and not h.startswith('mailto:'):
                    links.add(h)
        print(f'Listing links found: {len(links)}')
        for l in sorted(links)[:5]:
            print(f'  {l}')

        # Find listing link CSS selectors
        for a in soup.find_all('a', href=True):
            h = a['href']
            full = urljoin(url, h)
            if any(k in full.lower() for k in ['/property', '/listing', '-for-sale', '-for-rent']):
                cls = ' '.join(a.get('class', [])) if a.get('class') else 'no-class'
                parent_cls = ' '.join(a.parent.get('class', [])) if a.parent and a.parent.get('class') else ''
                print(f'  Sample link tag: <a class="{cls}" href="{h[:80]}">')
                if parent_cls:
                    print(f'    Parent class: {parent_cls}')
                break

        # Identify key page elements
        for sel, desc in [
            ('h1', 'Title (h1)'),
            ('.price, [class*=price]', 'Price'),
            ('.location, [class*=location], [class*=address]', 'Location'),
            ('.bedroom, [class*=bed]', 'Bedrooms'),
            ('.agent, [class*=agent], [class*=seller]', 'Agent'),
        ]:
            els = soup.select(sel)
            if els:
                for el in els[:2]:
                    text = el.get_text(strip=True)[:60]
                    if text:
                        cls = ' '.join(el.get('class', []))
                        print(f'  {desc}: <{el.name} class="{cls}"> {text}')

        # Phone / contact elements
        phones = []
        for tag in soup.find_all(['a', 'span', 'div', 'button', 'p']):
            text = tag.get_text(strip=True)
            if re.search(r'07\d{8}|01\d{8}|\+254', text):
                phones.append(text[:50])
            cls_str = ' '.join(tag.get('class', [])) if tag.get('class') else ''
            if any(k in cls_str.lower() for k in ['phone', 'number', 'contact', 'whatsapp', 'telephone']):
                phones.append(f'[class:{cls_str}] {text[:40]}')
        if phones:
            print(f'Contact elements ({len(phones)}):')
            for p in phones[:8]:
                print(f'  {p}')
        else:
            print('No contact elements found')

        # Gate buttons
        for tag in soup.find_all(['button', 'a', 'span']):
            text = tag.get_text(strip=True).lower()
            if any(k in text for k in ['view number', 'show number', 'phone', 'contact', 'reveal']):
                cls = ' '.join(tag.get('class', [])) if tag.get('class') else ''
                print(f'  Gate button: <{tag.name} class="{cls}"> {tag.get_text(strip=True)}')

    except Exception as e:
        print(f'Error: {e}')

for name, url in sites:
    inspect(name, url)
