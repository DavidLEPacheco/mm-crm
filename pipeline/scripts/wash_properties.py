#!/usr/bin/env python3
"""
wash_properties.py
Wash D.sampleListings / D.sampleOff / D.soldListings against local cached
Domain, REA, and OnTheHouse JSON dumps to fill in:

  - propertyType
  - beds / baths / parking
  - landSize
  - url  (canonical Domain listing URL with numeric ID, so hyperlinks work)

This script does NOT scrape the web — it relies on data already cached in
pipeline/*.json. If the caches are stale, re-run the existing
scrapers first (scrape_domain_realestate.py, scrape_onthehouse.py, etc.).

Usage:
    python3 wash_properties.py               # wash all three lists
    python3 wash_properties.py --dry-run     # report only
    python3 wash_properties.py --only-proping
    python3 wash_properties.py --lists for_sale
"""

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
HTML_FILE  = SCRIPT_DIR.parent / 'mazar_martin_app.html'
BACKUP_DIR = SCRIPT_DIR / 'backups'
DOWNLOADS  = SCRIPT_DIR.parent

LISTS = {
    'for_sale':   'sampleListings',
    'off_market': 'sampleOff',
    'sold':       'soldListings',
}

# Fields we want filled (and the field used in each source may vary — see normalize())
TARGET_FIELDS = ('propertyType', 'beds', 'baths', 'parking', 'landSize')

# Source files in priority order (first source wins for a given field)
SOURCE_FILES = [
    # Canonical URL + propertyType + full feature set
    ('domain_forsale_lns.json', 'domain'),
    ('domain_sold_lns.json',    'domain'),
    # OnTheHouse off-market data (has type + landSize)
    ('new_offmarket_oth.json',  'oth'),
    ('onthehouse_listings.json','oth'),
    # Legacy Domain fetches (beds/baths/parking, some landSize)
    ('fs_fetched.json',         'legacy'),
    ('sl_fetched.json',         'legacy'),
    ('lns_listings_raw.json',   'legacy'),
    ('lns_sold_raw.json',       'legacy'),
]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('wash')


# ── Address normalisation ─────────────────────────────────────────────────────

_STATE_POSTCODE_RE = re.compile(
    r',?\s*(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d{0,4}\s*$', re.I
)

# LNS suburbs — used to strip trailing suburb words when there's no comma
# separator (e.g. "17 Morella Road Mosman NSW" → "17 morella road").
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
    (r'\bst\b',      'street'),
    (r'\brd\b',      'road'),
    (r'\bave\b',     'avenue'),
    (r'\bav\b',      'avenue'),
    (r'\bdr\b',      'drive'),
    (r'\bcr\b',      'crescent'),
    (r'\bcres\b',    'crescent'),
    (r'\bct\b',      'court'),
    (r'\bpl\b',      'place'),
    (r'\bpde\b',     'parade'),
    (r'\bln\b',      'lane'),
    (r'\bhwy\b',     'highway'),
    (r'\bterr\b',    'terrace'),
    (r'\bter\b',     'terrace'),
]


def _norm_addr(addr):
    """
    Normalise an Australian street address to a stable key.

    Handles all of:
        "17 Morella Road, Mosman, NSW 2088"
        "17 Morella Road Mosman NSW"
        "17 Morella Rd, Mosman"
        "17 Morella Road"
    → "17morellaroad"
    """
    if not addr:
        return ''
    s = str(addr).strip().lower()

    # strip state + postcode (with or without preceding comma)
    s = _STATE_POSTCODE_RE.sub('', s).strip()

    # strip trailing suburb after final comma
    if ',' in s:
        s = s.rsplit(',', 1)[0].strip()

    # strip trailing LNS suburb (space-separated form)
    s = _LNS_SUBURBS_RE.sub('', s).strip()

    # a second state/postcode pass in case they were hidden behind the suburb
    s = _STATE_POSTCODE_RE.sub('', s).strip()

    # expand abbreviations
    for pat, repl in _ABBREV_MAP:
        s = re.sub(pat, repl, s)

    # collapse non-alnum
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s


