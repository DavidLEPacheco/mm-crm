#!/usr/bin/env python3
"""
scrape_planning_data.py
========================
Scrapes NSW Planning Portal APIs for zoning, heritage, conservation,
easement, FSR, and building height data for LNS properties.

Uses the free NSW ePlanning API:
  1. Address → Property ID
  2. Property ID → All planning layers (zoning, heritage, FSR, height, etc.)
  3. Property ID → Lot/DP

Outputs: planning_data.json → injected into app as D._planningData

Usage:
  python3 scrape_planning_data.py              # Scrape all For Sale + Off Market
  python3 scrape_planning_data.py --quick      # Only scrape uncached properties
  python3 scrape_planning_data.py --force      # Re-scrape everything
"""

import json, re, os, sys, time
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests',
                    '--break-system-packages'], check=True)
    import requests

SCRIPT_DIR = Path(__file__).parent
CACHE_FILE = SCRIPT_DIR / 'planning_data.json'
APP_PATH   = SCRIPT_DIR.parent / 'mazar_martin_app.html'
DEPLOY_PATH = SCRIPT_DIR.parent.parent / 'index.html'
PREVIEW_PATH = Path('/tmp/mm_preview/index.html')

# ePlanning API base
EPLAN_BASE = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi'

# ArcGIS endpoints for spatial queries
HERITAGE_URL = 'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/EPI_Primary_Planning_Layers/MapServer/0/query'
STATE_HERITAGE_URL = 'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/HMS/Heritage/MapServer/5/query'
EASEMENT_URL = 'https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/MapServer/9/query'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Accept': 'application/json',
}


def normalize_key(address, suburb):
    """Normalize address+suburb for matching — same as app's _normSoldKey."""
    addr = re.sub(r',\s*\w.*$', '', address).strip()
    a = (addr + ' ' + suburb).lower()
    # Normalize street types to abbreviations (matching app's _normSoldKey)
    abbrevs = [
        (r'\bstreet\b', 'st'), (r'\broad\b', 'rd'), (r'\bavenue\b', 'ave'),
        (r'\bdrive\b', 'dr'), (r'\bplace\b', 'pl'), (r'\blane\b', 'ln'),
        (r'\bcrescent\b', 'cres'), (r'\bcircuit\b', 'cct'), (r'\bparade\b', 'pde'),
        (r'\bcourt\b', 'ct'), (r'\bclose\b', 'cl'), (r'\bterrace\b', 'tce'),
        (r'\bboulevard\b', 'blvd'), (r'\bway\b', 'wy'), (r'\bhighway\b', 'hwy'),
        (r'\bgrove\b', 'gr'), (r'\bsquare\b', 'sq'),
    ]
    for pattern, replacement in abbrevs:
        a = re.sub(pattern, replacement, a)
    return re.sub(r'[^a-z0-9]', '', a)


