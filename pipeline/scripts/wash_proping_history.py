#!/usr/bin/env python3
"""
wash_proping_history.py
Enrich propingHistory entries (newly_listed, price_changes, sold, etc.) with
baths, parking, propertyType, landSize, canonical Domain URL, and planning data
(zoning, FSR, heritage, conservation, easements) from local caches.

Reads propingHistory between /* __PROPING_HIST_START__ */ and /* __PROPING_HIST_END__ */
in mazar_martin_app.html, then writes back in-place.

Usage:
    python3 wash_proping_history.py
    python3 wash_proping_history.py --dry-run
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

# Reuse lookup-building logic from wash_properties.py
import sys
sys.path.insert(0, str(Path(__file__).parent))
from wash_properties import build_lookup, _norm_addr, _normalise_property_type

HTML_FILE  = Path(__file__).resolve().parent.parent / 'mazar_martin_app.html'
BACKUP_DIR = Path(__file__).parent / 'backups'
PLANNING_JSON = Path(__file__).parent / 'planning_data.json'

# Categories in each daily propingHistory entry
SECTIONS = ['newly_listed', 'price_changes', 'sold', 'auction_changes', 'unlisted', 'over_90_days']
TARGET_FIELDS = ('propertyType', 'beds', 'baths', 'parking', 'landSize')


_STREET_ABBR = [
    (r'\bstreet\b', 'st'), (r'\broad\b', 'rd'), (r'\bavenue\b', 'ave'),
    (r'\bdrive\b', 'dr'), (r'\bplace\b', 'pl'), (r'\blane\b', 'ln'),
    (r'\bcrescent\b', 'cres'), (r'\bcircuit\b', 'cct'), (r'\bparade\b', 'pde'),
    (r'\bcourt\b', 'ct'), (r'\bclose\b', 'cl'), (r'\bterrace\b', 'tce'),
    (r'\bboulevard\b', 'blvd'), (r'\bboulevarde\b', 'blvd'), (r'\bhighway\b', 'hwy'),
]


def _norm_planning_addr(addr):
    """Normalize to planning_data.json format: abbreviated street type + suburb, lowercase, alphanum only."""
    a = (addr or '').lower()
    # Strip state/postcode
    a = re.sub(r',?\s*(?:nsw|new south wales|australia)\s*\d{0,4}\s*$', '', a)
    # Strip unit prefix like "2/" or "2A/"
    a = re.sub(r'^\d+[a-z]?\d*\s*/\s*', '', a)
    # Abbreviate street types
    for pat, repl in _STREET_ABBR:
        a = re.sub(pat, repl, a)
    # Remove commas, punctuation, spaces
    a = re.sub(r'[^a-z0-9]', '', a)
    return a


def load_planning_lookup():
    """Load planning_data.json (already keyed by normalized address with suburb)."""
    if not PLANNING_JSON.exists():
        return {}
    try:
        data = json.loads(PLANNING_JSON.read_text(encoding='utf-8'))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    # Keys are already normalized — use them as-is
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    html = HTML_FILE.read_text(encoding='utf-8')

    # Extract propingHistory block
    pat = re.compile(
        r'(/\* __PROPING_HIST_START__ \*/\s*const propingHistory = )(\[.*?\])(;\s*/\* __PROPING_HIST_END__ \*/)',
        re.DOTALL
    )
    m = pat.search(html)
    if not m:
        print('Could not locate propingHistory block')
        return 1

    before, arr_str, after = m.group(1), m.group(2), m.group(3)
    try:
        hist = json.loads(arr_str)
    except Exception as e:
        print(f'Failed to parse propingHistory: {e}')
        return 1

    # Build lookup from Domain/REA/OTH caches
    print('Building Domain/REA/OTH lookup…')
    lookup, stats = build_lookup()
    print(f'  {len(lookup)} unique addresses in lookup')

    planning = load_planning_lookup()
    print(f'  {len(planning)} addresses with planning data')

    # Backup
    if not args.dry_run:
        BACKUP_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = BACKUP_DIR / f'mazar_martin_app_{stamp}_propingwash.html'
        backup.write_bytes(html.encode('utf-8'))
        print(f'  Backup: {backup.name}')

    total = 0
    enriched_beds = enriched_baths = enriched_parking = 0
    enriched_type = enriched_url = enriched_land = 0
    enriched_zoning = enriched_heritage = 0
    missing = 0

    for day in hist:
        for section in SECTIONS:
            for p in day.get(section, []):
                total += 1
                addr = p.get('address', '')
                k = _norm_addr(addr)
                feats = lookup.get(k)
                if not feats:
                    # Try stripping unit prefix
                    mm = re.match(r'^\d+[a-z]?\d*', k)
                    if mm:
                        tail = k[mm.end():]
                        feats = lookup.get(tail) if tail else None

                if feats:
                    # Fill missing property fields
                    if not p.get('baths') and feats.get('baths'):
                        p['baths'] = feats['baths']; enriched_baths += 1
                    if not p.get('parking') and feats.get('parking'):
                        p['parking'] = feats['parking']; enriched_parking += 1
                    if not p.get('beds') and feats.get('beds'):
                        p['beds'] = feats['beds']; enriched_beds += 1
                    if not p.get('propertyType') and feats.get('propertyType'):
                        p['propertyType'] = feats['propertyType']; enriched_type += 1
                    if not p.get('landSize') and feats.get('landSize'):
                        p['landSize'] = feats['landSize']; enriched_land += 1
                    # URL — prefer canonical Domain
                    new_url = feats.get('url')
                    current = (p.get('url') or '').strip()
                    current_canonical = current and re.search(r'-\d{9,12}(?:/|$)', current) and 'domain.com.au' in current
                    if new_url and re.search(r'-\d{9,12}(?:/|$)', new_url) and not current_canonical:
                        p['url'] = new_url; enriched_url += 1
                else:
                    missing += 1

                # Planning data (uses different normalization — with suburb)
                addr_full = p.get('address', '')
                suburb = p.get('suburb', '')
                plan_key = _norm_planning_addr(f"{addr_full}, {suburb}" if suburb and suburb.lower() not in addr_full.lower() else addr_full)
                plan = planning.get(plan_key)
                if plan:
                    for fkey in ('zoning', 'fsr', 'heightLimit', 'heritage',
                                 'conservation', 'easements', 'minLotSize'):
                        val = plan.get(fkey)
                        if val and not p.get(fkey):
                            p[fkey] = val
                            if fkey == 'zoning': enriched_zoning += 1
                            if fkey in ('heritage', 'conservation'): enriched_heritage += 1

    # Write back
    if not args.dry_run:
        new_arr = json.dumps(hist, indent=2, ensure_ascii=False)
        new_html = html[:m.start()] + before + new_arr + after + html[m.end():]
        HTML_FILE.write_text(new_html, encoding='utf-8')
        print(f'\nSaved {HTML_FILE} ({len(html)} → {len(new_html)} bytes)')

    print('')
    print('=' * 60)
    print(f'Total Proping entries scanned: {total}')
    print(f'  Matched in Domain lookup:    {total - missing}')
    print(f'  No match:                    {missing}')
    print(f'  Filled beds:      +{enriched_beds}')
    print(f'  Filled baths:     +{enriched_baths}')
    print(f'  Filled parking:   +{enriched_parking}')
    print(f'  Filled propType:  +{enriched_type}')
    print(f'  Filled landSize:  +{enriched_land}')
    print(f'  Fixed URL:        +{enriched_url}')
    print(f'  Filled zoning:    +{enriched_zoning}')
    print(f'  Filled heritage:  +{enriched_heritage}')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
