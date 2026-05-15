import json, re
from pathlib import Path

APP_PATH = Path("/Users/gf/Downloads/mazar_martin_app.html")

def street_words(a):
    tokens = re.sub(r'[^a-z0-9]', ' ', (a or '').lower()).split()
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]

def match(a, b, sa, sb):
    suburb_ok = sa and sb and (sa in sb or sb in sa)
    words_ok = len(set(street_words(a)) & set(street_words(b))) >= 1
    return suburb_ok and words_ok

html = APP_PATH.read_text(encoding="utf-8")
m = re.search(r'propingHistory\s*=\s*(\[.*?\])\s*;', html, re.DOTALL)
history = json.loads(m.group(1))

domain_fs = json.load(open('/Users/gf/Downloads/domain_forsale_lns.json'))
domain_sold = json.load(open('/Users/gf/Downloads/domain_sold_lns.json'))

filled_listed = 0
filled_sold = 0

for day in history:
    for p in day.get('newly_listed', []):
        if p.get('baths'): continue
        pa, ps = p.get('address',''), p.get('suburb','').lower()
        for d in domain_fs:
            if match(pa, d.get('address',''), ps, d.get('suburb','').lower()):
                if d.get('baths'): p['baths'] = d['baths']
                if d.get('parking'): p['parking'] = d['parking']
                if d.get('propertyType'): p['propertyType'] = d['propertyType']
                if d.get('landSize'): p['landSize'] = d['landSize']
                filled_listed += 1
                break

    for p in day.get('sold', []):
        if p.get('baths'): continue
        pa, ps = p.get('address',''), p.get('suburb','').lower()
        for d in domain_sold:
            if match(pa, d.get('address',''), ps, d.get('suburb','').lower()):
                if d.get('baths'): p['baths'] = d['baths']
                if d.get('parking'): p['parking'] = d['parking']
                if d.get('propertyType'): p['propertyType'] = d['propertyType']
                if d.get('landSize'): p['landSize'] = d['landSize']
                if d.get('method'): p['method'] = d['method']
                filled_sold += 1
                break

APP_PATH.write_text(html[:m.start(1)] + json.dumps(history) + html[m.end(1):], encoding="utf-8")
print(f'Newly listed filled: {filled_listed} | Sold filled: {filled_sold}')
