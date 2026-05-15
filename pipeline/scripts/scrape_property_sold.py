"""
scrape_property_sold.py — Mazar Martin Pipeline
------------------------------------------------
Searches property.com.au for sold prices of properties in soldListings
that are missing a soldPrice. Updates mazar_martin_app.html in place.

Run after fill_sold_fields.py in the pipeline.
"""
import json, re, time, urllib.request, urllib.parse
from pathlib import Path

APP_PATH = Path("/Users/gf/Downloads/mazar_martin_app.html")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-AU,en;q=0.9',
}

def search_property_com(address, suburb):
    """Search property.com.au and return sold price if found."""
    query = f"{address} {suburb} NSW"
    url = "https://www.property.com.au/search/?query=" + urllib.parse.quote(query) + "&source=address"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')

        # Look for sold price in JSON data
        # property.com.au embeds data in window.__INITIAL_STATE__ or similar
        patterns = [
            r'"soldPrice"\s*:\s*"([^"]+)"',
            r'"sale_price"\s*:\s*"([^"]+)"',
            r'"lastSalePrice"\s*:\s*"([^"]+)"',
            r'"soldFor"\s*:\s*"([^"]+)"',
            r'Sold for\s*<[^>]*>\s*\$([0-9,]+)',
            r'"price"\s*:\s*\{\s*"display"\s*:\s*"(\$[^"]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                price = m.group(1).strip()
                if price and '$' in price or price.replace(',','').isdigit():
                    return price if '$' in price else f'${price}'

        # Also check for any price near "sold" keyword
        sold_idx = html.lower().find('sold')
        if sold_idx > -1:
            chunk = html[sold_idx:sold_idx+200]
            m = re.search(r'\$([0-9,]+)', chunk)
            if m:
                amount = m.group(1).replace(',','')
                if len(amount) >= 6:  # at least $100,000
                    return f'${m.group(1)}'
    except Exception as e:
        pass
    return None

def extract(html, key):
    m = re.search('"' + key + r'"\s*:\s*(\[.*?\])\s*[,}]', html, re.DOTALL)
    return (json.loads(m.group(1)), m.start(1), m.end(1)) if m else ([], -1, -1)

html = APP_PATH.read_text(encoding="utf-8")
sold, s, e = extract(html, "soldListings")

# Only process entries missing sold price
missing = [p for p in sold if not p.get('soldPrice') or p.get('soldPrice') == 'Price Withheld']
print(f"Sold entries missing price: {len(missing)} of {len(sold)}")

updated = 0
for i, p in enumerate(missing[:50]):  # limit to 50 per run to avoid rate limiting
    addr = p.get('address', '')
    suburb = p.get('suburb', '')
    if not addr or not suburb:
        continue

    print(f"  [{i+1}] Searching: {addr}, {suburb}")
    price = search_property_com(addr, suburb)
    if price:
        p['soldPrice'] = price
        print(f"       → Found: {price}")
        updated += 1
    else:
        print(f"       → Not found")

    time.sleep(1.5)  # be respectful

print(f"\nUpdated: {updated} sold prices")

if updated:
    APP_PATH.write_text(html[:s] + json.dumps(sold) + html[e:], encoding="utf-8")
    print("Saved.")
else:
    print("No changes.")
