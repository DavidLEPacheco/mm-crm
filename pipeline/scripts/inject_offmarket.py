#!/usr/bin/env python3
"""
inject_offmarket.py — Scrape OnTheHouse + Domain, find off-market, inject into app.

Cross-references OnTheHouse listings against:
  1. Domain for-sale scraped data
  2. App's existing sampleListings (For Sale)
  3. App's existing sampleOff (Off Market)
  4. App's soldListings (Sold)
  5. App's emailOffMarkets

Only genuinely new off-market properties are injected into D.sampleOff.
"""

import json, re, os, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
DOWNLOADS   = SCRIPT_DIR.parent
APP_PATH    = DOWNLOADS / 'mazar_martin_app.html'
OTH_PATH    = DOWNLOADS / 'onthehouse_listings.json'
DOMAIN_PATH = DOWNLOADS / 'domain_forsale_lns.json'
AGENCY_PATH = DOWNLOADS / 'agency_websites_listings.json'


def normalize_addr(addr):
    """Smart normalize: expand abbreviations, strip everything."""
    addr = addr.lower().strip()
    addr = re.sub(r'\bst\b', 'street', addr)
    addr = re.sub(r'\brd\b', 'road', addr)
    addr = re.sub(r'\bave\b', 'avenue', addr)
    addr = re.sub(r'\bdr\b', 'drive', addr)
    addr = re.sub(r'\bpl\b', 'place', addr)
    addr = re.sub(r'\bln\b', 'lane', addr)
    addr = re.sub(r'\bcres\b', 'crescent', addr)
    addr = re.sub(r'\bct\b', 'court', addr)
    addr = re.sub(r'\bpde\b', 'parade', addr)
    addr = re.sub(r'\btce\b', 'terrace', addr)
    addr = re.sub(r'\bcl\b', 'close', addr)
    addr = re.sub(r'\bcct\b', 'circuit', addr)
    addr = re.sub(r'\bblvd\b', 'boulevard', addr)
    return re.sub(r'[^a-z0-9]', '', addr)


def extract_json_array(html, key):
    """Extract a JSON array from the D constant by key name."""
    pattern = f'"{key}"\\s*:\\s*\\['
    m = re.search(pattern, html)
    if not m:
        return [], -1, -1
    start = m.end() - 1
    depth = 0
    for j in range(start, min(start + 3_000_000, len(html))):
        if html[j] == '[':
            depth += 1
        elif html[j] == ']':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start:j+1]), start, j+1
                except json.JSONDecodeError:
                    return [], start, j+1
    return [], -1, -1


def collect_known_addresses(html, domain_props):
    """Build a set of normalized addresses from all known sources."""
    known = set()

    # sampleListings
    listings, _, _ = extract_json_array(html, 'sampleListings')
    for p in listings:
        known.add(normalize_addr(p.get('address', '')))

    # sampleOff
    off, _, _ = extract_json_array(html, 'sampleOff')
    for p in off:
        known.add(normalize_addr(p.get('address', '')))

    # soldListings
    sold, _, _ = extract_json_array(html, 'soldListings')
    for p in sold:
        known.add(normalize_addr(p.get('address', '')))

    # emailOffMarkets
    emoff_start = html.find('emailOffMarkets')
    emoff_end = html.find('__OFFMKT_EMAIL_END__')
    if emoff_start > 0 and emoff_end > 0:
        for am in re.finditer(r'"address"\s*:\s*"([^"]*)"', html[emoff_start:emoff_end]):
            known.add(normalize_addr(am.group(1)))

    # Domain scraped
    for p in domain_props:
        addr = p.get('address', '') or p.get('name', '')
        known.add(normalize_addr(addr))

    known.discard('')
    return known


def run_scrapers():
    """Run OTH, Domain, and Agency scrapers if the scripts exist."""
    import subprocess
    scrapers = [
        ('OnTheHouse',      SCRIPT_DIR / 'scrape_onthehouse.py',      600),
        # Domain/REA uses Playwright + pagination → needs more time
        ('Domain/REA',      SCRIPT_DIR / 'scrape_domain_realestate.py', 2400),
        ('Agency Websites', SCRIPT_DIR / 'scrape_agency_websites.py',  600),
    ]
    for name, script, timeout_s in scrapers:
        if not script.exists():
            continue
        print(f"  Running {name} scraper...")
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True, text=True, timeout=timeout_s
            )
            if result.returncode == 0:
                print(f"  [OK] {name} scrape complete.")
            else:
                print(f"  [WARN] {name} exited {result.returncode}: {result.stderr[:200]}")
        except Exception as e:
            print(f"  [WARN] {name} failed: {e}")


