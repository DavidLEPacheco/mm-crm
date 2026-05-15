#!/usr/bin/env python3
"""
inject_onthehouse_data.py
=========================
Cross-references onthehouse.com.au scraped data with existing app data:

1. Properties on onthehouse that match existing For Sale = update/verify
2. Properties on onthehouse NOT in existing For Sale = add to For Sale (they're online)
3. Properties in existing Off Market that appear on onthehouse = move to For Sale
4. Match Proping price guides & sold prices to listings
5. Rebuild This Week / This Month dashboard stats from all data

Usage:
    python3 inject_onthehouse_data.py
"""

import json, re, sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
BASE_DIR   = SCRIPT_DIR.parent
DASHBOARD  = BASE_DIR / 'mazar_martin_app.html'
OTH_FILE   = BASE_DIR / 'onthehouse_listings.json'
PROPING_FILE = BASE_DIR / 'proping_history.json'

TODAY = datetime.now()


def normalize_address(addr):
    """Normalize address for comparison."""
    if not addr:
        return ''
    a = addr.lower().strip()
    # Remove state/postcode suffixes
    a = re.sub(r'\s+(nsw|vic|qld|sa|wa|tas|nt|act)\s*\d{4}$', '', a)
    # Remove suburb name at end (after last comma)
    a = re.sub(r',\s*[^,]+$', '', a)
    # Normalize whitespace and punctuation
    a = re.sub(r'[,/\-]+', ' ', a)
    a = re.sub(r'\s+', ' ', a).strip()
    # Normalize common abbreviations
    for old, new in [('street', 'st'), ('road', 'rd'), ('avenue', 'ave'),
                     ('drive', 'dr'), ('place', 'pl'), ('lane', 'ln'),
                     ('crescent', 'cres'), ('court', 'ct'), ('parade', 'pde'),
                     ('boulevard', 'blvd'), ('terrace', 'tce')]:
        a = re.sub(rf'\b{old}\b', new, a)
    return a


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except:
            pass
    return default


def extract_d_from_html(html):
    """Extract the const D = {...} from dashboard HTML."""
    for line in html.split('\n'):
        if line.strip().startswith('const D ='):
            json_str = line.strip()[len('const D = '):]
            if json_str.endswith(';'):
                json_str = json_str[:-1]
            return json.loads(json_str)
    return None


def inject_d_into_html(html, D):
    """Replace const D = {...} in dashboard HTML."""
    lines = html.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('const D ='):
            new_json = json.dumps(D, separators=(',', ':'))
            lines[i] = f'const D = {new_json};'
            break
    return '\n'.join(lines)


def compute_week_month_stats(listings, sold_listings):
    """Compute This Week and This Month stats from listings data."""
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Try to parse listing dates
    def parse_date(d):
        if not d:
            return None
        for fmt in ('%Y-%m-%d', '%d %b %Y', '%d/%m/%Y', '%d/%m/%y', '%d %B %Y'):
            try:
                return datetime.strptime(str(d).strip(), fmt)
            except:
                continue
        return None

    suburbs = set()
    week_new = defaultdict(int)
    week_sold = defaultdict(int)
    month_new = defaultdict(int)
    month_sold = defaultdict(int)

    for l in listings:
        sub = l.get('suburb', '')
        if sub:
            suburbs.add(sub)
        dt = parse_date(l.get('listedDate') or l.get('listDate') or l.get('date'))
        if dt:
            if dt >= week_ago:
                week_new[sub] += 1
            if dt >= month_ago:
                month_new[sub] += 1

    for s in sold_listings:
        sub = s.get('suburb', '')
        if sub:
            suburbs.add(sub)
        dt = parse_date(s.get('soldDate') or s.get('date'))
        if dt:
            if dt >= week_ago:
                week_sold[sub] += 1
            if dt >= month_ago:
                month_sold[sub] += 1

    week_key = f"Week {now.strftime('%d %b')}"
    month_key = now.strftime('%B %Y')

    week_stats = [{'suburb': s, 'new': week_new.get(s, 0), 'sold': week_sold.get(s, 0)} for s in sorted(suburbs)]
    month_stats = [{'suburb': s, 'new': month_new.get(s, 0), 'sold': month_sold.get(s, 0)} for s in sorted(suburbs)]

    return (
        {'week': week_key, 'stats': week_stats},
        {'month': month_key, 'stats': month_stats}
    )


