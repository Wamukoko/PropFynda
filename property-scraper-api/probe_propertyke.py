import requests, re, sys
url = 'https://propertyke.com'
resp = requests.get(url, timeout=10)
print('Status:', resp.status_code)
if resp.status_code != 200:
    sys.exit(0)
text = resp.text
links = re.findall(r'href=["\']([^"\'>]+)', text)
filtered = [l for l in links if 'property' in l.lower() or 'listings' in l.lower()]
print('Found', len(filtered), 'potential listing links:')
for link in filtered[:30]:
    print(link)
