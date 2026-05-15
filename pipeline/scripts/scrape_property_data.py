#!/usr/bin/env python3
"""
scrape_property_data.py
========================
Scrapes property.com.au using Playwright (headed browser — KPSDK blocks headless)
for House/Semi-Detached properties from the app's For Sale + Off Market listings.

Extracts per property:
  - Land size, building size
  - Previous sold prices and dates
  - Heritage status
  - Year built, frontage

Results are saved to property_data.json and injected into the app HTML
as a lookup table accessible via D._propertyData.

The URL pattern uses /property/{slug}/ which auto-redirects to the PID page:
  https://www.property.com.au/property/3-glover-street-mosman-nsw-2088/
  → redirects to /nsw/mosman-2088/glover-st/3-pid-696651/

Usage:
  python3 scrape_property_data.py              # Full scrape (max 50/run)
  python3 scrape_property_data.py --quick      # Only new/missing properties
  python3 scrape_property_data.py --dry-run    # Preview what would be scraped
  python3 scrape_property_data.py --count 10   # Scrape 10 properties
"""

import json, re, os, sys, time, random
from pathlib import Path
from datetime import datetime

SCRIPT_DIR   = Path(__file__).parent
APP_PATH     = Path('/Users/gf/Downloads/mazar_martin_app.html')
DEPLOY_PATH  = Path('/Users/gf/Downloads/mazar-martin-deploy/index.html')
PREVIEW_PATH = Path('/tmp/mm_preview/index.html')
DATA_FILE    = SCRIPT_DIR / 'property_data.json'

# LNS suburb postcodes for URL construction
SUBURB_POSTCODES = {
    'mosman': '2088', 'neutral bay': '2089', 'cremorne': '2090',
    'cremorne point': '2090', 'kirribilli': '2061', 'milsons point': '2061',
    'mcmahons point': '2060', 'north sydney': '2060', 'waverton': '2060',
    'lavender bay': '2060', 'wollstonecraft': '2065', 'cammeray': '2062',
    'crows nest': '2065', 'kurraba point': '2089', 'northbridge': '2063',
    'castlecrag': '2068', 'castle cove': '2069', 'willoughby': '2068',
    'naremburn': '2065', 'artarmon': '2064', 'st leonards': '2065',
    'lane cove': '2066', 'lane cove north': '2066', 'greenwich': '2065',
    'longueville': '2066', 'northwood': '2066', 'middle cove': '2068',
    'north willoughby': '2068', 'riverview': '2066', 'chatswood': '2067',
    'chatswood west': '2067', 'hunters hill': '2110', 'woolwich': '2110',
    'henley': '2111', 'linley point': '2066', 'beauty point': '2088',
    'clifton gardens': '2088', 'balmoral': '2088',
}

MAX_SCRAPES_PER_RUN = 50
CACHE_DAYS = 60
PAGE_DELAY = (5, 10)

HOUSE_TYPES = re.compile(r'house|semi|duplex|villa|cottage|bungalow|terrace', re.IGNORECASE)
SKIP_TYPES  = re.compile(r'apartment|unit|flat|townhouse|studio|penthouse', re.IGNORECASE)

# JS extraction code run inside the browser page
EXTRACT_JS = """
() => {
  const result = {};
  const text = document.body.innerText;
  const html = document.body.innerHTML;

  // Land size
  let m = text.match(/Land size[:\\s]*([\d,]+)\\s*m/i) || text.match(/([\d,]+)\\s*m²\\s*land/i);
  if (m) result.landSize = m[1].replace(',','') + 'm²';

  // Building size
  m = text.match(/(?:Building|Floor|Internal)\\s*size[:\\s]*([\d,]+)\\s*m/i) || text.match(/([\d,]+)\\s*m²\\s*(?:building|floor)/i);
  if (m) result.buildingSize = m[1].replace(',','') + 'm²';

  // Heritage
  if (/heritage/i.test(text)) result.heritage = true;

  // Frontage
  m = text.match(/frontage[:\\s]*([\\d.]+)\\s*m/i);
  if (m) result.frontage = m[1] + 'm';

  // Year built
  m = text.match(/(?:year\\s*built|built\\s*in?)[:\\s]*(\\d{4})/i);
  if (m) result.yearBuilt = m[1];

  // Sales history from HTML: "YYYY Sold $X,XXX,XXX"
  result.salesHistory = [];
  const seen = new Set();
  const sp = /(\\d{4})\\s*Sold\\s*\\$([\\d,]+)/g;
  let match;
  while ((match = sp.exec(html)) !== null && result.salesHistory.length < 5) {
    if (!seen.has(match[2])) {
      seen.add(match[2]);
      result.salesHistory.push({date: match[1], price: '$' + match[2]});
    }
  }

  result.url = location.href;
  return JSON.stringify(result);
}
"""


