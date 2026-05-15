#!/usr/bin/env python3
"""
inject_proping_data.py (FIXED)
================================
Reads ~/Downloads/proping_history.json (produced by scrape_gmail.py) and
injects only the last 48 hours of entries into mazar_martin_app.html's
propingHistory array.

Behaviour:
  - Reads ALL of proping_history.json each run (so all data is preserved).
  - Filters to entries dated in the last 48 hours by `date` field (DD/MM/YYYY).
  - Skips dates that are already present in the app's propingHistory array,
    so re-running same-day is safe (dedupe by date).
  - Appends new entries before the closing ]; — same logic as before.
  - Writes the app and copies to deploy/preview paths.

Original behaviour (hardcoded "Jan 29 - Feb 6" sample data) is replaced.
"""
import json
import re
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

APP_PATH = Path.home() / 'Downloads' / 'mazar_martin_app.html'
DEPLOY_PATH = Path.home() / 'Downloads' / 'mazar-martin-deploy' / 'index.html'
PREVIEW_PATH = Path('/tmp/mm_preview/mazar_martin_app.html')

# The scraper saves the full history here
HISTORY_PATH = Path.home() / 'Downloads' / 'proping_history.json'

# Configurable window in hours
WINDOW_HOURS = 48


def normalize_addr(addr):
    return re.sub(r'[^a-z0-9]', '', (addr or '').lower())


def parse_date_ddmmyyyy(s):
    """Parse DD/MM/YYYY → date object, return None on failure."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y').date()
    except (ValueError, AttributeError):
        return None


def load_history():
    """Load proping_history.json. Format may be a list of entries or a dict
    keyed by date. Return a list of entries each with a `date` field."""
    if not HISTORY_PATH.exists():
        sys.exit(f'ERROR: {HISTORY_PATH} not found — run scrape_gmail.py first')
    with open(HISTORY_PATH) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Could be { "DD/MM/YYYY": <entry>, ... }
        out = []
        for k, v in data.items():
            if isinstance(v, dict):
                v.setdefault('date', k)
                out.append(v)
            elif isinstance(v, list):
                # multiple entries for that date
                for e in v:
                    if isinstance(e, dict):
                        e.setdefault('date', k)
                        out.append(e)
        return out
    sys.exit(f'ERROR: unexpected proping_history.json structure: {type(data).__name__}')


def filter_recent(entries, hours):
    """Return entries whose date is within `hours` of now."""
    cutoff = datetime.now().date() - timedelta(days=max(1, hours // 24))
    out = []
    for e in entries:
        d = parse_date_ddmmyyyy(e.get('date'))
        if d and d >= cutoff:
            out.append(e)
    return out


def get_existing_dates(html, end_pos):
    """Find dates already present in propingHistory by scanning ONLY the
    propingHistory array section."""
    start = html.rfind('propingHistory', 0, end_pos)
    if start < 0:
        start = 0
    section = html[start:end_pos]
    return set(re.findall(r'"date"\s*:\s*"(\d{2}/\d{2}/\d{4})"', section))


def main():
    if not APP_PATH.exists():
        sys.exit(f'ERROR: {APP_PATH} not found')

    print(f'Reading {HISTORY_PATH}...')
    entries = load_history()
    print(f'  Total history entries: {len(entries)}')

    recent = filter_recent(entries, WINDOW_HOURS)
    print(f'  Entries in last {WINDOW_HOURS}h: {len(recent)}')

    if not recent:
        print('Nothing recent to inject — exiting.')
        return

    with open(APP_PATH) as f:
        html = f.read()

    # Find the propingHistory closing bracket via marker
    marker = '/* __PROPING_HIST_END__ */'
    idx = html.find(marker)
    if idx == -1:
        sys.exit('ERROR: __PROPING_HIST_END__ marker not found in app')
    bracket_idx = html.rfind('];', 0, idx)
    if bracket_idx == -1:
        sys.exit('ERROR: closing ]; of propingHistory not found')

    # Dedupe by date — skip entries whose date already exists in the app
    existing_dates = get_existing_dates(html, bracket_idx)
    print(f'  App already has {len(existing_dates)} unique dates in propingHistory')

    new_entries = []
    skipped = 0
    for e in recent:
        d = e.get('date')
        if d in existing_dates:
            skipped += 1
            continue
        new_entries.append(e)
        existing_dates.add(d)

    print(f'  New entries to inject: {len(new_entries)} (skipped {skipped} already-present dates)')

    if not new_entries:
        print('All recent entries already injected — nothing to do.')
        return

    # Build JSON for new entries (no outer brackets — we're appending into the existing array)
    entries_json = ',\n'.join(json.dumps(e, indent=2) for e in new_entries)
    new_html = html[:bracket_idx] + ',\n' + entries_json + '\n];' + html[bracket_idx + 2:]

    # Build sold-price + price-guide lookups for diagnostic output (kept from original)
    sold_prices = {}
    price_guides = {}
    for e in new_entries:
        for s in e.get('sold', []) or []:
            if s.get('sold_price') and s['sold_price'] != 'Price Withheld':
                key = normalize_addr(s.get('address',''))
                sold_prices[key] = {
                    'sold_price': s['sold_price'],
                    'price_guide': s.get('price_guide', s.get('price', '')),
                    'date': s.get('date',''),
                }
        for p in (e.get('price_changes', []) or []) + (e.get('newly_listed', []) or []):
            if p.get('price'):
                price_guides[normalize_addr(p.get('address',''))] = p['price']
        for s in e.get('sold', []) or []:
            if s.get('price_guide'):
                price_guides[normalize_addr(s.get('address',''))] = s['price_guide']

    print(f'  Sold prices extracted: {len(sold_prices)}')
    print(f'  Price guides extracted: {len(price_guides)}')

    # Write app
    with open(APP_PATH, 'w') as f:
        f.write(new_html)
    print(f'\nUpdated {APP_PATH}  ({len(new_html):,} bytes)')

    # Copy to deploy + preview
    for path in (DEPLOY_PATH, PREVIEW_PATH):
        try:
            os.makedirs(path.parent, exist_ok=True)
            with open(path, 'w') as f:
                f.write(new_html)
            print(f'Updated {path}')
        except Exception as ex:
            print(f'Warning: could not update {path}: {ex}')


if __name__ == '__main__':
    main()
