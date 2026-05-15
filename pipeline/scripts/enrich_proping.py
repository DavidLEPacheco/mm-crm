#!/usr/bin/env python3
"""
enrich_proping.py
Cross-reference proping_history.json entries against cached Domain/OTH data
to fill in missing baths, parking, propertyType, landSize, and url.

Run AFTER scrape_gmail.py and BEFORE inject_email_data.py.
"""

import json
import re
from pathlib import Path

DOWNLOADS = Path('/Users/gf/Downloads')
HISTORY_FILE = DOWNLOADS / 'proping_history.json'

# Source files for enrichment (same as wash_properties.py)
SOURCE_FILES = [
    ('domain_forsale_lns.json', 'domain'),
    ('domain_sold_lns.json',    'domain'),
    ('new_offmarket_oth.json',  'oth'),
    ('onthehouse_listings.json','oth'),
    ('fs_fetched.json',         'legacy'),
    ('sl_fetched.json',         'legacy'),
    ('lns_listings_raw.json',   'legacy'),
    ('lns_sold_raw.json',       'legacy'),
]

# ── Address normalisation (same as wash_properties.py) ────────────────────
_STATE_POSTCODE_RE = re.compile(
    r',?\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d{0,4}\s*$', re.I
)
_LNS_SUBURBS = [
    'kurraba point', 'beauty point', 'cremorne point', 'lavender bay',
    'neutral bay', 'milsons point', 'mcmahons point', 'north sydney',
    'wollstonecraft', 'crows nest', 'naremburn', 'willoughby',
    'chatswood', 'northbridge', 'castlecrag', 'castle cove',
    'middle cove', 'hunters hill', 'artarmon', 'mosman', 'cremorne',
    'kirribilli', 'waverton', 'cammeray', 'balmoral',
    'st leonards', 'greenwich', 'lane cove', 'lane cove west',
    'riverview', 'longueville', 'northwood', 'linley point',
]
_LNS_SUBURBS_RE = re.compile(
    r',?\s*(?:' + '|'.join(re.escape(s) for s in _LNS_SUBURBS) + r')\s*$',
    re.I
)
_ABBREV_MAP = [
    (r'\bst\b',   'street'), (r'\brd\b',   'road'),
    (r'\bave\b',  'avenue'), (r'\bav\b',   'avenue'),
    (r'\bdr\b',   'drive'),  (r'\bcr\b',   'crescent'),
    (r'\bcres\b', 'crescent'), (r'\bct\b', 'court'),
    (r'\bpl\b',   'place'),  (r'\bpde\b',  'parade'),
    (r'\bln\b',   'lane'),   (r'\bhwy\b',  'highway'),
    (r'\bterr\b', 'terrace'), (r'\bter\b', 'terrace'),
]

def _norm_addr(addr):
    if not addr:
        return ''
    s = str(addr).strip().lower()
    s = _STATE_POSTCODE_RE.sub('', s).strip()
    if ',' in s:
        s = s.rsplit(',', 1)[0].strip()
    s = _LNS_SUBURBS_RE.sub('', s).strip()
    s = _STATE_POSTCODE_RE.sub('', s).strip()
    for pat, repl in _ABBREV_MAP:
        s = re.sub(pat, repl, s)
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s

def _clean(v):
    if v is None:
        return ''
    if isinstance(v, (int, float)):
        return str(int(v)) if v and v == int(v) else ('' if v == 0 else str(v))
    s = str(v).strip()
    return '' if s in ('', '0', 'None', 'null') else s

def _norm_type(t):
    if not t:
        return ''
    low = t.strip().lower().replace(' ', '').replace('-', '')
    if 'town' in low: return 'Townhouse'
    if 'villa' in low: return 'Villa'
    if 'terrace' in low: return 'Terrace'
    if 'duplex' in low or 'semi' in low: return 'Semi-Detached'
    if 'apartment' in low or 'unit' in low or 'flat' in low: return 'Apartment'
    if 'house' in low or 'home' in low: return 'House'
    if 'studio' in low: return 'Studio'
    if 'land' in low or 'vacant' in low: return 'Land'
    return t.strip().title()