def address_to_prop_id(address, suburb):
    """Look up NSW Planning Portal property ID from address."""
    # Try full address with suburb
    query = f"{address}, {suburb}"
    try:
        r = requests.get(f"{EPLAN_BASE}/address",
                         params={'a': query, 'noOfRecords': 5},
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                return data[0].get('propId'), data[0].get('address', '')
    except Exception as e:
        pass

    # Try without suburb
    try:
        r = requests.get(f"{EPLAN_BASE}/address",
                         params={'a': address, 'noOfRecords': 5},
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                # Filter to LNS postcodes
                for item in data:
                    addr_text = (item.get('address', '') or '').upper()
                    if any(s in addr_text for s in ['2060', '2061', '2062', '2063', '2064',
                                                      '2065', '2066', '2067', '2068', '2069',
                                                      '2088', '2089', '2090', '2110', '2111']):
                        return item.get('propId'), item.get('address', '')
                # Fallback to first result
                return data[0].get('propId'), data[0].get('address', '')
    except Exception as e:
        pass

    return None, None


def get_planning_layers(prop_id):
    """Get all planning layers for a property ID."""
    try:
        r = requests.get(f"{EPLAN_BASE}/layerintersect",
                         params={'type': 'property', 'id': prop_id},
                         headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        pass
    return []


def get_lot_dp(prop_id):
    """Get Lot/DP info for a property."""
    try:
        r = requests.get(f"{EPLAN_BASE}/lot",
                         params={'propId': prop_id},
                         headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                attrs = data[0].get('attributes', {})
                return attrs.get('LotDescription', '')
    except Exception as e:
        pass
    return ''


def parse_planning_layers(layers):
    """Extract useful info from planning layer data."""
    result = {}

    for layer in (layers or []):
        title = (layer.get('title') or layer.get('layerName') or '').lower()
        attrs = layer.get('results', [])

        # Handle different response structures
        if isinstance(layer, dict) and 'layerName' in layer:
            layer_name = layer['layerName'].lower()
            results = layer.get('results', [])
        else:
            layer_name = title
            results = [layer] if isinstance(layer, dict) else []

        for item in results:
            item_title = (item.get('title') or '').lower()
            attrs_dict = item if isinstance(item, dict) else {}

            # Zoning
            if 'zone' in item_title or 'zoning' in item_title or 'land zoning' in item_title:
                zone = attrs_dict.get('Zone') or attrs_dict.get('zone') or ''
                land_use = attrs_dict.get('Land Use') or attrs_dict.get('landUse') or ''
                if zone:
                    result['zoning'] = f"{zone}: {land_use}" if land_use else zone

            # Heritage
            if 'heritage' in item_title:
                h_name = attrs_dict.get('H_NAME') or attrs_dict.get('Name') or ''
                h_sig = attrs_dict.get('SIG') or ''
                lay_class = attrs_dict.get('LAY_CLASS') or ''
                if 'conservation area' in lay_class.lower():
                    result['conservationArea'] = h_name or True
                elif h_name or 'item' in lay_class.lower():
                    result['heritage'] = h_name or True
                    if h_sig:
                        result['heritageSig'] = h_sig

            # FSR (Floor Space Ratio)
            if 'floor space' in item_title or 'fsr' in item_title:
                fsr = attrs_dict.get('FSR') or attrs_dict.get('Floor Space Ratio') or ''
                if fsr:
                    result['fsr'] = str(fsr)

            # Building Height
            if 'height' in item_title and 'building' in item_title:
                height = attrs_dict.get('Height') or attrs_dict.get('MAX_B_H') or ''
                if height:
                    result['maxHeight'] = f"{height}m" if not str(height).endswith('m') else str(height)

            # Lot Size (minimum)
            if 'lot size' in item_title:
                lot_size = attrs_dict.get('Lot Size') or attrs_dict.get('MIN_LOT_SZ') or ''
                if lot_size:
                    result['minLotSize'] = f"{lot_size}m²" if not str(lot_size).endswith('m') else str(lot_size)

    return result


def parse_layer_intersect_response(data):
    """Parse the layerintersect API response which has a specific structure."""
    result = {}
    heritage_items = []  # Collect ALL heritage/conservation entries

    if not isinstance(data, list):
        return result

    for layer_group in data:
        layer_name = (layer_group.get('layerName', '') or '').strip()
        results = layer_group.get('results', [])

        for item in results:
            title = (item.get('title', '') or '').strip()

            # Land Zoning Map
            if 'Land Zoning' in layer_name or 'Land Zoning' in title:
                zone = item.get('Zone', '')
                land_use = item.get('Land Use', '')
                if zone:
                    result['zoning'] = f"{zone}: {land_use}" if land_use else zone

            # Heritage Map — collect ALL heritage entries with full detail
            if 'Heritage' in layer_name or 'Heritage' in title:
                h_type = item.get('Heritage Type', '') or item.get('LAY_CLASS', '') or ''
                h_name = item.get('Item Name', '') or item.get('Name', '') or item.get('H_NAME', '') or ''
                h_sig = item.get('Significance', '') or item.get('SIG', '') or ''
                h_id = item.get('Item Number', '') or item.get('H_ID', '') or ''
                h_epi = item.get('EPI Name', '') or ''
                if h_type or h_name:
                    heritage_items.append({
                        'type': h_type,
                        'name': h_name,
                        'significance': h_sig,
                        'id': str(h_id) if h_id else '',
                        'epi': h_epi,
                    })

            # Floor Space Ratio
            if 'Floor Space Ratio' in layer_name or 'FSR' in title:
                fsr = item.get('FSR', '') or item.get('Floor Space Ratio', '')
                if fsr:
                    result['fsr'] = str(fsr).replace(':1', '')

            # Height of Buildings
            if 'Height' in layer_name and 'Building' in layer_name:
                h = item.get('Height', '') or item.get('MAX_B_H', '')
                if h:
                    result['maxHeight'] = f"{h}m" if not str(h).endswith('m') else str(h)

            # Minimum Lot Size
            if 'Lot Size' in layer_name:
                ls = item.get('Lot Size', '') or item.get('MIN_LOT_SZ', '')
                if ls:
                    result['minLotSize'] = f"{ls}m²"

            # Acid Sulfate Soils
            if 'Acid Sulfate' in layer_name:
                cls = item.get('Class', '') or item.get('Acid Sulfate Soils Class', '')
                if cls:
                    result['acidSulfate'] = str(cls)

    # Store heritage items as detailed array
    if heritage_items:
        result['heritageItems'] = heritage_items
        # Also set convenience flags for backward compat
        for h in heritage_items:
            ht = (h.get('type', '') or '').lower()
            if 'conservation' in ht:
                result['conservationArea'] = h.get('name', '') or True
            else:
                result['heritage'] = h.get('name', '') or True
                if h.get('significance'):
                    result['heritageSig'] = h['significance']

    return result


def query_easements(lot_dp):
    """Query NSW Spatial Services for easements on a Lot/DP.

    Uses the ArcGIS MapServer endpoint for easement parcels.
    Returns list of easement descriptions (e.g. 'Right of Way', 'Drainage').
    """
    if not lot_dp:
        return []

    easements = []
    try:
        # Parse lot and DP from e.g. "Lot 1 DP 123456" or "1/123456"
        lot_m = re.match(r'(?:Lot\s+)?(\d+)\s*(?:/|DP\s*)(\d+)', lot_dp, re.I)
        if not lot_m:
            return []

        lot_num, dp_num = lot_m.group(1), lot_m.group(2)

        # Query the easement layer by Lot/DP
        params = {
            'where': f"lotnumber='{lot_num}' AND plannumber='{dp_num}'",
            'outFields': 'easementtype,easementwidth,purpose,createdate',
            'returnGeometry': 'false',
            'f': 'json',
        }
        r = requests.get(EASEMENT_URL, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for feat in data.get('features', []):
                attrs = feat.get('attributes', {})
                etype = attrs.get('easementtype', '') or attrs.get('purpose', '') or ''
                width = attrs.get('easementwidth', '')
                if etype:
                    desc = etype.strip()
                    if width:
                        desc += f' ({width}m wide)'
                    easements.append(desc)

        # If no results from lot query, try a broader where clause
        if not easements:
            params['where'] = f"plannumber='{dp_num}'"
            r = requests.get(EASEMENT_URL, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                for feat in data.get('features', []):
                    attrs = feat.get('attributes', {})
                    etype = attrs.get('easementtype', '') or attrs.get('purpose', '') or ''
                    if etype:
                        easements.append(etype.strip())

    except Exception as e:
        pass

    return list(set(easements))  # Deduplicate


def scrape_property(address, suburb):
    """Scrape all planning data for a single property."""
    prop_id, matched_addr = address_to_prop_id(address, suburb)
    if not prop_id:
        return None

    time.sleep(0.5)  # Be polite

    # Get all planning layers
    layers = get_planning_layers(prop_id)
    result = parse_layer_intersect_response(layers)

    # Get lot/DP
    lot_dp = get_lot_dp(prop_id)
    if lot_dp:
        result['lotDP'] = lot_dp

    # Query easements using Lot/DP
    easements = query_easements(lot_dp)
    if easements:
        result['easements'] = easements

    result['_propId'] = prop_id
    result['_address'] = address
    result['_suburb'] = suburb
    result['_ts'] = time.time()

    return result


def extract_addresses_from_app():
    """Extract For Sale + Off Market addresses from the app HTML."""
    addresses = []
    if not APP_PATH.exists():
        return addresses

    html = APP_PATH.read_text()

    # Extract from sampleListings and sampleOff
    for section in ['sampleListings', 'sampleOff']:
        pattern = rf'"{section}"\s*:\s*\['
        match = re.search(pattern, html)
        if not match:
            continue

        start = match.end() - 1
        depth = 0
        i = start
        while i < len(html):
            if html[i] == '[': depth += 1
            elif html[i] == ']':
                depth -= 1
                if depth == 0:
                    chunk = html[start:i+1]
                    for addr_m in re.finditer(r'"address"\s*:\s*"([^"]+)"', chunk):
                        addr = addr_m.group(1)
                        # Find suburb near this address (look after first, then before)
                        sub_m = re.search(r'"suburb"\s*:\s*"([^"]+)"', chunk[addr_m.end():addr_m.end()+200])
                        if not sub_m:
                            # suburb may come before address in JSON key order
                            lookback = chunk[max(0, addr_m.start()-200):addr_m.start()]
                            sub_m = re.search(r'"suburb"\s*:\s*"([^"]+)"', lookback)
                        suburb = sub_m.group(1) if sub_m else ''
                        if suburb:
                            addresses.append((addr, suburb))
                    break
            i += 1

    return addresses


def load_cache():
    """Load cached planning data."""
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def save_cache(data):
    """Save planning data cache."""
    CACHE_FILE.write_text(json.dumps(data, indent=2))


def inject_planning_data(data, html_path):
    """Inject planning data into app HTML as D._planningData."""
    html = html_path.read_text()
    js_data = json.dumps(data, separators=(',', ':'))

    marker_start = '/* __PLANNING_DATA_START__ */'
    marker_end = '/* __PLANNING_DATA_END__ */'
    injection = f"{marker_start}\nD._planningData = {js_data};\n{marker_end}"

    if marker_start in html:
        start_idx = html.index(marker_start)
        end_idx = html.index(marker_end) + len(marker_end)
        html = html[:start_idx] + injection + html[end_idx:]
    else:
        # Insert after existing data blocks
        for prev_marker in ['/* __SOLD_HISTORY_END__ */', '/* __LOCAL_NEWS_END__ */',
                            '/* __PROPERTY_DATA_END__ */']:
            if prev_marker in html:
                insert_pos = html.index(prev_marker) + len(prev_marker)
                html = html[:insert_pos] + '\n' + injection + '\n' + html[insert_pos:]
                html_path.write_text(html)
                return True

        # Fallback: after const D = {...};
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

    html_path.write_text(html)
    return True


def main():
    quick = '--quick' in sys.argv
    force = '--force' in sys.argv

    print("=" * 60)
    print("NSW Planning Data Scraper — LNS Properties")
    print(f"Date: {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    # Load cache
    cache = load_cache()
    print(f"Cached: {len(cache)} properties")

    # Migrate cache keys to new normalized format (with street abbreviations)
    migrated = 0
    old_keys = list(cache.keys())
    for old_key in old_keys:
        entry = cache[old_key]
        if entry.get('_address') and entry.get('_suburb'):
            new_key = normalize_key(entry['_address'], entry['_suburb'])
            if new_key != old_key:
                cache[new_key] = entry
                del cache[old_key]
                migrated += 1
    if migrated:
        print(f"Migrated {migrated} cache keys to new normalized format")
        save_cache(cache)

    # Get addresses
    addresses = extract_addresses_from_app()
    print(f"Properties to check: {len(addresses)} (For Sale + Off Market)")

    # Filter to uncached if --quick
    to_scrape = []
    for addr, suburb in addresses:
        key = normalize_key(addr, suburb)
        if force or key not in cache:
            to_scrape.append((addr, suburb, key))
        elif quick and key in cache:
            continue
        else:
            to_scrape.append((addr, suburb, key))

    if quick:
        to_scrape = [(a, s, k) for a, s, k in to_scrape if k not in cache]

    print(f"Need to scrape: {len(to_scrape)}")

    if not to_scrape:
        print("All properties already cached.")
    else:
        # Limit batch size
        batch_size = 100 if not quick else 50
        to_scrape = to_scrape[:batch_size]
        print(f"Scraping {len(to_scrape)} properties...")

        scraped = 0
        errors = 0
        for i, (addr, suburb, key) in enumerate(to_scrape):
            print(f"  [{i+1}/{len(to_scrape)}] {addr}, {suburb}", end='')
            try:
                result = scrape_property(addr, suburb)
                if result:
                    cache[key] = result
                    zoning = result.get('zoning', '')
                    heritage = 'Heritage' if result.get('heritage') else ''
                    cons = 'Conservation' if result.get('conservationArea') else ''
                    flags = ' | '.join(filter(None, [zoning, heritage, cons]))
                    print(f" → {flags or 'OK'}")
                    scraped += 1
                else:
                    print(f" → Not found")
                    errors += 1
            except Exception as e:
                print(f" → Error: {e}")
                errors += 1

            # Rate limiting
            if i < len(to_scrape) - 1:
                time.sleep(1)

        print(f"\nScraped: {scraped} | Errors: {errors} | Total cached: {len(cache)}")

    # Save cache
    save_cache(cache)
    print(f"Saved cache: {CACHE_FILE} ({CACHE_FILE.stat().st_size:,} bytes)")

    # Inject into app
    # Include useful data + _address/_suburb metadata (needed for reindexing in app)
    inject = {}
    for key, val in cache.items():
        useful = {k: v for k, v in val.items() if (not k.startswith('_') or k in ('_address', '_suburb')) and v}
        if any(k for k in useful if not k.startswith('_')):
            inject[key] = useful

    print(f"\nInjecting data for {len(inject)} properties into app...")
    for path in [APP_PATH, DEPLOY_PATH, PREVIEW_PATH]:
        if path.exists():
            try:
                inject_planning_data(inject, path)
                print(f"  ✓ {path.name}")
            except Exception as e:
                print(f"  ✗ {path.name}: {e}")

    print(f"\nDone!")


if __name__ == '__main__':
    main()