# ── Data source loading ───────────────────────────────────────────────────────

def _as_clean(v):
    """Convert value to a non-empty string, treating 0/None/'' as empty."""
    if v is None:
        return ''
    if isinstance(v, (int, float)):
        if v == 0:
            return ''
        return str(int(v)) if v == int(v) else str(v)
    s = str(v).strip()
    if s in ('', '0', 'None', 'null'):
        return ''
    return s


def _normalise_property_type(t):
    if not t:
        return ''
    t = str(t).strip()
    # Expand CamelCase → "Camel Case" so substring checks find the pieces
    t_clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
    low = t_clean.lower()
    compact = low.replace(' ', '').replace('-', '')

    # Land first (before "house" because "vacantland" doesn't contain house)
    if 'vacantland' in compact or low == 'land' or 'block' in low:
        # "BlockOfUnits" is an apartment block, not land
        if 'blockofunits' in compact:
            return 'Apartment'
        if 'vacant' in low or low == 'land':
            return 'Land'
    if 'studio' in low:
        return 'Studio'
    if 'retirement' in low:
        return 'Retirement'
    if 'commercial' in low or 'office' in low or 'shop' in low or 'industrial' in low:
        return 'Commercial'
    if 'town' in low:
        return 'Townhouse'
    if 'villa' in low:
        return 'Villa'
    if 'terrace' in low:
        return 'Terrace'
    if 'duplex' in low or 'semi' in low:
        return 'Semi-Detached'
    # Apartment family — catches "ApartmentUnitFlat", "NewApartments",
    # "ApartmentUnit", "Unit", "Flat", "BlockOfUnits"
    if ('apartment' in low or 'unit' in low or 'flat' in low or
            'newapartment' in compact or 'blockofunits' in compact):
        return 'Apartment'
    if 'house' in low or 'home' in low:
        return 'House'
    if low == 'unknown':
        return ''
    return t_clean.title()


def _extract_feats(item, source_type):
    """Normalise one record from a source into our TARGET_FIELDS + url."""
    out = {}

    if source_type == 'domain':
        ptype = _normalise_property_type(item.get('propertyType', ''))
        if ptype:
            out['propertyType'] = ptype
        for k_src, k_dst in [('beds', 'beds'), ('baths', 'baths'), ('parking', 'parking')]:
            v = _as_clean(item.get(k_src))
            if v:
                out[k_dst] = v
        v = _as_clean(item.get('landSize'))
        if v:
            out['landSize'] = v
        url = item.get('url') or ''
        if url and 'domain.com.au' in url and re.search(r'-\d{9,12}(?:/|$)', url):
            out['url'] = url

    elif source_type == 'oth':
        ptype = _normalise_property_type(item.get('type', ''))
        if ptype:
            out['propertyType'] = ptype
        for k_src, k_dst in [('beds', 'beds'), ('baths', 'baths'), ('cars', 'parking')]:
            v = _as_clean(item.get(k_src))
            if v:
                out[k_dst] = v
        v = _as_clean(item.get('landSize'))
        if v:
            out['landSize'] = v
        url = item.get('url') or ''
        if url and 'onthehouse' in url:
            # Only use OnTheHouse URL if nothing else available; Domain is
            # preferred. We'll still set it but Domain passes will overwrite.
            out['url'] = url

    else:  # legacy (fs_fetched / sl_fetched / lns_*)
        for k_src, k_dst in [('beds', 'beds'), ('baths', 'baths'), ('parking', 'parking')]:
            v = _as_clean(item.get(k_src))
            if v:
                out[k_dst] = v
        v = _as_clean(item.get('landSize'))
        if v:
            out['landSize'] = v
        v = _as_clean(item.get('propertyType'))
        if v:
            out['propertyType'] = _normalise_property_type(v)

    return out


