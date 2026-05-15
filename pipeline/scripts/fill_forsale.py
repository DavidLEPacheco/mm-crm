import json, re

def norm(a):
    return re.sub(r'[^a-z0-9]', ' ', (a or '').lower()).split()

def street_words(a):
    tokens = norm(a)
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]

h = open('/Users/gf/Downloads/mazar_martin_app.html').read()
m = re.search('"sampleListings"\\s*:\\s*(\\[.*?\\])\\s*[,}]', h, re.DOTALL)
app = json.loads(m.group(1))
domain = json.load(open('/Users/gf/Downloads/domain_forsale_lns.json'))

filled = 0
for p in app:
    if p.get('propertyType') and p.get('baths') and p.get('parking'):
        continue
    pa = street_words(p.get('address',''))
    ps = p.get('suburb','').lower().strip()
    best_match = None
    best_score = 0
    for d in domain:
        ds = d.get('suburb','').lower().strip()
        if ps and ds and ps not in ds and ds not in ps:
            continue
        da = street_words(d.get('address',''))
        score = len(set(pa) & set(da))
        if score > best_score:
            best_score = score
            best_match = d
    if best_match and best_score >= 1:
        if not p.get('propertyType') and best_match.get('propertyType'): p['propertyType'] = best_match['propertyType']
        if not p.get('baths') and best_match.get('baths'): p['baths'] = best_match['baths']
        if not p.get('parking') and best_match.get('parking'): p['parking'] = best_match['parking']
        if not p.get('landSize') and best_match.get('landSize'): p['landSize'] = best_match['landSize']
        filled += 1

open('/Users/gf/Downloads/mazar_martin_app.html','w').write(h[:m.start(1)] + json.dumps(app) + h[m.end(1):])
print(f'Filled: {filled}')
