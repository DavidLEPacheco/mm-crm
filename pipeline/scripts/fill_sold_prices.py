import json, re

def street_words(a):
    tokens = re.sub(r'[^a-z0-9]', ' ', (a or '').lower()).split()
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]

def match(a, b):
    return len(set(street_words(a)) & set(street_words(b))) >= 1

proping = json.load(open('/Users/gf/Downloads/proping_history.json'))
domain_fs = json.load(open('/Users/gf/Downloads/domain_forsale_lns.json'))

# Build proping sold lookup — price = Proping Estimate (sold price)
proping_sold = {}
for day in proping:
    for s in day.get('sold', []):
        addr = s.get('address','')
        if addr and s.get('price'):
            proping_sold[addr] = s.get('price','')

# Build domain guide price lookup
domain_guide = {}
for d in domain_fs:
    addr = d.get('address','')
    if addr and d.get('price'):
        domain_guide[addr] = d.get('price','')

print(f'Proping sold: {len(proping_sold)} | Domain guide: {len(domain_guide)}')

h = open('/Users/gf/Downloads/mazar_martin_app.html').read()
m = re.search('"soldListings"\\s*:\\s*(\\[.*?\\])\\s*[,}]', h, re.DOTALL)
sold = json.loads(m.group(1))

updated = 0
for s in sold:
    sa = s.get('address','')
    # Fill soldPrice from Proping estimate
    if not s.get('soldPrice') or s.get('soldPrice') == 'Price Withheld':
        for pa, price in proping_sold.items():
            if match(sa, pa):
                s['soldPrice'] = price
                updated += 1
                break
    # Fill guidePrice from Domain for sale cache
    if not s.get('guidePrice'):
        for da, price in domain_guide.items():
            if match(sa, da):
                s['guidePrice'] = price
                break

print(f'Sold prices updated: {updated}')
open('/Users/gf/Downloads/mazar_martin_app.html','w').write(h[:m.start(1)] + json.dumps(sold) + h[m.end(1):])
print('Done.')