def load_existing_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except:
            pass
    return {}


def extract_app_properties(html):
    """Extract For Sale + Off Market house/semi properties from app HTML."""
    properties = []

    for field, label in [('sampleListings', 'For Sale'), ('sampleOff', 'Off Market')]:
        for pat in [rf'"{field}"\s*:\s*\[', rf'{field}\s*:\s*\[']:
            match = re.search(pat, html)
            if match:
                break
        if not match:
            print(f"  Could not find {field}")
            continue

        start = match.end() - 1
        depth = 0
        i = start
        while i < len(html):
            if html[i] == '[': depth += 1
            elif html[i] == ']':
                depth -= 1
                if depth == 0: break
            i += 1

        try:
            arr = json.loads(html[start:i+1])
            count = 0
            for item in arr:
                prop_type = item.get('propertyType', item.get('type', ''))
                if HOUSE_TYPES.search(prop_type) and not SKIP_TYPES.search(prop_type):
                    addr = item.get('address', '')
                    suburb = item.get('suburb', '')
                    if addr and suburb:
                        properties.append({
                            'address': addr,
                            'suburb': suburb,
                            'type': prop_type,
                            'source': label,
                        })
                        count += 1
            print(f"  {label}: {count} house/semi properties")
        except json.JSONDecodeError as e:
            print(f"  ERROR parsing {field}: {e}")

    return properties


def make_property_key(address, suburb):
    return re.sub(r'[^a-z0-9]', '', (address + suburb).lower())


def get_postcode(suburb):
    """Look up postcode for a suburb."""
    key = suburb.lower().strip()
    return SUBURB_POSTCODES.get(key, '')


def build_property_url(address, suburb):
    """Build property.com.au /property/ redirect URL.
    Format: /property/{number}-{street-slug}-{suburb-slug}-nsw-{postcode}/
    This auto-redirects to the canonical PID page.
    """
    postcode = get_postcode(suburb)
    if not postcode:
        return None

    parts = address.lower().strip().split()
    if not parts:
        return None
    number = parts[0]
    street = '-'.join(parts[1:])
    sub_slug = suburb.lower().replace(' ', '-')
    slug = f"{number}-{street}-{sub_slug}-nsw-{postcode}"
    return f"https://www.property.com.au/property/{slug}/"


def scrape_with_playwright(properties, existing, max_count):
    """Scrape properties using Playwright headed browser (KPSDK requires real browser)."""
    from playwright.sync_api import sync_playwright

    results = {}
    scraped = 0
    errors = 0
    skipped = 0

    with sync_playwright() as p:
        # HEADED mode — KPSDK blocks headless browsers
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            locale='en-AU',
        )
        # Remove webdriver flag
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        for i, prop in enumerate(properties[:max_count]):
            key = make_property_key(prop['address'], prop['suburb'])
            addr_display = f"{prop['address']}, {prop['suburb']}"
            print(f"\n[{i+1}/{min(len(properties), max_count)}] {addr_display}")

            url = build_property_url(prop['address'], prop['suburb'])
            if not url:
                print(f"  ✗ Could not build URL (missing postcode for {prop['suburb']})")
                skipped += 1
                continue

            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                # Wait for redirect + KPSDK challenge + page render
                time.sleep(random.uniform(5, 8))

                current_url = page.url
                if '/pid-' not in current_url:
                    print(f"  ✗ Not redirected to property page (at {current_url[:80]})")
                    results[key] = {'_ts': time.time(), '_address': prop['address'], '_suburb': prop['suburb'], '_miss': True}
                    errors += 1
                    time.sleep(random.uniform(3, 5))
                    continue

                # Scroll to bottom to trigger lazy-loaded content
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(random.uniform(2, 4))

                # Extract data using JS
                raw = page.evaluate(EXTRACT_JS)
                data = json.loads(raw)

                if data.get('landSize') or data.get('salesHistory') or data.get('buildingSize'):
                    data['_ts'] = time.time()
                    data['_address'] = prop['address']
                    data['_suburb'] = prop['suburb']
                    data['_type'] = prop['type']
                    results[key] = data

                    land = data.get('landSize', '-')
                    bld = data.get('buildingSize', '-')
                    sales = len(data.get('salesHistory', []))
                    heritage = '🏛' if data.get('heritage') else ''
                    print(f"  ✓ Land: {land}, Build: {bld}, Sales: {sales} {heritage}")
                    for s in data.get('salesHistory', [])[:3]:
                        print(f"    {s['date']}: {s['price']}")
                    scraped += 1
                else:
                    results[key] = {'_ts': time.time(), '_address': prop['address'], '_suburb': prop['suburb'], '_miss': True}
                    print(f"  ✗ No useful data found on page")
                    errors += 1

            except Exception as e:
                results[key] = {'_ts': time.time(), '_address': prop['address'], '_suburb': prop['suburb'], '_miss': True}
                print(f"  ✗ Error: {e}")
                errors += 1

            # Rate limit
            delay = random.uniform(*PAGE_DELAY)
            print(f"  Waiting {delay:.0f}s...")
            time.sleep(delay)

        browser.close()

    return results, scraped, errors


