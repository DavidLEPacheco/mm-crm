#!/usr/bin/env python3
"""
Reorder For Sale and Sold data in Mazar Martin App to match Domain sequence.
Domain scraped data (dom_ prefix IDs) goes first, maintaining Domain's newest-first order.
Sold data is sorted by soldDate descending (newest first).
"""

import json, re, os, sys
from datetime import datetime
from pathlib import Path

_DL = Path(__file__).resolve().parent.parent

APP_PATH = str(_DL / 'mazar_martin_app.html')
DEPLOY_PATH = str(_DL.parent / 'index.html')
PREVIEW_PATH = '/tmp/mm_preview/mazar_martin_app.html'


def extract_array(html, key):
    """Extract a JSON array from the HTML by key name."""
    # Try "key": [ or D.key = [
    for pattern in [f'"{key}"', f"'{key}'", f'D.{key}']:
        start = html.find(pattern)
        if start != -1:
            break
    if start == -1:
        return None, -1, -1

    arr_start = html.find('[', start)
    if arr_start == -1 or arr_start > start + 500:
        return None, -1, -1

    depth = 0
    i = arr_start
    while i < len(html):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                arr_str = html[arr_start:i+1]
                try:
                    data = json.loads(arr_str)
                    return data, arr_start, i+1
                except json.JSONDecodeError:
                    return None, arr_start, i+1
        i += 1
    return None, -1, -1


def parse_sold_date(d):
    """Parse sold date string into datetime for sorting."""
    if not d:
        return datetime(1900, 1, 1)
    # Try "31 Mar 2026" format
    for fmt in ['%d %b %Y', '%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(d.strip(), fmt)
        except:
            continue
    return datetime(1900, 1, 1)


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("📋 Reorder Data — Domain Sequence")
    print(f"   {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    with open(APP_PATH) as f:
        html = f.read()

    # Extract For Sale array
    fs_data, fs_start, fs_end = extract_array(html, 'sampleListings')
    if fs_data is None:
        print("  ❌ Could not extract sampleListings")
        return
    print(f"\n  For Sale: {len(fs_data)} listings")

    # Split into Domain-scraped (dom_ prefix) and original data
    dom_fs = [l for l in fs_data if str(l.get('id', '')).startswith('dom_')]
    orig_fs = [l for l in fs_data if not str(l.get('id', '')).startswith('dom_')]
    prop_fs = [l for l in fs_data if str(l.get('id', '')).startswith('prop_')]
    print(f"    Domain scraped: {len(dom_fs)}")
    print(f"    Proping added: {len(prop_fs)}")
    print(f"    Original spreadsheet: {len(orig_fs) - len(prop_fs)}")

    # Reorder: Domain scraped first (already in Domain's newest-first order),
    # then Proping added, then original
    reordered_fs = dom_fs + [l for l in orig_fs if str(l.get('id', '')).startswith('prop_')] + [l for l in orig_fs if not str(l.get('id', '')).startswith('prop_')]

    # Extract Sold array
    sold_data, sold_start, sold_end = extract_array(html, 'soldListings')
    if sold_data is None:
        print("  ❌ Could not extract soldListings")
        return
    print(f"\n  Sold: {len(sold_data)} listings")

    # Sort sold by date descending (newest first)
    sold_data.sort(key=lambda l: parse_sold_date(l.get('soldDate', '')), reverse=True)

    # Show date range
    dates = [l.get('soldDate', '') for l in sold_data if l.get('soldDate')]
    if dates:
        print(f"    Date range: {dates[0]} → {dates[-1]}")

    if dry_run:
        print("\n  (Dry run — no files modified)")
        return

    # Replace arrays in HTML — do sold first (later in file) then for sale
    # Find positions again since we need exact positions
    new_fs_json = json.dumps(reordered_fs)
    new_sold_json = json.dumps(sold_data)

    # Replace sold first (assuming it comes after sampleListings)
    if sold_start > fs_end:
        html = html[:sold_start] + new_sold_json + html[sold_end:]
        # fs positions unchanged
        html = html[:fs_start] + new_fs_json + html[fs_end:]
    else:
        html = html[:fs_start] + new_fs_json + html[fs_end:]
        # Recalculate sold positions after replacement
        offset = len(new_fs_json) - (fs_end - fs_start)
        html = html[:sold_start + offset] + new_sold_json + html[sold_end + offset:]

    # Write
    with open(APP_PATH, 'w') as f:
        f.write(html)
    print(f"\n  ✅ Reordered {APP_PATH}")

    for path in [DEPLOY_PATH, PREVIEW_PATH]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(html)
            print(f"  ✅ Updated {path}")
        except Exception as e:
            print(f"  ⚠️  {path}: {e}")

    print(f"\n  📦 App size: {len(html):,} bytes")


if __name__ == '__main__':
    main()