def inject(app_path=None, scrape=True):
    """
    Main entry point. Returns dict with summary.
    """
    app_path = Path(app_path or APP_PATH)
    today = datetime.today().strftime('%d/%m/%Y')
    summary = {'new': 0, 'skipped': 0, 'deduped_off': 0}

    # Optionally run scrapers first
    if scrape:
        run_scrapers()

    # Load scraped data
    oth_props = []
    if OTH_PATH.exists():
        with open(OTH_PATH) as f:
            oth_props = json.load(f)

    domain_props = []
    if DOMAIN_PATH.exists():
        with open(DOMAIN_PATH) as f:
            domain_props = json.load(f)

    agency_props = []
    if AGENCY_PATH.exists():
        with open(AGENCY_PATH) as f:
            agency_props = json.load(f)

    print(f"  OTH listings: {len(oth_props)}")
    print(f"  Domain listings: {len(domain_props)}")
    print(f"  Agency website listings: {len(agency_props)}")

    if not oth_props and not agency_props:
        print("  [WARN] No scraped data found. Skipping off-market injection.")
        return summary

    # Read app HTML
    with open(app_path) as f:
        html = f.read()

    # Build known address set
    known = collect_known_addresses(html, domain_props)
    print(f"  Known addresses across all sources: {len(known)}")

    # Find genuinely new off-market properties from BOTH OTH and agency websites
    new_entries = []

    # OnTheHouse properties (any not on Domain are off-market)
    for p in oth_props:
        addr = p.get('address', '')
        if not addr:
            continue
        if normalize_addr(addr) in known:
            summary['skipped'] += 1
            continue

        entry = {
            'id': 'oth_' + normalize_addr(addr)[:40],
            'suburb': p.get('suburb', ''),
            'address': addr,
            'price': p.get('price', ''),
            'propertyType': p.get('property_type', p.get('type', '')),
            'beds': str(p.get('beds', p.get('bedrooms', ''))) if p.get('beds', p.get('bedrooms', '')) else '',
            'baths': str(p.get('baths', p.get('bathrooms', ''))) if p.get('baths', p.get('bathrooms', '')) else '',
            'parking': str(p.get('cars', p.get('parking', p.get('car_spaces', '')))) if p.get('cars', p.get('parking', p.get('car_spaces', ''))) else '',
            'landSize': str(p.get('land', p.get('land_size', ''))) if p.get('land', p.get('land_size', '')) else '',
            'agent': p.get('agent', p.get('agency', '')),
            'agency': p.get('agency', ''),
            'date': p.get('listed_date', today),
            'source': 'onthehouse',
            'comments': 'Found on OnTheHouse, not listed on Domain',
            'url': p.get('url', p.get('link', '')),
        }
        new_entries.append(entry)
        known.add(normalize_addr(addr))

    # Agency website properties (those NOT on Domain are exclusive/off-market)
    for p in agency_props:
        addr = p.get('address', '')
        if not addr:
            continue
        if normalize_addr(addr) in known:
            summary['skipped'] += 1
            continue

        agency = p.get('agency', '')
        entry = {
            'id': 'agency_' + normalize_addr(addr)[:40],
            'suburb': p.get('suburb', ''),
            'address': addr,
            'price': p.get('price', ''),
            'propertyType': p.get('property_type', ''),
            'beds': str(p.get('beds', '')),
            'baths': str(p.get('baths', '')),
            'parking': str(p.get('cars', '')),
            'landSize': '',
            'agent': agency,
            'agency': agency,
            'date': today,
            'source': 'agent_website',
            'comments': f'Exclusive listing on {agency} website, not on Domain',
            'url': p.get('url', ''),
        }
        new_entries.append(entry)
        known.add(normalize_addr(addr))

    summary['new'] = len(new_entries)
    print(f"  New off-market to inject: {len(new_entries)}")
    print(f"  Skipped (already known): {summary['skipped']}")

    if not new_entries:
        print("  Nothing new to inject.")
        # Still dedup existing off-market
        return _dedup_offmarket(html, app_path, summary)

    # Inject into sampleOff
    off_arr, off_start, off_end = extract_json_array(html, 'sampleOff')
    if off_start < 0:
        print("  [ERROR] Cannot find sampleOff in app HTML")
        summary['error'] = 'sampleOff not found'
        return summary

    # Find end of array and append
    m = re.search(r'"sampleOff"\s*:\s*\[', html)
    bracket_start = m.end() - 1
    depth = 0
    end_idx = None
    for j in range(bracket_start, min(bracket_start + 3_000_000, len(html))):
        if html[j] == '[': depth += 1
        elif html[j] == ']':
            depth -= 1
            if depth == 0:
                end_idx = j
                break

    entries_json = ','.join(json.dumps(e, separators=(',', ':')) for e in new_entries)
    html = html[:end_idx] + ',' + entries_json + html[end_idx:]

    # Now dedup the whole off-market list
    return _dedup_offmarket(html, app_path, summary)


def _dedup_offmarket(html, app_path, summary):
    """Remove internal duplicates from sampleOff (same address appearing twice).
    NOTE: We do NOT remove entries that also appear in sampleListings (For Sale).
    Off-market entries are permanent — once scraped, they stay with their
    original date. Only true internal duplicates (same address twice within
    sampleOff itself) are removed."""
    off, off_start, off_end = extract_json_array(html, 'sampleOff')
    seen = set()
    deduped = []
    removed = 0
    for p in off:
        key = normalize_addr(p.get('address', ''))
        if key in seen:
            removed += 1
        else:
            seen.add(key)
            deduped.append(p)

    summary['deduped_off'] = removed
    if removed:
        print(f"  Deduped off-market: removed {removed} duplicates")

    # Write back
    new_off_json = json.dumps(deduped, separators=(',', ':'))
    html = html[:off_start] + new_off_json + html[off_end:]

    # Update count
    html = re.sub(r'"offmarketCount"\s*:\s*\d+', f'"offmarketCount":{len(deduped)}', html)

    # Save
    with open(app_path, 'w') as f:
        f.write(html)
    print(f"  [OK] App updated: {len(deduped)} off-market properties")

    # Copy to deploy + preview
    for dest in [
        DOWNLOADS / 'mazar-martin-deploy' / 'index.html',
        Path('/tmp/mm_preview/mazar_martin_app.html'),
    ]:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html)
        except Exception:
            pass

    return summary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Off-market scrape + inject')
    parser.add_argument('--no-scrape', action='store_true', help='Skip running scrapers')
    args = parser.parse_args()
    inject(scrape=not args.no_scrape)
