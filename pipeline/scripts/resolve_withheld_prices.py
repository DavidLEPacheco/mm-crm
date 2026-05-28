#!/usr/bin/env python3
"""
resolve_withheld_prices.py
==========================
Checks sold properties with "Price Withheld" and tries to resolve actual
sold prices from multiple sources:

  1. Proping history data (proping_history.json)
  2. PropertyValue.com.au (NSW Land Registry data, free tier)
  3. Allhomes.com.au sold data
  4. OnTheHouse cache (onthehouse_listings.json)
  5. Previously resolved prices cache (resolved_prices.json)

Resolved prices are:
  - Updated directly in the app HTML (D.soldListings)
  - Saved to resolved_prices.json for future reference
  - Logged with source attribution

Usage:
  python3 resolve_withheld_prices.py              # Full resolve
  python3 resolve_withheld_prices.py --dry-run     # Preview only
  python3 resolve_withheld_prices.py --check-new   # Only check recent (last 30 days)
"""

import json, re, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

SCRIPT_DIR   = Path(__file__).parent
APP_PATH     = SCRIPT_DIR.parent / 'mazar_martin_app.html'
DEPLOY_PATH  = SCRIPT_DIR.parent.parent / 'index.html'
PREVIEW_PATH = Path('/tmp/mm_preview/mazar_martin_app.html')

PROPING_HIST = SCRIPT_DIR.parent / 'proping_history.json'
OTH_CACHE    = SCRIPT_DIR.parent / 'onthehouse_listings.json'
RESOLVED_CACHE = SCRIPT_DIR / 'resolved_prices.json'

# Rate limiting
REQUEST_DELAY = 1.5  # seconds between web requests
MAX_WEB_CHECKS = 50  # max properties to check online per run (avoid hammering)


def normalize_addr(addr):
    """Normalize address for matching."""
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


def extract_withheld_properties(html):
    """Extract all sold properties with 'Price Withheld' from the app."""
    withheld = []
    section_start = html.find('"soldListings"')
    if section_start == -1:
        section_start = html.find("'soldListings'")
    if section_start == -1:
        return withheld

    arr_start = html.find('[', section_start)
    if arr_start == -1:
        return withheld

    depth = 0
    i = arr_start
    while i < len(html):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                chunk = html[arr_start:i+1]
                break
        i += 1
    else:
        return withheld

    # Find each property object with Price Withheld
    for m in re.finditer(
        r'\{[^{}]*?"address"\s*:\s*"([^"]+)"[^{}]*?"soldPrice"\s*:\s*"Price Withheld"[^{}]*?\}',
        chunk
    ):
        obj_str = m.group(0)
        addr = m.group(1)

        # Extract other fields
        suburb_m = re.search(r'"suburb"\s*:\s*"([^"]*)"', obj_str)
        date_m = re.search(r'"soldDate"\s*:\s*"([^"]*)"', obj_str)
        if not date_m:
            date_m = re.search(r'"date"\s*:\s*"([^"]*)"', obj_str)

        withheld.append({
            'address': addr,
            'suburb': suburb_m.group(1) if suburb_m else '',
            'soldDate': date_m.group(1) if date_m else '',
            'norm': normalize_addr(addr),
        })

    # Also check reverse order: soldPrice before address
    for m in re.finditer(
        r'\{[^{}]*?"soldPrice"\s*:\s*"Price Withheld"[^{}]*?"address"\s*:\s*"([^"]+)"[^{}]*?\}',
        chunk
    ):
        addr = m.group(1)
        norm = normalize_addr(addr)
        if not any(w['norm'] == norm for w in withheld):
            obj_str = m.group(0)
            suburb_m = re.search(r'"suburb"\s*:\s*"([^"]*)"', obj_str)
            date_m = re.search(r'"soldDate"\s*:\s*"([^"]*)"', obj_str)
            if not date_m:
                date_m = re.search(r'"date"\s*:\s*"([^"]*)"', obj_str)
            withheld.append({
                'address': addr,
                'suburb': suburb_m.group(1) if suburb_m else '',
                'soldDate': date_m.group(1) if date_m else '',
                'norm': norm,
            })

    return withheld


def load_resolved_cache():
    """Load previously resolved prices."""
    if RESOLVED_CACHE.exists():
        try:
            return json.loads(RESOLVED_CACHE.read_text())
        except Exception:
            pass
    return {}


