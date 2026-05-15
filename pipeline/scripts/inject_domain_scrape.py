#!/usr/bin/env python3
"""
Inject Domain.com.au scraped For Sale + Sold data into Mazar Martin App
=======================================================================
Reads JSON files from Chrome scrape and merges with existing app data.
- Adds new For Sale listings not already in the app
- Adds new Sold listings not already in the app
- Cross-references sold with For Sale to move properties
- Updates prices where Domain has newer data

Usage:
  python3 inject_domain_scrape.py
  python3 inject_domain_scrape.py --dry-run
"""

import json, re, os, sys
from datetime import datetime

APP_PATH = '/Users/gf/Downloads/mazar_martin_app.html'
DEPLOY_PATH = '/Users/gf/Downloads/mazar-martin-deploy/index.html'
PREVIEW_PATH = '/tmp/mm_preview/mazar_martin_app.html'
FS_JSON = '/Users/gf/Downloads/domain_forsale_lns.json'
SOLD_JSON = '/Users/gf/Downloads/domain_sold_lns.json'

def normalize_addr(addr):
    a = (addr or '').lower()
    a = re.sub(r',?\s*(nsw|new south wales|australia)\s*', '', a)
    a = re.sub(r'\bstreet\b', 'st', a)
    a = re.sub(r'\broad\b', 'rd', a)
    a = re.sub(r'\bavenue\b', 'ave', a)
    a = re.sub(r'\bdrive\b', 'dr', a)
    a = re.sub(r'\bplace\b', 'pl', a)
    a = re.sub(r'\blane\b', 'ln', a)
    a = re.sub(r'\bcrescent\b', 'cres', a)
    a = re.sub(r'\bcircuit\b', 'cct', a)
    a = re.sub(r'\bparade\b', 'pde', a)
    a = re.sub(r'\bcourt\b', 'ct', a)
    a = re.sub(r'\bclose\b', 'cl', a)
    a = re.sub(r'\bterrace\b', 'tce', a)
    a = re.sub(r'\bboulevard\b', 'blvd', a)
    a = re.sub(r'\bway\b', 'wy', a)
    a = re.sub(r'[^a-z0-9]', '', a)
    return a


def extract_existing_addresses(html, section_key):
    """Extract normalized addresses from a D.xxx array in the HTML."""
    addrs = set()
    start = html.find(f'"{section_key}"')
    if start == -1:
        start = html.find(f"'{section_key}'")
    if start == -1:
        # Try D.sectionKey = [
        start = html.find(f'D.{section_key}')
    if start == -1:
        return addrs

    arr_start = html.find('[', start)
    if arr_start == -1 or arr_start > start + 500:
        return addrs

    depth = 0
    i = arr_start
    while i < len(html):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                chunk = html[arr_start:i+1]
                for addr in re.findall(r'"address"\s*:\s*"([^"]+)"', chunk):
                    addrs.add(normalize_addr(addr))
                break
        i += 1
    return addrs


def find_array_start(html, section_key):
    """Find the position just after the opening [ of a D.xxx array (for prepending)."""
    start = html.find(f'"{section_key}"')
    if start == -1:
        start = html.find(f"'{section_key}'")
    if start == -1:
        start = html.find(f'D.{section_key}')
    if start == -1:
        return -1

    arr_start = html.find('[', start)
    if arr_start == -1:
        return -1
    return arr_start + 1  # Position right after [


