import json, re
from pathlib import Path

APP_PATH = Path("/Users/gf/Downloads/mazar_martin_app.html")

def street_words(a):
    tokens = re.sub(r'[^a-z0-9]', ' ', (a or '').lower()).split()
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]

def match(a, b):
    return len(set(street_words(a)) & set(street_words(b))) >= 1

html = APP_PATH.read_text(encoding="utf-8")
m = re.search('"soldListings"\\s*:\\s*(\\[.*?\\])\\s*[,}]', html, re.DOTALL)
sold = json.loads(m.group(1))
domain = json.load(open('/Users/gf/Downloads/domain_sold_lns.json'))

filled = 0
for s in sold:
    if s.get('method') and s.get('baths'):
        continue
    sa = s.get('address', '')
    ss = s.get('suburb', '').lower()
    for d in domain:
        ds = d.get('suburb', '').lower()
        if ss and ds and ss not in ds and ds not in ss:
            continue
        if match(sa, d.get('address', '')):
            if not s.get('method') and d.get('method'): s['method'] = d['method']
            if not s.get('baths') and d.get('baths'): s['baths'] = d['baths']
            if not s.get('parking') and d.get('parking'): s['parking'] = d['parking']
            if not s.get('propertyType') and d.get('propertyType'): s['propertyType'] = d['propertyType']
            if not s.get('landSize') and d.get('landSize'): s['landSize'] = d['landSize']
            filled += 1
            break

APP_PATH.write_text(html[:m.start(1)] + json.dumps(sold) + html[m.end(1):], encoding="utf-8")
print(f'Filled: {filled}')