def save_resolved_cache(cache):
    """Save resolved prices cache."""
    RESOLVED_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def check_proping(withheld_props):
    """Check Proping history for sold prices."""
    resolved = {}
    if not PROPING_HIST.exists():
        return resolved

    try:
        history = json.loads(PROPING_HIST.read_text())
    except Exception:
        return resolved

    # Build lookup from all proping sold entries
    proping_sold = {}
    for day in history:
        for entry in day.get('sold', []):
            addr = entry.get('address', '')
            price = entry.get('soldPrice', '') or entry.get('price', '')
            if addr and price and price != 'Price Withheld':
                proping_sold[normalize_addr(addr)] = price

    for prop in withheld_props:
        if prop['norm'] in proping_sold:
            resolved[prop['norm']] = {
                'address': prop['address'],
                'price': proping_sold[prop['norm']],
                'source': 'Proping',
            }

    return resolved


def check_oth_cache(withheld_props):
    """Check OnTheHouse cache for sold prices."""
    resolved = {}
    if not OTH_CACHE.exists():
        return resolved

    try:
        listings = json.loads(OTH_CACHE.read_text())
    except Exception:
        return resolved

    oth_prices = {}
    for l in listings:
        addr = l.get('address', '')
        price = l.get('soldPrice', '') or l.get('price', '')
        if addr and price and 'withheld' not in price.lower():
            oth_prices[normalize_addr(addr)] = price

    for prop in withheld_props:
        if prop['norm'] in oth_prices:
            resolved[prop['norm']] = {
                'address': prop['address'],
                'price': oth_prices[prop['norm']],
                'source': 'OnTheHouse',
            }

    return resolved


def check_propertyvalue(address, suburb):
    """Check PropertyValue.com.au for a sold price."""
    try:
        # Build the URL slug
        addr_slug = re.sub(r'[^a-z0-9\s]', '', address.lower()).strip()
        addr_slug = re.sub(r'\s+', '-', addr_slug)
        suburb_slug = suburb.lower().replace(' ', '-')

        url = f'https://www.propertyvalue.com.au/property/{addr_slug}-{suburb_slug}-nsw/0'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml',
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')

        # Look for sold price in the page
        # PropertyValue shows: "Last sold for $X,XXX,XXX on DD Mon YYYY"
        price_m = re.search(
            r'(?:sold\s+for|sale\s+price)[:\s]*\$?([\d,]+(?:\.\d+)?)',
            content, re.I
        )
        if price_m:
            price_val = price_m.group(1).replace(',', '')
            if int(float(price_val)) > 0:
                return f'${int(float(price_val)):,}'

        # Also check for JSON-LD or structured data
        price_m = re.search(r'"price"\s*:\s*"?\$?([\d,]+)"?', content)
        if price_m:
            price_val = price_m.group(1).replace(',', '')
            if int(float(price_val)) > 100000:
                return f'${int(float(price_val)):,}'

    except Exception:
        pass
    return None


def check_allhomes(address, suburb):
    """Check Allhomes.com.au for a sold price."""
    try:
        addr_slug = re.sub(r'[/]', '-', address.lower())
        addr_slug = re.sub(r'[^a-z0-9\s-]', '', addr_slug).strip()
        addr_slug = re.sub(r'\s+', '-', addr_slug)
        suburb_slug = suburb.lower().replace(' ', '-')

        url = f'https://www.allhomes.com.au/{addr_slug}-{suburb_slug}-nsw'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')

        # Allhomes shows sold price in various formats
        price_m = re.search(r'Sold\s+(?:for\s+)?\$\s*([\d,]+)', content, re.I)
        if price_m:
            price_val = price_m.group(1).replace(',', '')
            if int(price_val) > 100000:
                return f'${int(price_val):,}'

        # Check structured data
        price_m = re.search(r'"soldPrice"\s*:\s*"?\$?([\d,]+)"?', content)
        if price_m:
            price_val = price_m.group(1).replace(',', '')
            if int(price_val) > 100000:
                return f'${int(price_val):,}'

    except Exception:
        pass
    return None


