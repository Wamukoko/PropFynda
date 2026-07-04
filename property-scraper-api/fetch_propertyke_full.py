import cloudscraper, sys
scraper = cloudscraper.create_scraper()
url = 'https://propertyke.com/for-rent'
resp = scraper.get(url, timeout=10)
print('Status:', resp.status_code)
print(resp.text[:8000])
