#!/usr/bin/env python3
"""
inject_domain_data.py
Reads domain_scraped_data.json (output of scrape_domain_realestate.py)
and injects the newly listed and sold properties into mazar_martin_app.html,
updating the For Sale tab (sampleListings) and Sold tab (soldListings).

Usage:
    python3 inject_domain_data.py
"""

import json, re, sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR   = Path(__file__).parent
BASE_DIR     = SCRIPT_DIR.parent
SCRAPE_FILE  = BASE_DIR / 'domain_scraped_data.json'
DASHBOARD    = BASE_DIR / 'mazar_martin_app.html'

# ── Markers already used in the dashboard ────────────────────────────────────
# We inject into the existing const D = {...} by patching sampleListings and soldListings
# We also update the snapshot counts.

PROPING_START = '/* __PROPING_DATA_START__ */'
PROPING_END   = '/* __PROPING_DATA_END__ */'

# New markers for scraped data
SCRAPED_START = '/* __SCRAPED_DATA_START__ */'
SCRAPED_END   = '/* __SCRAPED_DATA_END__ */'


def load_scrape_data():
    if not SCRAPE_FILE.exists():
        print(f'❌ {SCRAPE_FILE} not found. Run scrape_domain_realestate.py first.')
        sys.exit(1)
    return json.loads(SCRAPE_FILE.read_text())


def format_listing(p):
    """Convert scraped item to dashboard listing format."""
    return {
        'address':  p.get('address', '').strip(),
        'suburb':   p.get('suburb', '').strip(),
        'price':    p.get('price', '').strip(),
        'beds':     p.get('beds') or '',
        'baths':    p.get('baths') or '',
        'cars':     p.get('cars') or '',
        'land':     p.get('land', ''),
        'tag':      p.get('tag', 'New'),
        'agency':   p.get('agency', '').strip(),
        'agents':   p.get('agent', '').strip(),
        'url':      p.get('url', ''),
        'source':   p.get('source', ''),
    }


def format_sold(p):
    """Convert scraped sold item to dashboard sold format."""
    return {
        'date':     p.get('date', '').strip(),
        'suburb':   p.get('suburb', '').strip(),
        'price':    p.get('price', '').strip(),
        'method':   p.get('method', ''),
        'beds':     p.get('beds') or '',
        'baths':    p.get('baths') or '',
        'agency':   p.get('agency', '').strip(),
        'agents':   p.get('agent', '').strip(),
        'url':      p.get('url', ''),
        'source':   p.get('source', ''),
    }


def inject(html: str, data: dict) -> str:
    """Inject scraped data into the dashboard HTML."""

    newly_listed = [format_listing(p) for p in data.get('newly_listed', []) if p.get('address')]
    sold         = [format_sold(p)    for p in data.get('sold', [])          if p.get('address')]
    scrape_date  = data.get('date', datetime.now().strftime('%d %b %Y'))

    print(f'  Injecting {len(newly_listed)} listed, {len(sold)} sold')

    # Build the JS block
    js_block = (
        f'{SCRAPED_START}\n'
        f'const scrapedListings = {json.dumps(newly_listed, indent=2, ensure_ascii=False)};\n'
        f'const scrapedSold     = {json.dumps(sold, indent=2, ensure_ascii=False)};\n'
        f'const scrapedDate     = "{scrape_date}";\n'
        f'// Merge scraped listings into D.sampleListings if not already present\n'
        f'(function() {{\n'
        f'  const existingAddrs = new Set((D.sampleListings||[]).map(l=>l.address.toLowerCase()));\n'
        f'  scrapedListings.forEach(l => {{\n'
        f'    if (!existingAddrs.has(l.address.toLowerCase())) {{\n'
        f'      D.sampleListings.push(l);\n'
        f'      D.listingsCount = (D.listingsCount||0) + 1;\n'
        f'    }}\n'
        f'  }});\n'
        f'  const existingSold = new Set((D.soldListings||[]).map(s=>s.address ? s.address.toLowerCase() : s.suburb));\n'
        f'  scrapedSold.forEach(s => {{\n'
        f'    const key = (s.address||\"\").toLowerCase() || s.suburb;\n'
        f'    if (!existingSold.has(key)) {{\n'
        f'      D.soldListings.push(s);\n'
        f'      D.soldCount = (D.soldCount||0) + 1;\n'
        f'    }}\n'
        f'  }});\n'
        f'}})();\n'
        f'{SCRAPED_END}'
    )

    # Replace existing block if present, else insert before </script>
    if SCRAPED_START in html:
        html = re.sub(
            re.escape(SCRAPED_START) + r'.*?' + re.escape(SCRAPED_END),
            js_block,
            html,
            flags=re.DOTALL
        )
    else:
        html = html.replace('</script>', js_block + '\n</script>', 1)

    return html


def main():
    print('=' * 60)
    print('  Domain/REA Data Injector')
    print(f'  {datetime.now().strftime("%A %d %B %Y  %H:%M")}')
    print('=' * 60)

    data = load_scrape_data()
    print(f'\n  Loaded: {data["counts"]["newly_listed"]} listed, {data["counts"]["sold"]} sold')
    print(f'  Scraped at: {data.get("scraped_at","?")}')

    html = DASHBOARD.read_text(encoding='utf-8')
    html = inject(html, data)
    DASHBOARD.write_text(html, encoding='utf-8')

    print(f'\n  ✅ Dashboard updated: {DASHBOARD}')
    print('=' * 60)


if __name__ == '__main__':
    main()