def inject_property_data(data, html_path):
    """Inject property data into the app HTML after const D = {...};"""
    html = html_path.read_text()
    js_data = json.dumps(data, separators=(',', ':'))

    marker_start = '/* __PROPERTY_DATA_START__ */'
    marker_end = '/* __PROPERTY_DATA_END__ */'
    injection = f"{marker_start}\nD._propertyData = {js_data};\n{marker_end}"

    if marker_start in html:
        # Use string replacement (not regex) to avoid escaping issues with \u in URLs
        start_idx = html.index(marker_start)
        end_idx = html.index(marker_end) + len(marker_end)
        html = html[:start_idx] + injection + html[end_idx:]
    else:
        # Insert after const D = {...};
        d_match = re.search(r'const\s+D\s*=\s*\{', html)
        if d_match:
            start = d_match.end() - 1
            depth = 0
            i = start
            while i < len(html):
                if html[i] == '{': depth += 1
                elif html[i] == '}':
                    depth -= 1
                    if depth == 0: break
                i += 1
            semi = html.index(';', i)
            insert_pos = semi + 1
            html = html[:insert_pos] + '\n' + injection + '\n' + html[insert_pos:]
        else:
            idx = html.find('</script>')
            if idx > 0:
                html = html[:idx] + '\n' + injection + '\n' + html[idx:]

    html_path.write_text(html)
    return True


def main():
    dry_run = '--dry-run' in sys.argv
    quick = '--quick' in sys.argv

    max_count = MAX_SCRAPES_PER_RUN
    if '--count' in sys.argv:
        idx = sys.argv.index('--count')
        if idx + 1 < len(sys.argv):
            max_count = int(sys.argv[idx + 1])

    print("=" * 60)
    print("Property.com.au Scraper — House/Semi Property Data")
    print(f"Max properties per run: {max_count}")
    print(f"Mode: {'DRY RUN' if dry_run else ('QUICK' if quick else 'FULL')}")
    print("=" * 60)

    if not APP_PATH.exists():
        print(f"ERROR: App not found at {APP_PATH}")
        return

    html = APP_PATH.read_text()
    print(f"App size: {len(html):,} bytes")

    print("\nExtracting house/semi properties from app...")
    properties = extract_app_properties(html)
    print(f"Total house/semi properties: {len(properties)}")

    if not properties:
        print("No properties found. Exiting.")
        return

    existing = load_existing_data()
    print(f"Existing cached data: {len(existing)} properties")

    # Filter to properties that need scraping
    now = time.time()
    to_scrape = []
    for prop in properties:
        key = make_property_key(prop['address'], prop['suburb'])
        cached = existing.get(key)
        if cached and quick:
            continue
        if cached:
            age_days = (now - cached.get('_ts', 0)) / 86400
            if age_days < CACHE_DAYS:
                continue
        to_scrape.append(prop)

    print(f"Need to scrape: {len(to_scrape)} (skipping {len(properties) - len(to_scrape)} cached)")

    if dry_run:
        print(f"\n[DRY RUN] Would scrape (first {max_count}):")
        for p in to_scrape[:max_count]:
            url = build_property_url(p['address'], p['suburb'])
            status = '✓' if url else '✗ no postcode'
            print(f"  {status} {p['address']}, {p['suburb']} ({p['type']}) [{p['source']}]")
        if len(to_scrape) > max_count:
            print(f"  ... and {len(to_scrape) - max_count} more (next run)")
        return

    if not to_scrape:
        print("All properties are cached. Nothing to scrape.")
    else:
        new_data, scraped, errors = scrape_with_playwright(to_scrape, existing, max_count)
        existing.update(new_data)

        DATA_FILE.write_text(json.dumps(existing, indent=2))
        print(f"\n{'=' * 60}")
        print(f"Scraped: {scraped} | Errors: {errors} | Total cached: {len(existing)}")

    # Build injection data (exclude misses and metadata)
    inject_data = {}
    for key, val in existing.items():
        if val.get('_miss'):
            continue
        clean = {}
        for k, v in val.items():
            if not k.startswith('_') and v:
                clean[k] = v
        if clean:
            inject_data[key] = clean

    print(f"Injecting data for {len(inject_data)} properties into app...")

    for path in [APP_PATH, DEPLOY_PATH, PREVIEW_PATH]:
        if path.exists():
            try:
                inject_property_data(inject_data, path)
                print(f"  ✓ {path.name}")
            except Exception as e:
                print(f"  ✗ {path.name}: {e}")

    print("\nDone!")


if __name__ == '__main__':
    main()
