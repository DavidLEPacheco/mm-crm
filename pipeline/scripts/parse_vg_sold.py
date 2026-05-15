#!/usr/bin/env python3
"""
parse_vg_sold.py
=================
Parses NSW Valuer General Property Sales Information (PSI) data files
to build a complete sold history for Lower North Shore houses and semis.

Data source: https://valuation.property.nsw.gov.au/embed/propertySalesInformation
- Annual files (2001-2025): all sales for the year by LGA
- Weekly files (2026): current year sales by LGA

Filters to houses/semis only (no strata lot = not an apartment/unit).
Outputs: vg_sold_history.json → injected into app as D._soldHistory

B-record fields (semicolon-delimited, 1-indexed):
  1: Record type (B)      8: Street number     15: Settlement date
  2: LGA code             9: Street name       16: Purchase price
  3: Dealing number      10: Suburb            17: Zone code
  4: Sequence            11: Postcode          18: Nature (R=residential)
  5: Datetime            12: Area              19: Description
  6: (unused)            13: Area type (M/H)   20: Strata lot (empty=house)
  7: Unit number         14: Contract date

Usage:
  python3 parse_vg_sold.py                # Parse all downloaded data
  python3 parse_vg_sold.py --download     # Download latest then parse
  python3 parse_vg_sold.py --years 5      # Only last 5 years
"""

import json, re, os, sys, zipfile, glob
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
VG_DIR     = SCRIPT_DIR / 'vg_data'
DATA_FILE  = SCRIPT_DIR / 'vg_sold_history.json'
APP_PATH   = Path('/Users/gf/Downloads/mazar_martin_app.html')
DEPLOY_PATH = Path('/Users/gf/Downloads/mazar-martin-deploy/index.html')
PREVIEW_PATH = Path('/tmp/mm_preview/index.html')

# LGA codes for Lower North Shore councils
LNS_LGA_CODES = {
    '083': 'Hunters Hill',
    '085': 'Lane Cove',
    '087': 'Mosman',
    '088': 'North Sydney',
    '092': 'Willoughby',
}

# All LNS suburbs we care about
LNS_SUBURBS = {
    'MOSMAN', 'NEUTRAL BAY', 'CREMORNE', 'CREMORNE POINT',
    'KIRRIBILLI', 'MILSONS POINT', 'MCMAHONS POINT',
    'NORTH SYDNEY', 'WAVERTON', 'LAVENDER BAY',
    'WOLLSTONECRAFT', 'CAMMERAY', 'CROWS NEST',
    'KURRABA POINT', 'NORTHBRIDGE', 'CASTLECRAG',
    'CASTLE COVE', 'WILLOUGHBY', 'NAREMBURN',
    'ARTARMON', 'ST LEONARDS', 'LANE COVE',
    'LANE COVE NORTH', 'GREENWICH', 'LONGUEVILLE',
    'NORTHWOOD', 'MIDDLE COVE', 'NORTH WILLOUGHBY',
    'RIVERVIEW', 'CHATSWOOD', 'CHATSWOOD WEST',
    'HUNTERS HILL', 'WOOLWICH', 'HENLEY',
    'LINLEY POINT', 'BEAUTY POINT', 'CLIFTON GARDENS',
    'BALMORAL',
}


def download_latest():
    """Download latest VG data files."""
    try:
        import requests
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
        import requests

    VG_DIR.mkdir(exist_ok=True)
    base = 'https://www.valuergeneral.nsw.gov.au/__psi'

    # Download annual files for recent years if not already present
    current_year = datetime.now().year
    for year in range(current_year - 6, current_year):
        dest = VG_DIR / f'yearly_{year}.zip'
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  ✓ {year} annual already downloaded ({dest.stat().st_size:,} bytes)")
            continue
        url = f'{base}/yearly/{year}.zip'
        print(f"  Downloading {year}...")
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                dest.write_bytes(r.content)
                print(f"  ✓ {year}: {len(r.content):,} bytes")
            else:
                print(f"  ✗ {year}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ✗ {year}: {e}")

    # Download latest weekly file
    today = datetime.now()
    # Try this week and last week
    for days_back in range(0, 14):
        d = today.replace(hour=0, minute=0, second=0)
        from datetime import timedelta
        d = d - timedelta(days=days_back)
        date_str = d.strftime('%Y%m%d')
        dest = VG_DIR / f'weekly_{date_str}.zip'
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  ✓ Weekly {date_str} already downloaded")
            break
        url = f'{base}/weekly/{date_str}.zip'
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 500:
                dest.write_bytes(r.content)
                print(f"  ✓ Weekly {date_str}: {len(r.content):,} bytes")
                break
        except:
            pass