def build_lookup():
    """Build address→feature map from all cached source files."""
    lookup = {}
    stats = []

    for fname, source_type in SOURCE_FILES:
        path = DOWNLOADS / fname
        if not path.exists():
            stats.append((fname, 'MISSING', 0, 0))
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            stats.append((fname, f'ERR {e}', 0, 0))
            continue

        if isinstance(data, dict):
            # Some files wrap a list under keys like 'newly_listed' or 'sold'
            candidates = []
            for k in ('newly_listed', 'sold', 'listings', 'items', 'results'):
                if isinstance(data.get(k), list):
                    candidates.extend(data[k])
            data = candidates

        if not isinstance(data, list):
            stats.append((fname, 'not-list', 0, 0))
            continue

        added = 0
        updated = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            addr = item.get('address') or item.get('streetAddress') or ''
            if not addr:
                continue
            k = _norm_addr(addr)
            if not k:
                continue
            feats = _extract_feats(item, source_type)
            if not feats:
                continue
            if k not in lookup:
                lookup[k] = feats
                added += 1
            else:
                # Merge — don't clobber existing filled fields
                for fkey, fval in feats.items():
                    if fkey not in lookup[k]:
                        lookup[k][fkey] = fval
                        updated += 1
        stats.append((fname, 'ok', added, updated))

    return lookup, stats


# ── HTML read/write ───────────────────────────────────────────────────────────

def load_d_object(html):
    m = re.search(r'const D = (\{.*?\});', html, re.S)
    if not m:
        raise RuntimeError("Couldn't locate const D in HTML")
    return json.loads(m.group(1)), m.start(1), m.end(1)


def write_d_object(html, d_obj, start, end):
    new_json = json.dumps(d_obj, separators=(',', ':'), ensure_ascii=False)
    return html[:start] + new_json + html[end:]


def backup_html():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_DIR / f'mazar_martin_app_{stamp}_wash.html'
    dest.write_bytes(HTML_FILE.read_bytes())
    return dest


# ── Washing logic ─────────────────────────────────────────────────────────────

def needs_washing(item, only_proping=False):
    if only_proping and item.get('source') != 'proping':
        return False
    url = (item.get('url') or '').strip()
    bad_url = (not url) or ('?q=' in url) or ('search=' in url) or not re.search(r'-\d{9,12}(?:/|$)', url)
    missing = any(not _as_clean(item.get(f)) for f in TARGET_FIELDS)
    return bad_url or missing


