import cloudscraper, os
scraper = cloudscraper.create_scraper()
url = 'https://propertyke.com/for-rent'
resp = scraper.get(url, timeout=10)
if resp.status_code == 200:
    out_path = os.path.join(os.path.dirname(__file__), 'propertyke_for_rent.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print('Saved HTML to', out_path)
else:
    print('Failed, status', resp.status_code)