def parse_b_record(line):
    """Parse a B record from VG data file."""
    fields = line.split(';')
    if len(fields) < 20 or fields[0] != 'B':
        return None

    lga = fields[1]
    unit = fields[6].strip()
    street_num = fields[7].strip()
    street_name = fields[8].strip()
    suburb = fields[9].strip()
    postcode = fields[10].strip()
    area = fields[11].strip()
    area_type = fields[12].strip()
    contract_date = fields[13].strip()
    settlement_date = fields[14].strip()
    price_str = fields[15].strip()
    zone = fields[16].strip() if len(fields) > 16 else ''
    nature = fields[17].strip() if len(fields) > 17 else ''
    description = fields[18].strip() if len(fields) > 18 else ''
    strata_lot = fields[19].strip() if len(fields) > 19 else ''

    # Filter: only residential
    if nature and nature != 'R':
        return None

    # Filter: no strata lot = house/semi (strata = apartment/unit)
    if strata_lot:
        return None

    # Filter: must have a price
    try:
        price = int(price_str) if price_str else 0
    except ValueError:
        return None
    if price < 100000:  # Skip very low prices (likely partial interests)
        return None

    # Filter: LNS suburbs only
    if suburb.upper() not in LNS_SUBURBS:
        return None

    # Build address
    address = f"{street_num} {street_name}".strip()
    if unit:
        address = f"{unit}/{address}"

    # Parse date
    date_str = contract_date or settlement_date
    if date_str and len(date_str) == 8:
        try:
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except:
            formatted_date = date_str
    else:
        formatted_date = date_str

    # Land area
    land_size = ''
    if area:
        if area_type == 'H':
            try:
                land_size = f"{float(area) * 10000:.0f}m²"
            except:
                land_size = f"{area}ha"
        elif area_type == 'M':
            land_size = f"{area}m²"

    return {
        'address': address.title(),
        'suburb': suburb.title(),
        'postcode': postcode,
        'price': price,
        'date': formatted_date,
        'zone': zone,
        'landSize': land_size,
        'lga': lga,
    }


def extract_lns_from_dat_entries(zf, lga_codes):
    """Extract LNS house sales from .DAT entries inside a ZipFile."""
    sales = []
    for name in zf.namelist():
        if not name.endswith('.DAT'):
            continue
        basename = os.path.basename(name)
        file_lga = basename.split('_')[0]
        if file_lga not in lga_codes:
            continue
        with zf.open(name) as f:
            for raw_line in f:
                line = raw_line.decode('utf-8', errors='ignore').strip()
                if not line.startswith('B;'):
                    continue
                record = parse_b_record(line)
                if record:
                    sales.append(record)
    return sales


def extract_lns_from_zip(zip_path):
    """Extract LNS house sales from a VG zip file (handles nested zips for annual data)."""
    import io
    sales = []
    lga_codes = set(LNS_LGA_CODES.keys())

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            has_dat = any(n.endswith('.DAT') for n in names)
            has_nested_zip = any(n.endswith('.zip') for n in names)

            if has_dat:
                # Weekly file: .DAT files directly inside
                sales = extract_lns_from_dat_entries(zf, lga_codes)
            elif has_nested_zip:
                # Annual file: nested weekly zips inside
                for name in names:
                    if not name.endswith('.zip'):
                        continue
                    try:
                        with zf.open(name) as inner_file:
                            inner_bytes = io.BytesIO(inner_file.read())
                            with zipfile.ZipFile(inner_bytes) as inner_zf:
                                week_sales = extract_lns_from_dat_entries(inner_zf, lga_codes)
                                sales.extend(week_sales)
                    except Exception as e:
                        pass  # Skip corrupt inner zips
    except Exception as e:
        print(f"  ✗ Error reading {zip_path.name}: {e}")

    return sales


def build_address_key(address, suburb):
    """Normalize address for matching — must match JS _normSoldKey()."""
    # Strip suburb from address if already included
    addr = re.sub(r',\s*\w.*$', '', address).strip()
    return re.sub(r'[^a-z0-9]', '', (addr + ' ' + suburb).lower())


