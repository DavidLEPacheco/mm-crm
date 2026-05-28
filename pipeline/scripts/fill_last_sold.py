import json, re
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "mazar_martin_app.html"

def street_words(a):
    tokens = re.sub(r'[^a-z0-9]', ' ', (a or '').lower()).split()
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]

def match(a, b, sa, sb):
    suburb_ok = sa and sb and (sa in sb or sb in sa)
    words_ok = len(set(street_words(a)) & set(street_words(b))) >= 1
    return suburb_ok and words_ok

html = APP_PATH.read_text(encoding="utf-8")
m = re.search('"sampleListings"\\s*:\\s*(\\[.*?\\])\\s*[,}]', html, re.DOTALL)
app = json.loads(m.group(1))
sold = json.load(open(Path(__file__).resolve().parent.parent / 'domain_sold_lns.json'))

filled = 0
for p in app:
    if p.get('lastSold'): continue
    pa = p.get('address', '')
    ps = p.get('suburb', '').lower()
    for s in sold:
        if match(pa, s.get('address', ''), ps, s.get('suburb', '').lower()):
            if s.get('soldPrice'): p['lastSold'] = s['soldPrice']
            if s.get('soldDate'): p['lastSoldDate'] = s['soldDate']
            filled += 1
            break

APP_PATH.write_text(html[:m.start(1)] + json.dumps(app) + html[m.end(1):], encoding="utf-8")
print(f'Last sold filled: {filled}')