def find_array_insertion_point(html, section_key):
    """Find the position just before the closing ] of a D.xxx array."""
    start = html.find(f'"{section_key}"')
    if start == -1:
        start = html.find(f"'{section_key}'")
    if start == -1:
        start = html.find(f'D.{section_key}')
    if start == -1:
        return -1

    arr_start = html.find('[', start)
    if arr_start == -1:
        return -1

    depth = 0
    i = arr_start
    while i < len(html):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                return i  # Position of closing ]
        i += 1
    return -1


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("🏠 Domain Scrape → Mazar Martin App Injection")
    print(f"   {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    if dry_run:
        print("   🔍 DRY RUN — no changes will be written")
    print("=" * 60)

    # Load scraped data
    if not os.path.exists(FS_JSON):
        print(f"  ❌ {FS_JSON} not found. Run Chrome scrape first.")
        return
    if not os.path.exists(SOLD_JSON):
        print(f"  ❌ {SOLD_JSON} not found. Run Chrome scrape first.")
        return

    with open(FS_JSON) as f:
        fs_scraped = json.load(f)
    with open(SOLD_JSON) as f:
        sold_scraped = json.load(f)

    print(f"\n  📥 Loaded {len(fs_scraped)} For Sale + {len(sold_scraped)} Sold from Domain scrape")

    # Load app HTML
    with open(APP_PATH) as f:
        html = f.read()

    # Get existing addresses
    existing_fs = extract_existing_addresses(html, 'sampleListings')
    existing_sold = extract_existing_addresses(html, 'soldListings')
    print(f"  📊 Existing app: {len(existing_fs)} For Sale, {len(existing_sold)} Sold")

    # Find new For Sale listings
    new_fs = []
    for item in fs_scraped:
        k = normalize_addr(item.get('address', ''))
        if k and k not in existing_fs and k not in existing_sold:
            new_fs.append(item)
            existing_fs.add(k)  # Prevent duplicates within scraped data

    # Find new Sold listings
    new_sold = []
    for item in sold_scraped:
        k = normalize_addr(item.get('address', ''))
        if k and k not in existing_sold:
            new_sold.append(item)
            existing_sold.add(k)

    # Find For Sale that are now Sold (cross-reference)
    sold_addrs_set = set(normalize_addr(s.get('address', '')) for s in sold_scraped)
    moved_to_sold = []
    for item in fs_scraped:
        k = normalize_addr(item.get('address', ''))
        if k in sold_addrs_set and k in existing_fs:
            moved_to_sold.append(item['address'])

    print(f"\n  ✅ New For Sale to add: {len(new_fs)}")
    print(f"  ✅ New Sold to add: {len(new_sold)}")
    print(f"  ⚠️  For Sale → Sold (to flag): {len(moved_to_sold)}")

    if new_fs:
        # Show suburb breakdown
        suburbs = {}
        for item in new_fs:
            s = item.get('suburb', 'Unknown')
            suburbs[s] = suburbs.get(s, 0) + 1
        print(f"\n  New For Sale by suburb:")
        for s in sorted(suburbs, key=suburbs.get, reverse=True)[:15]:
            print(f"    {s}: {suburbs[s]}")
        if len(suburbs) > 15:
            print(f"    ... and {len(suburbs)-15} more suburbs")

    if new_sold:
        suburbs = {}
        for item in new_sold:
            s = item.get('suburb', 'Unknown')
            suburbs[s] = suburbs.get(s, 0) + 1
        print(f"\n  New Sold by suburb:")
        for s in sorted(suburbs, key=suburbs.get, reverse=True)[:15]:
            print(f"    {s}: {suburbs[s]}")

    if dry_run:
        print("\n  (Dry run — no files modified)")
        return

    if not new_fs and not new_sold:
        print("\n  ✅ App is already up to date with Domain data")
        return

    # Inject new For Sale listings — PREPEND at start to maintain Domain's date order
    if new_fs:
        start_pos = find_array_start(html, 'sampleListings')
        if start_pos == -1:
            print("  ❌ Could not find sampleListings array in HTML")
        else:
            entries = []
            for item in new_fs:
                entry = {
                    'id': 'dom_' + normalize_addr(item.get('address', '')),
                    'suburb': item.get('suburb', ''),
                    'address': item.get('address', ''),
                    'price': item.get('price', ''),
                    'propertyType': item.get('propertyType', ''),
                    'beds': item.get('beds', ''),
                    'baths': item.get('baths', ''),
                    'parking': item.get('parking', ''),
                    'landSize': '',
                    'tagText': '',
                    'agencyName': item.get('agencyName', ''),
                    'agentNames': item.get('agentNames', ''),
                    'guidePrice': item.get('price', ''),
                    'aspect': '',
                    'auctionDetail': '',
                    'propertyDetail': '',
                    'url': item.get('url', ''),
                    'listDate': '',
                }
                entries.append(entry)

            # Prepend after opening [ to keep Domain's newest-first order
            inject_str = '\n' + ',\n'.join(json.dumps(e) for e in entries) + ','
            html = html[:start_pos] + inject_str + html[start_pos:]
            print(f"  ✅ Injected {len(entries)} new For Sale listings (newest first)")

    # Inject new Sold listings — PREPEND at start to maintain Domain's date order
    if new_sold:
        start_pos = find_array_start(html, 'soldListings')
        if start_pos == -1:
            print("  ❌ Could not find soldListings array in HTML")
        else:
            entries = []
            for item in new_sold:
                entry = {
                    'id': 'dom_sold_' + normalize_addr(item.get('address', '')),
                    'suburb': item.get('suburb', ''),
                    'address': item.get('address', ''),
                    'soldPrice': item.get('soldPrice', ''),
                    'method': item.get('method', ''),
                    'soldDate': item.get('soldDate', ''),
                    'propertyType': item.get('propertyType', ''),
                    'beds': item.get('beds', ''),
                    'baths': item.get('baths', ''),
                    'parking': item.get('parking', ''),
                    'landSize': '',
                    'agencyName': item.get('agencyName', ''),
                    'agentNames': item.get('agentNames', ''),
                    'guidePrice': '',
                    'aspect': '',
                    'propertyDetail': '',
                    'priceDiff': '',
                    'pctChange': '',
                    'url': item.get('url', ''),
                }
                entries.append(entry)

            # Prepend after opening [ to keep Domain's newest-sold-first order
            inject_str = '\n' + ',\n'.join(json.dumps(e) for e in entries) + ','
            html = html[:start_pos] + inject_str + html[start_pos:]
            print(f"  ✅ Injected {len(entries)} new Sold listings (newest first)")

    # Write updated HTML
    with open(APP_PATH, 'w') as f:
        f.write(html)
    print(f"\n  Updated {APP_PATH}")

    for path in [DEPLOY_PATH, PREVIEW_PATH]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(html)
            print(f"  Updated {path}")
        except Exception as e:
            print(f"  ⚠️  {path}: {e}")

    print(f"\n  📦 App size: {len(html):,} bytes")
    print(f"\n✅ Domain scrape injection complete!")


if __name__ == '__main__':
    main()