def check_auhouseprices(address, suburb):
    """Check AuHousePrices.com for a sold price."""
    try:
        addr_encoded = quote(f'{address}, {suburb} NSW')
        url = (f'https://www.auhouseprices.com/sold/list/state/NSW/'
               f'addr/{quote(address + ", " + suburb + " NSW")}/')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')

        # Look for the exact address and its price
        addr_norm = normalize_addr(address)
        # AuHousePrices lists: "Address ... $X,XXX,XXX ... Date"
        for m in re.finditer(r'(\$[\d,]+)', content):
            price_val = m.group(1).replace(',', '').replace('$', '')
            if int(price_val) > 100000:
                # Check if our address is nearby in the content
                start = max(0, m.start() - 500)
                end = min(len(content), m.end() + 500)
                nearby = content[start:end].lower()
                if addr_norm[:15] in normalize_addr(nearby):
                    return f'${int(price_val):,}'

    except Exception:
        pass
    return None


def resolve_from_web(prop):
    """Try multiple web sources to resolve a withheld price."""
    address = prop['address']
    suburb = prop['suburb']

    if not suburb:
        # Try to extract suburb from address
        parts = address.split(',')
        if len(parts) > 1:
            suburb = parts[-1].strip()
            suburb = re.sub(r'\s+(?:NSW|VIC)\s*\d*$', '', suburb).strip()

    if not suburb:
        return None, None

    # Try PropertyValue first (most reliable for NSW sales)
    price = check_propertyvalue(address, suburb)
    if price:
        return price, 'PropertyValue'

    time.sleep(REQUEST_DELAY)

    # Try Allhomes
    price = check_allhomes(address, suburb)
    if price:
        return price, 'Allhomes'

    time.sleep(REQUEST_DELAY)

    # Try AuHousePrices
    price = check_auhouseprices(address, suburb)
    if price:
        return price, 'AuHousePrices'

    return None, None


def update_app_html(html, resolved_prices):
    """Replace 'Price Withheld' with actual prices in the app HTML."""
    updated = 0
    for norm_addr, info in resolved_prices.items():
        addr = info['address']
        price = info['price']

        # Find and replace the soldPrice for this specific address
        # Pattern: "address":"<addr>"...,"soldPrice":"Price Withheld"
        # Need to handle both orderings

        # Escape address for regex
        addr_esc = re.escape(addr)

        # Try: address before soldPrice
        pattern1 = (
            r'("address"\s*:\s*"' + addr_esc + r'"'
            r'[^}]*?)'
            r'"soldPrice"\s*:\s*"Price Withheld"'
        )
        replacement1 = r'\1"soldPrice":"' + price + '"'
        new_html = re.sub(pattern1, replacement1, html, count=1)

        if new_html != html:
            html = new_html
            updated += 1
            continue

        # Try: soldPrice before address
        pattern2 = (
            r'"soldPrice"\s*:\s*"Price Withheld"'
            r'([^}]*?"address"\s*:\s*"' + addr_esc + r'")'
        )
        replacement2 = '"soldPrice":"' + price + r'"\1'
        new_html = re.sub(pattern2, replacement2, html, count=1)

        if new_html != html:
            html = new_html
            updated += 1

    return html, updated


def deploy(html):
    """Write updated HTML to all locations."""
    APP_PATH.write_text(html)
    print(f"    Updated {APP_PATH}")

    for path in [DEPLOY_PATH, PREVIEW_PATH]:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html)
            print(f"    Updated {path}")
        except Exception as e:
            print(f"    ⚠️  {path}: {e}")