def main():
    do_download = '--download' in sys.argv
    max_years = 10
    if '--years' in sys.argv:
        idx = sys.argv.index('--years')
        if idx + 1 < len(sys.argv):
            max_years = int(sys.argv[idx + 1])

    print("=" * 60)
    print("NSW Valuer General — LNS House Sold History Parser")
    print(f"LGAs: {', '.join(LNS_LGA_CODES.values())}")
    print("=" * 60)

    VG_DIR.mkdir(exist_ok=True)

    if do_download:
        print("\n▶ Downloading latest VG data...")
        download_latest()

    # Find all zip files to process
    zip_files = sorted(VG_DIR.glob('*.zip'))
    if not zip_files:
        print("\nNo VG data files found. Run with --download to fetch data.")
        return

    # Filter by year range
    current_year = datetime.now().year
    min_year = current_year - max_years

    print(f"\n▶ Parsing {len(zip_files)} zip files (houses/semis only, {min_year}-{current_year})...")

    all_sales = []
    for zf in zip_files:
        # Check year from filename
        name = zf.stem
        year_match = re.search(r'(\d{4})', name)
        if year_match:
            file_year = int(year_match.group(1))
            if file_year < min_year:
                continue

        sales = extract_lns_from_zip(zf)
        if sales:
            print(f"  {zf.name}: {len(sales)} house sales")
        all_sales.extend(sales)

    print(f"\nTotal raw sales: {len(all_sales)}")

    # Build lookup: address → list of sales (most recent first)
    address_history = {}
    for sale in all_sales:
        key = build_address_key(sale['address'], sale['suburb'])
        if key not in address_history:
            address_history[key] = []
        address_history[key].append(sale)

    # Sort each property's sales by date descending
    for key in address_history:
        address_history[key].sort(key=lambda s: s.get('date', ''), reverse=True)

    # Build compact output for injection
    # Keep: last 3 sales per property, with price, date, landSize
    inject_data = {}
    for key, sales in address_history.items():
        prop = {
            'address': sales[0]['address'],
            'suburb': sales[0]['suburb'],
            'sales': [],
        }
        if sales[0].get('landSize'):
            prop['landSize'] = sales[0]['landSize']

        for s in sales[:5]:  # Keep up to 5 sales
            prop['sales'].append({
                'price': f"${s['price']:,}",
                'date': s['date'],
            })

        inject_data[key] = prop

    print(f"Unique properties with sold history: {len(inject_data)}")

    # Stats by suburb
    suburb_counts = {}
    for key, prop in inject_data.items():
        sub = prop['suburb']
        suburb_counts[sub] = suburb_counts.get(sub, 0) + 1
    for sub in sorted(suburb_counts, key=lambda s: suburb_counts[s], reverse=True):
        print(f"  {sub}: {suburb_counts[sub]} properties")

    # Save full data
    DATA_FILE.write_text(json.dumps(inject_data, indent=2))
    print(f"\nSaved to {DATA_FILE} ({DATA_FILE.stat().st_size:,} bytes)")

    # Inject into app
    print("\nInjecting into app as D._soldHistory...")
    for path in [APP_PATH, DEPLOY_PATH, PREVIEW_PATH]:
        if path.exists():
            try:
                inject_sold_history(inject_data, path)
                print(f"  ✓ {path.name}")
            except Exception as e:
                print(f"  ✗ {path.name}: {e}")

    print(f"\n✅ Done! {len(inject_data)} properties with sold history injected.")


def inject_sold_history(data, html_path):
    """Inject sold history into app HTML as D._soldHistory."""
    html = html_path.read_text()
    js_data = json.dumps(data, separators=(',', ':'))

    marker_start = '/* __SOLD_HISTORY_START__ */'
    marker_end = '/* __SOLD_HISTORY_END__ */'
    injection = f"{marker_start}\nD._soldHistory = {js_data};\n{marker_end}"

    if marker_start in html:
        start_idx = html.index(marker_start)
        end_idx = html.index(marker_end) + len(marker_end)
        html = html[:start_idx] + injection + html[end_idx:]
    else:
        # Insert after D._localNews block, or D._propertyData, or const D = {...};
        for prev_marker in ['/* __LOCAL_NEWS_END__ */', '/* __PROPERTY_DATA_END__ */']:
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


if __name__ == '__main__':
    main()