def apply_result(item, feats):
    """Merge lookup into item without clobbering existing real data."""
    changed = {}
    if not feats:
        return changed

    # URL — overwrite any "bad" URL with a canonical Domain URL
    new_url = feats.get('url')
    if new_url and re.search(r'-\d{9,12}(?:/|$)', new_url):
        current = (item.get('url') or '').strip()
        current_is_canonical = current and re.search(r'-\d{9,12}(?:/|$)', current) and 'domain.com.au' in current
        if not current_is_canonical:
            item['url'] = new_url
            changed['url'] = new_url

    # Features — only fill when blank
    for f in TARGET_FIELDS:
        val = feats.get(f)
        if not val:
            continue
        current = _as_clean(item.get(f))
        if not current:
            item[f] = val
            changed[f] = val
    return changed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only-proping', action='store_true',
                    help='Only wash entries tagged source=proping')
    ap.add_argument('--lists', nargs='+',
                    choices=list(LISTS.keys()),
                    default=list(LISTS.keys()),
                    help='Which lists to wash')
    ap.add_argument('--dry-run', action='store_true',
                    help='Look up but do not write back')
    args = ap.parse_args()

    print('=' * 60)
    print('  Wash properties against local Domain/REA/OTH caches')
    print(f'  {datetime.now().strftime("%A %d %B %Y  %H:%M")}')
    print('=' * 60)

    log.info('Building lookup table from local JSON sources…')
    lookup, stats = build_lookup()
    for fname, status, added, updated in stats:
        log.info('  %-32s %s  (+%d new, %d merged)', fname, status, added, updated)
    log.info('Lookup table: %d unique addresses', len(lookup))

    html = HTML_FILE.read_text(encoding='utf-8')
    d_obj, d_start, d_end = load_d_object(html)

    backup = backup_html()
    log.info('Backup: %s', backup)

    per_list_stats = {}
    total_processed = 0
    total_changed = 0
    total_type_normalized = 0

    for list_key in args.lists:
        json_key = LISTS[list_key]
        items = d_obj.get(json_key, []) or []

        # ── Pass A: normalise propertyType in-place (always) ────────────
        # Cleans up raw Domain API values like "ApartmentUnitFlat",
        # "NewApartments", "BlockOfUnits", "SemiDetached", "VacantLand"
        # on every run — even entries that otherwise look complete.
        # Also clears meaningless values like "Unknown" so downstream
        # lookups can fill them in on the next pass.
        type_normalized = 0
        for itm in items:
            old = itm.get('propertyType') or ''
            if not old:
                continue
            new = _normalise_property_type(old)
            if new != old:
                itm['propertyType'] = new
                type_normalized += 1
        if type_normalized:
            log.info('  %s: normalised %d propertyType values',
                     list_key, type_normalized)
            total_type_normalized += type_normalized
            total_changed += type_normalized

        candidates = [
            (i, itm) for i, itm in enumerate(items)
            if needs_washing(itm, args.only_proping)
        ]
        log.info('')
        log.info('▶ %s (%s): %d candidates / %d total',
                 list_key, json_key, len(candidates), len(items))

        changed_here = 0
        url_fixed = 0
        feats_filled = 0
        missing = 0

        for idx, itm in candidates:
            total_processed += 1
            addr = itm.get('address', '')
            k = _norm_addr(addr)
            feats = lookup.get(k)

            if not feats:
                # Try without unit prefix (e.g. "3/125 Kurraba Road" → "125 Kurraba Road")
                m = re.match(r'^\d+[a-z]?\d*', k)
                if m:
                    tail = k[m.end():]
                    feats = lookup.get(tail) if tail else None

            if not feats:
                missing += 1
                continue

            changed = apply_result(itm, feats)
            if changed:
                changed_here += 1
                total_changed += 1
                if 'url' in changed:
                    url_fixed += 1
                if any(f in changed for f in TARGET_FIELDS):
                    feats_filled += 1

        per_list_stats[list_key] = {
            'candidates': len(candidates),
            'changed':    changed_here,
            'url_fixed':  url_fixed,
            'feats_filled': feats_filled,
            'missing':    missing,
        }
        log.info('  updated=%d  url_fixed=%d  feats_filled=%d  no_match=%d',
                 changed_here, url_fixed, feats_filled, missing)

    if not args.dry_run and total_changed:
        new_html = write_d_object(html, d_obj, d_start, d_end)
        HTML_FILE.write_text(new_html, encoding='utf-8')
        log.info('')
        log.info('Saved %s: %d → %d bytes', HTML_FILE, len(html), len(new_html))
    else:
        log.info('')
        log.info('(dry-run — no changes written)' if args.dry_run else 'No changes to write')

    print('')
    print('=' * 60)
    print('Summary')
    for list_key, s in per_list_stats.items():
        print(f'  {list_key:10s}: {s["changed"]:4d}/{s["candidates"]:4d} updated  '
              f'(url +{s["url_fixed"]}, features +{s["feats_filled"]}, no-match {s["missing"]})')
    print(f'  Total processed : {total_processed}')
    print(f'  Total changed   : {total_changed}')
    print('=' * 60)


if __name__ == '__main__':
    main()
