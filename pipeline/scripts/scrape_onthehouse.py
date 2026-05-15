#!/usr/bin/env python3
"""
scrape_onthehouse.py
Scrapes onthehouse.com.au for all for-sale properties in LNS suburbs.
Extracts listings from embedded REDUX_DATA in page HTML.

Output: onthehouse_listings.json in parent (Downloads) directory.
"""

import json, re, time, random, sys
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4'], check=True)
    from bs4 import BeautifulSoup

SCRIPT_DIR  = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR.parent / 'onthehouse_listings.json'

LNS_SUBURBS = [
    ('mosman',           '2088'),
    ('neutral-bay',      '2089'),
    ('cremorne',         '2090'),
    ('kirribilli',       '2061'),
    ('milsons-point',    '2061'),
    ('mcmahons-point',   '2060'),
    ('north-sydney',     '2060'),
    ('waverton',         '2060'),
    ('lavender-bay',     '2060'),
    ('wollstonecraft',   '2065'),
    ('cammeray',         '2062'),
    ('crows-nest',       '2065'),
    ('kurraba-point',    '2089'),
    ('northbridge',      '2063'),
    ('castlecrag',       '2068'),
    ('willoughby',       '2068'),
    ('naremburn',        '2065'),
    ('artarmon',         '2064'),
    ('st-leonards',      '2065'),
    ('lane-cove',        '2066'),
    ('greenwich',        '2065'),
    ('longueville',      '2066'),
    ('northwood',        '2066'),
    ('middle-cove',      '2068'),
    ('north-willoughby', '2068'),
    ('riverview',        '2066'),
    ('chatswood',        '2067'),
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}


def extract_redux_listings(html_text):
    """Extract listings from REDUX_DATA embedded in page."""
    soup = BeautifulSoup(html_text, 'html.parser')
    for script in soup.find_all('script'):
        txt = script.string or ''
        if 'REDUX_DATA' in txt:
            match = re.search(r'window\.REDUX_DATA\s*=\s*({.*});', txt, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                sp = data.get('searchProperties', {}).get('results', {})
                content = sp.get('content', [])
                total = sp.get('totalElements', 0)
                total_pages = sp.get('totalPages', 1)
                return content, total, total_pages
    return [], 0, 1


def parse_listing(item):
    """Convert a REDUX listing item into our standard format."""
    addr = item.get('address', {})
    listing = item.get('listing', {})
    agency = listing.get('agency', {})
    agents = agency.get('agents', [])

    # Format address nicely
    street_num = addr.get('streetNumber', '')
    street_name = addr.get('streetName', '')
    street_type = addr.get('streetType', '')
    raw_addr = f"{street_num} {street_name} {street_type}".strip()
    # Title case
    address = raw_addr.title()

    suburb = addr.get('suburb', '').title()
    postcode = addr.get('postCode', '')
    loc = addr.get('location', {})

    agent_names = ', '.join(
        f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
        for a in agents if a.get('firstName')
    )

    price_display = ''
    if listing.get('priceDescription'):
        price_display = listing['priceDescription']
    elif listing.get('price'):
        price_display = f"${listing['price']:,.0f}" if isinstance(listing['price'], (int, float)) else str(listing['price'])

    return {
        'address': address,
        'suburb': suburb,
        'postcode': postcode,
        'price': price_display,
        'beds': item.get('beds') or '',
        'baths': item.get('baths') or '',
        'cars': item.get('carSpaces') or '',
        'landSize': item.get('landSize') or '',
        'type': item.get('type', ''),
        'agency': agency.get('name', ''),
        'agents': agent_names,
        'listedDate': listing.get('listedDate', ''),
        'lat': loc.get('lat'),
        'lon': loc.get('lon'),
        'source': 'onthehouse',
        'othId': item.get('othPropertyId', ''),
    }


def scrape_suburb(suburb_slug, postcode):
    """Scrape all pages for a suburb."""
    all_listings = []
    base_url = f'https://www.onthehouse.com.au/property-for-sale/nsw/{suburb_slug}-{postcode}'

    try:
        r = requests.get(base_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ HTTP {r.status_code}")
            return []

        content, total, total_pages = extract_redux_listings(r.text)
        all_listings.extend(content)
        print(f"  {total} listings, {total_pages} pages — got {len(content)} from page 1")

        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            time.sleep(random.uniform(1.5, 3.0))
            url = f"{base_url}?page={page}"
            r2 = requests.get(url, headers=HEADERS, timeout=30)
            if r2.status_code == 200:
                content2, _, _ = extract_redux_listings(r2.text)
                all_listings.extend(content2)
                print(f"    Page {page}: +{len(content2)}")

    except Exception as e:
        print(f"  ✗ Error: {e}")

    return [parse_listing(item) for item in all_listings]


def main():
    print("=" * 60)
    print("OnTheHouse.com.au Scraper — Lower North Shore")
    print("=" * 60)

    all_properties = []
    seen_addresses = set()

    for suburb_slug, postcode in LNS_SUBURBS:
        display = suburb_slug.replace('-', ' ').title()
        print(f"\n▶ {display} ({postcode})")
        time.sleep(random.uniform(2.0, 4.0))

        listings = scrape_suburb(suburb_slug, postcode)
        for p in listings:
            key = p['address'].lower().strip()
            if key not in seen_addresses:
                seen_addresses.add(key)
                all_properties.append(p)

    # Save
    OUTPUT_FILE.write_text(json.dumps(all_properties, indent=2))
    print(f"\n{'=' * 60}")
    print(f"Done — {len(all_properties)} unique properties saved")
    print(f"Output: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