def main():
    dry_run = '--dry-run' in sys.argv
    check_new = '--check-new' in sys.argv

    print("=" * 60)
    print("💰 Resolve Withheld Sold Prices")
    print(f"   {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    if dry_run:
        print("   🔍 DRY RUN — no changes will be written\n")

    # Read app HTML
    html = APP_PATH.read_text()

    # Extract withheld properties
    withheld = extract_withheld_properties(html)
    print(f"\n  📊 {len(withheld)} properties with 'Price Withheld'")

    if not withheld:
        print("  ✅ No withheld prices to resolve")
        return

    # If --check-new, only check properties sold in last 30 days
    if check_new:
        cutoff = datetime.now() - timedelta(days=30)
        filtered = []
        for prop in withheld:
            if prop['soldDate']:
                try:
                    # Try various date formats
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d %b %Y', '%d-%b-%Y',
                                '%a %d/%m/%Y', '%a %d %b %Y', '%d %B %Y']:
                        try:
                            # Strip day prefix like "Sat "
                            date_str = re.sub(r'^[A-Za-z]{3}\s+', '', prop['soldDate'])
                            dt = datetime.strptime(date_str, fmt)
                            if dt >= cutoff:
                                filtered.append(prop)
                            break
                        except ValueError:
                            continue
                except Exception:
                    filtered.append(prop)  # Include if we can't parse date
            else:
                filtered.append(prop)  # Include if no date
        withheld = filtered
        print(f"  📅 Checking {len(withheld)} recent properties (last 30 days)")

    # Load cached resolutions
    cache = load_resolved_cache()
    already_cached = 0

    # ── Step 1: Check cache ──
    all_resolved = {}
    remaining = []
    for prop in withheld:
        if prop['norm'] in cache:
            all_resolved[prop['norm']] = cache[prop['norm']]
            already_cached += 1
        else:
            remaining.append(prop)

    if already_cached:
        print(f"  💾 {already_cached} prices found in cache")

    # ── Step 2: Check Proping history ──
    print("\n  📧 Checking Proping history...")
    proping_resolved = check_proping(remaining)
    if proping_resolved:
        print(f"    Found {len(proping_resolved)} prices in Proping data")
        for norm, info in proping_resolved.items():
            print(f"      ✅ {info['address']} → {info['price']}")
        all_resolved.update(proping_resolved)
        remaining = [p for p in remaining if p['norm'] not in proping_resolved]

    # ── Step 3: Check OnTheHouse cache ──
    print("  🏠 Checking OnTheHouse cache...")
    oth_resolved = check_oth_cache(remaining)
    if oth_resolved:
        print(f"    Found {len(oth_resolved)} prices in OTH cache")
        for norm, info in oth_resolved.items():
            print(f"      ✅ {info['address']} → {info['price']}")
        all_resolved.update(oth_resolved)
        remaining = [p for p in remaining if p['norm'] not in oth_resolved]

    # ── Step 4: Check web sources ──
    web_checked = 0
    web_found = 0
    if remaining:
        print(f"\n  🌐 Checking web sources for {min(len(remaining), MAX_WEB_CHECKS)} "
              f"of {len(remaining)} remaining properties...")

        for prop in remaining[:MAX_WEB_CHECKS]:
            web_checked += 1
            price, source = resolve_from_web(prop)
            if price:
                web_found += 1
                info = {
                    'address': prop['address'],
                    'price': price,
                    'source': source,
                    'resolved_date': datetime.now().strftime('%Y-%m-%d'),
                }
                all_resolved[prop['norm']] = info
                print(f"    ✅ {prop['address']} → {price} (via {source})")
            else:
                if web_checked <= 10 or web_checked % 10 == 0:
                    print(f"    ❌ {prop['address']} — still withheld")

            time.sleep(REQUEST_DELAY)

        print(f"    Checked {web_checked}, found {web_found} prices")

    # ── Summary ──
    new_resolved = {k: v for k, v in all_resolved.items() if k not in cache}
    total = len(all_resolved) - already_cached  # newly resolved this run

    print(f"\n{'='*60}")
    print(f"  📊 SUMMARY")
    print(f"{'='*60}")
    print(f"  Total withheld:        {len(withheld)}")
    print(f"  From cache:            {already_cached}")
    print(f"  From Proping:          {len(proping_resolved)}")
    print(f"  From OnTheHouse:       {len(oth_resolved)}")
    print(f"  From web:              {web_found}")
    print(f"  Still withheld:        {len(withheld) - len(all_resolved)}")

    if not all_resolved:
        print("\n  ℹ️  No prices resolved this run")
        return

    # Update cache with all resolved (including previously cached)
    cache.update(all_resolved)
    if not dry_run:
        save_resolved_cache(cache)
        print(f"\n  💾 Cache saved ({len(cache)} total resolved prices)")

    # Update HTML
    if all_resolved and not dry_run:
        html, updated = update_app_html(html, all_resolved)
        if updated:
            deploy(html)
            print(f"\n  ✅ Updated {updated} sold prices in app")
        else:
            print("\n  ℹ️  No HTML changes needed (prices may have been updated already)")
    elif dry_run:
        print("\n  (Dry run — no files modified)")


if __name__ == '__main__':
    main()