def build_lookup():
    """Build address → {baths, parking, propertyType, landSize, url} lookup."""
    lookup = {}
    for fname, src_type in SOURCE_FILES:
        fpath = DOWNLOADS / fname
        if not fpath.exists():
            continue
        try:
            data = json.loads(fpath.read_text())
        except Exception:
            continue
        items = data if isinstance(data, list) else data.get('listings', data.get('results', []))
        if isinstance(items, dict):
            items = list(items.values()) if all(isinstance(v, dict) for v in items.values()) else []

        for item in items:
            addr = item.get('address') or item.get('streetAddress') or ''
            key = _norm_addr(addr)
            if not key:
                continue

            rec = lookup.setdefault(key, {})

            # Extract fields based on source type
            if src_type == 'domain':
                if not rec.get('baths'):
                    rec['baths'] = _clean(item.get('baths'))
                if not rec.get('parking'):
                    rec['parking'] = _clean(item.get('parking'))
                if not rec.get('propertyType'):
                    rec['propertyType'] = _norm_type(item.get('propertyType', ''))
                if not rec.get('landSize'):
                    rec['landSize'] = _clean(item.get('landSize'))
                url = item.get('url') or ''
                if url and 'domain.com.au' in url and not rec.get('url'):
                    rec['url'] = url
            elif src_type == 'oth':
                if not rec.get('baths'):
                    rec['baths'] = _clean(item.get('baths'))
                if not rec.get('parking'):
                    rec['parking'] = _clean(item.get('cars') or item.get('parking'))
                if not rec.get('propertyType'):
                    rec['propertyType'] = _norm_type(item.get('type', ''))
                if not rec.get('landSize'):
                    rec['landSize'] = _clean(item.get('landSize'))
            else:  # legacy
                if not rec.get('baths'):
                    rec['baths'] = _clean(item.get('baths'))
                if not rec.get('parking'):
                    rec['parking'] = _clean(item.get('parking'))
                if not rec.get('propertyType'):
                    rec['propertyType'] = _norm_type(item.get('propertyType', ''))
                if not rec.get('landSize'):
                    rec['landSize'] = _clean(item.get('landSize'))

    return lookup


def enrich():
    if not HISTORY_FILE.exists():
        print('No proping_history.json found')
        return

    history = json.loads(HISTORY_FILE.read_text())
    lookup = build_lookup()
    print(f'Lookup built: {len(lookup)} addresses from cached data')

    enriched = 0
    total = 0
    for day in history:
        for section in ('newly_listed', 'price_changes', 'sold', 'auction_changes', 'unlisted', 'ninety_plus_days'):
            for item in day.get(section, []):
                total += 1
                key = _norm_addr(item.get('address', ''))
                if not key or key not in lookup:
                    continue
                ref = lookup[key]
                changed = False
                if ref.get('baths') and not item.get('baths'):
                    item['baths'] = ref['baths']
                    changed = True
                if ref.get('parking') and not item.get('parking'):
                    item['parking'] = ref['parking']
                    changed = True
                if ref.get('propertyType') and not item.get('propertyType'):
                    item['propertyType'] = ref['propertyType']
                    changed = True
                if ref.get('landSize') and not item.get('landSize'):
                    item['landSize'] = ref['landSize']
                    changed = True
                if ref.get('url') and not item.get('url') and not item.get('domain_url'):
                    item['url'] = ref['url']
                    changed = True
                if changed:
                    enriched += 1

    HISTORY_FILE.write_text(json.dumps(history, indent=2))
    print(f'Enriched {enriched}/{total} items in proping_history.json')


if __name__ == '__main__':
    enrich()