def main():
    print('=' * 60)
    print('OnTheHouse Data Injector + Cross-Reference')
    print(f'{datetime.now().strftime("%A %d %B %Y  %H:%M")}')
    print('=' * 60)

    # Load onthehouse data
    oth_data = load_json(OTH_FILE, [])
    if not oth_data:
        print(f'❌ No data in {OTH_FILE}. Run scrape_onthehouse.py first.')
        sys.exit(1)
    print(f'\nOnTheHouse listings: {len(oth_data)}')

    # Load proping history
    proping = load_json(PROPING_FILE, [])
    print(f'Proping history: {len(proping)} days')

    # Load dashboard HTML
    html = DASHBOARD.read_text(encoding='utf-8')
    D = extract_d_from_html(html)
    if not D:
        print('❌ Could not extract const D from dashboard')
        sys.exit(1)

    existing_forsale = D.get('sampleListings', [])
    existing_offmarket = D.get('sampleOff', [])
    existing_sold = D.get('soldListings', [])
    print(f'Existing For Sale: {len(existing_forsale)}')
    print(f'Existing Off Market: {len(existing_offmarket)}')
    print(f'Existing Sold: {len(existing_sold)}')

    # Build address index of existing For Sale
    forsale_addrs = set()
    for l in existing_forsale:
        forsale_addrs.add(normalize_address(l.get('address', '')))

    # Build address index of existing Off Market
    offmarket_addrs = {}
    for i, l in enumerate(existing_offmarket):
        offmarket_addrs[normalize_address(l.get('address', ''))] = i

    # ── Process OnTheHouse listings ──────────────────────────────────────
    new_forsale = 0
    moved_to_forsale = 0

    for oth in oth_data:
        addr_norm = normalize_address(oth.get('address', ''))
        if not addr_norm:
            continue

        # Already in For Sale?
        if addr_norm in forsale_addrs:
            continue

        # Convert to For Sale format
        listing = {
            'address': oth.get('address', ''),
            'suburb': oth.get('suburb', ''),
            'price': oth.get('price', ''),
            'beds': oth.get('beds', ''),
            'baths': oth.get('baths', ''),
            'parking': oth.get('cars', ''),
            'landSize': oth.get('landSize', ''),
            'propertyType': oth.get('type', ''),
            'agencyName': oth.get('agency', ''),
            'agentNames': oth.get('agents', ''),
            'tagText': 'New',
            'listDate': oth.get('listedDate', ''),
            'url': '',
            'source': 'onthehouse',
        }

        # Was it in Off Market? Move it to For Sale
        if addr_norm in offmarket_addrs:
            moved_to_forsale += 1
            listing['tagText'] = 'Was Off Market'

        existing_forsale.append(listing)
        forsale_addrs.add(addr_norm)
        new_forsale += 1

    print(f'\nNew For Sale from OnTheHouse: {new_forsale}')
    print(f'  (of which {moved_to_forsale} moved from Off Market)')

    # Remove properties from Off Market that are now on For Sale
    new_offmarket = []
    removed_from_offmarket = 0
    for l in existing_offmarket:
        addr_norm = normalize_address(l.get('address', ''))
        if addr_norm in forsale_addrs:
            removed_from_offmarket += 1
        else:
            new_offmarket.append(l)
    print(f'Removed from Off Market (now online): {removed_from_offmarket}')

    # ── Match Proping data ───────────────────────────────────────────────
    proping_matched = 0
    sold_from_proping = 0

    # Build lookup for For Sale by normalized address
    forsale_lookup = {}
    for l in existing_forsale:
        forsale_lookup[normalize_address(l.get('address', ''))] = l

    # Build lookup for Sold by normalized address
    sold_addrs = set()
    for s in existing_sold:
        sold_addrs.add(normalize_address(s.get('address', '')))

    for day in proping:
        # Price changes → update guide prices on For Sale listings
        for pc in day.get('price_changes', []):
            addr_norm = normalize_address(pc.get('address', ''))
            if addr_norm in forsale_lookup:
                listing = forsale_lookup[addr_norm]
                if pc.get('price'):
                    listing['guidePrice'] = pc['price']
                    proping_matched += 1

        # Newly listed from Proping
        for nl in day.get('newly_listed', []):
            addr_norm = normalize_address(nl.get('address', ''))
            if addr_norm in forsale_lookup:
                listing = forsale_lookup[addr_norm]
                if nl.get('price') and not listing.get('price'):
                    listing['price'] = nl['price']

        # Sold from Proping → add to Sold tab if not already there
        for sold in day.get('sold', []):
            addr_norm = normalize_address(sold.get('address', ''))
            if addr_norm not in sold_addrs:
                sold_entry = {
                    'address': sold.get('address', ''),
                    'suburb': sold.get('suburb', ''),
                    'soldPrice': sold.get('price', ''),
                    'method': 'Private Treaty',
                    'soldDate': day.get('date', ''),
                    'beds': sold.get('beds', ''),
                    'baths': '',
                    'agencyName': sold.get('agency', ''),
                    'agentNames': sold.get('agent', ''),
                }
                existing_sold.append(sold_entry)
                sold_addrs.add(addr_norm)
                sold_from_proping += 1

    print(f'Proping price guides matched to listings: {proping_matched}')
    print(f'Proping sold added to Sold tab: {sold_from_proping}')

    # ── Rebuild Week/Month stats ─────────────────────────────────────────
    week_stat, month_stat = compute_week_month_stats(existing_forsale, existing_sold)

    # Update or create WEEK_HISTORY and MONTH_HISTORY
    week_history = D.get('WEEK_HISTORY', [])
    month_history = D.get('MONTH_HISTORY', [])

    # Replace current week if exists, else prepend
    if week_history and week_history[0].get('week') == week_stat['week']:
        week_history[0] = week_stat
    else:
        week_history.insert(0, week_stat)
    week_history = week_history[:8]  # Keep 8 weeks

    if month_history and month_history[0].get('month') == month_stat['month']:
        month_history[0] = month_stat
    else:
        month_history.insert(0, month_stat)
    month_history = month_history[:6]  # Keep 6 months

    # ── Write back ───────────────────────────────────────────────────────
    D['sampleListings'] = existing_forsale
    D['sampleOff'] = new_offmarket
    D['soldListings'] = existing_sold
    D['WEEK_HISTORY'] = week_history
    D['MONTH_HISTORY'] = month_history

    new_html = inject_d_into_html(html, D)
    DASHBOARD.write_text(new_html, encoding='utf-8')

    print(f'\n{"=" * 60}')
    print(f'Updated dashboard:')
    print(f'  For Sale: {len(existing_forsale)} listings')
    print(f'  Off Market: {len(new_offmarket)} properties')
    print(f'  Sold: {len(existing_sold)} sales')
    print(f'  This Week: {sum(s["new"] for s in week_stat["stats"])} new, {sum(s["sold"] for s in week_stat["stats"])} sold')
    print(f'  This Month: {sum(s["new"] for s in month_stat["stats"])} new, {sum(s["sold"] for s in month_stat["stats"])} sold')
    print(f'  Dashboard: {len(new_html):,} bytes')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
