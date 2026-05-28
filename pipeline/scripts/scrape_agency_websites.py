#!/usr/bin/env python3
"""
scrape_agency_websites.py
=========================
Scrapes private agent/agency websites for Lower North Shore listings.

Each agency site is parsed individually because they all use different HTML
structures. Output is a single JSON file at:
    pipeline/agency_websites_listings.json

Agencies covered (10):
  1. Murphy Residential
  2. BresicWhitney (exclusive listings filter)
  3. Belle Property (LNS suburbs filter)
  4. Atlas
  5. McGrath (LNS suburbs filter)
  6. Ray White Lower North Shore
  7. Stone Real Estate (LNS suburbs filter)
  8. Raine & Horne Mosman
  9. Raine & Horne LNS
 10. Northside Realtors
"""

import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install',
                    'requests', 'beautifulsoup4', 'lxml',
                    '--break-system-packages'], check=True)
    import requests
    from bs4 import BeautifulSoup

# ── Playwright (auto-install if missing) ─────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("Installing playwright...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright',
                    '--break-system-packages'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'],
                   check=True)
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUTPUT = Path(__file__).resolve().parent.parent / 'agency_websites_listings.json'

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-AU,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

LNS_SUBURBS = {
    'Mosman', 'Cremorne', 'Cremorne Point', 'Neutral Bay', 'Kurraba Point',
    'Kirribilli', 'North Sydney', 'Waverton', 'Cammeray', 'McMahons Point',
    'Mcmahons Point', 'Naremburn', 'Willoughby', 'Wollstonecraft', 'Crows Nest',
    'Northbridge', 'Castlecrag', 'Artarmon', 'Lane Cove', 'Longueville',
    'Chatswood', 'St Leonards', 'Riverview', 'Greenwich', 'Milsons Point',
    'Lavender Bay', 'Middle Cove', 'North Willoughby',
}

# Maps lowercase suburb -> proper case
LNS_LOWER = {s.lower(): s for s in LNS_SUBURBS}

PW_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/125.0.0.0 Safari/537.36'
)

# ── Playwright shared browser (lazy init) ────────────────────────────────────
_pw_instance = None   # sync_playwright() context manager
_pw_browser = None    # Browser
_pw_context = None    # BrowserContext


def _ensure_pw():
    """Lazily launch a shared Playwright Chromium browser + context."""
    global _pw_instance, _pw_browser, _pw_context
    if _pw_context is not None:
        return _pw_context
    _pw_instance = sync_playwright().start()
    _pw_browser = _pw_instance.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ],
    )
    _pw_context = _pw_browser.new_context(
        user_agent=PW_USER_AGENT,
        viewport={'width': 1440, 'height': 900},
        locale='en-AU',
        timezone_id='Australia/Sydney',
    )
    # Stealth: remove webdriver flag
    _pw_context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return _pw_context


def _close_pw():
    """Close the shared Playwright browser if it was started."""
    global _pw_instance, _pw_browser, _pw_context
    try:
        if _pw_context:
            _pw_context.close()
        if _pw_browser:
            _pw_browser.close()
        if _pw_instance:
            _pw_instance.stop()
    except Exception:
        pass
    _pw_context = _pw_browser = _pw_instance = None


def fetch_pw(url, wait_selector=None, wait_ms=3000, timeout=30000):
    """
    Fetch a page using Playwright headless Chromium (for JS-rendered sites).
    Returns the full page HTML or None on failure.
    """
    ctx = _ensure_pw()
    page = ctx.new_page()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=timeout)
        # Wait for a specific selector if provided
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=12000)
            except PWTimeout:
                pass
        # Always wait for network to settle + extra buffer
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except PWTimeout:
            pass
        page.wait_for_timeout(wait_ms)
        return page.content()
    except Exception as e:
        print(f"    PW fetch error: {e}")
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass


def fetch(url, timeout=30):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
        print(f"    HTTP {r.status_code} for {url[:80]}")
    except Exception as e:
        print(f"    Fetch error: {e}")
    return None


def extract_suburb(text):
    """Try to find an LNS suburb in a string."""
    if not text:
        return ''
    text_lower = text.lower()
    # Sort by length so multi-word suburbs match first
    for sub_lower in sorted(LNS_LOWER.keys(), key=len, reverse=True):
        if sub_lower in text_lower:
            return LNS_LOWER[sub_lower]
    return ''


def extract_beds_baths_cars(text):
    """Pull bed/bath/car counts from a snippet of text."""
    out = {'beds': '', 'baths': '', 'cars': ''}
    if not text:
        return out
    m = re.search(r'(\d+)\s*(?:bed|bd)', text, re.I)
    if m: out['beds'] = m.group(1)
    m = re.search(r'(\d+)\s*(?:bath|ba)', text, re.I)
    if m: out['baths'] = m.group(1)
    m = re.search(r'(\d+)\s*(?:car|garage|park)', text, re.I)
    if m: out['cars'] = m.group(1)
    return out


def extract_price(text):
    if not text:
        return ''
    m = re.search(r'\$[\d,]+(?:\.\d+)?\s*(?:m|mil|million|k)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?\s*(?:m|mil|million|k)?)?', text, re.I)
    return m.group(0) if m else (text.strip() if 'contact' in text.lower() or 'auction' in text.lower() or 'guide' in text.lower() else '')


def make_entry(agency, address, suburb='', price='', beds='', baths='', cars='', url='', extra=None):
    """Standardize one listing record."""
    if not suburb:
        suburb = extract_suburb(address)
    return {
        'agency': agency,
        'address': address.strip(),
        'suburb': suburb,
        'price': price.strip() if price else '',
        'beds': str(beds) if beds else '',
        'baths': str(baths) if baths else '',
        'cars': str(cars) if cars else '',
        'url': url,
        'source': 'agent_website',
        **(extra or {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-agency scrapers
# ─────────────────────────────────────────────────────────────────────────────

def scrape_murphy():
    """Murphy Residential — uses /sale/.../{id} URLs."""
    url = 'https://www.murphyresidential.com.au/buy/residential-for-sale/'
    print("  → Murphy Residential")
    html = fetch(url)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    seen_urls = set()
    # Use property detail links as anchor for each card
    for a in soup.select('a[href*="/sale/nsw/"]'):
        href = a.get('href', '')
        if not href or href in seen_urls:
            continue
        if not re.search(r'/\d+/?$', href):
            continue
        seen_urls.add(href)
        # Find the parent card
        card = a.find_parent(['article', 'div', 'li'])
        text = card.get_text(' ', strip=True) if card else a.get_text(' ', strip=True)
        if len(text) < 10:
            continue
        # Murphy URL pattern: /sale/nsw/north-shore-lower/{suburb}/.../{id}
        suburb_m = re.search(r'/sale/nsw/north-shore-lower/([^/]+)/', href)
        suburb = ''
        if suburb_m:
            slug = suburb_m.group(1).replace('-', ' ')
            suburb = LNS_LOWER.get(slug.lower(), slug.title())
        # Extract address: number + street name
        addr_m = re.search(
            r'(\d+[a-z]?(?:[/\-]\d+[a-z]?)?)\s+([A-Z][a-zA-Z\s]+?(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Place|Pl|Lane|Ln|Crescent|Cres|Court|Ct|Way|Parade|Pde|Terrace|Tce|Close|Cl|Boulevard|Blvd))',
            text
        )
        if not addr_m:
            continue
        addr = f"{addr_m.group(1)} {addr_m.group(2)}".strip()
        # Beds/baths/cars: look for "5 3 2" pattern after address
        bbc_m = re.search(re.escape(addr) + r'\s+(\d+)\s+(\d+)\s+(\d+)', text)
        beds = baths = cars = ''
        if bbc_m:
            beds, baths, cars = bbc_m.group(1), bbc_m.group(2), bbc_m.group(3)
        else:
            bbc = extract_beds_baths_cars(text)
            beds, baths, cars = bbc['beds'], bbc['baths'], bbc['cars']
        # Price: look for $X or "Auction" or "Contact Agent"
        price = ''
        pm = re.search(r'\$[\d,]+(?:\.\d+)?[KMmk]?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?[KMmk]?)?', text)
        if pm:
            price = pm.group(0)
        elif 'Auction' in text:
            price = 'Auction'
        elif 'Contact' in text:
            price = 'Contact Agent'
        listings.append(make_entry(
            'Murphy Residential', addr, suburb,
            price, beds, baths, cars,
            urljoin(url, href),
        ))
    print(f"     {len(listings)} listings")
    return listings


def scrape_bresic_whitney():
    url = 'https://bresicwhitney.com.au/buy?type=buy&sort=_createdAt_DESC&exclusive=true&page=1'
    print("  → BresicWhitney (exclusive, Playwright)")
    html = fetch_pw(url, wait_selector='a[href*="/property/"], a[href*="/listing/"], [class*="property"], [class*="listing"]', wait_ms=4000)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    for card in soup.select('a[href*="/property/"], a[href*="/listing/"], .listing-card, .property-tile, [class*="PropertyCard"], article'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 20:
            continue
        link = card.get('href') if card.name == 'a' else (card.find('a', href=True) or {}).get('href', '')
        addr_m = re.search(r'(\d+[a-z]?[/\-\d ]*)\s+([A-Z][a-zA-Z\s]+?)(?:,|\s+(?:' + '|'.join(re.escape(s) for s in LNS_SUBURBS) + r'))', text)
        if not addr_m:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        addr = addr_m.group(0).split(',')[0].strip()
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'BresicWhitney', addr, suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, link) if link else url,
            extra={'exclusive': True},
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


def scrape_belle_property():
    url = ('https://www.belleproperty.com/listings?propertyType=residential&sort=newold'
           '&searchStatus=buy&searchKeywords=Crows%20Nest%20NSW%202065%3BCammeray%20NSW%202062'
           '%3BNeutral%20Bay%20NSW%202089%3BCremorne%20NSW%202090%3BCremorne%20Point%20NSW%202090'
           '%3BMosman%20NSW%202088%3BWollstonecraft%20NSW%202065%3BWaverton%20NSW%202060'
           '%3BNorthbridge%20NSW%202063&surr=1&state=all')
    print("  → Belle Property (Playwright)")
    html = fetch_pw(url, wait_selector='article, .listing, [class*="listing"], [class*="property"]', wait_ms=5000)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    for card in soup.select('article, .listing, .property-card, [class*="listing-card"], [class*="ListingCard"], a[href*="/listing/"]'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 30:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        link = card.find('a', href=True) if card.name != 'a' else card
        href = ''
        if link:
            href = link.get('href', '') if card.name != 'a' else link.get('href', '')
        addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
        if not addr_m:
            continue
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'Belle Property', addr_m.group(0).strip(), suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, href) if href else url,
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


def scrape_atlas():
    listings = []
    for pg in [1, 2, 3]:
        url = f'https://www.atlas.com.au/our-listings/property/page/{pg}/'
        print(f"  → Atlas page {pg} (Playwright)")
        html = fetch_pw(url, wait_selector='article, .property-item, [class*="property"]', wait_ms=4000)
        if not html: break
        soup = BeautifulSoup(html, 'html.parser')
        page_count = 0
        for card in soup.select('article, .property-item, [class*="property"], [class*="listing"]'):
            text = card.get_text(' ', strip=True)
            if not text or len(text) < 20:
                continue
            suburb = extract_suburb(text)
            if not suburb:
                continue
            link = card.find('a', href=True)
            addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
            if not addr_m:
                continue
            bbc = extract_beds_baths_cars(text)
            listings.append(make_entry(
                'Atlas', addr_m.group(0).strip(), suburb,
                extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
                urljoin(url, link['href']) if link else url,
            ))
            page_count += 1
        print(f"     page {pg}: {page_count} LNS")
        if page_count == 0: break
        time.sleep(random.uniform(1.0, 2.0))
    print(f"     Total Atlas: {len(listings)}")
    return listings


def scrape_mcgrath():
    url = ('https://www.mcgrath.com.au/properties/suburb/'
           'mosman-nsw-2088-id358+cremorne-nsw-2090-id362+willoughby-nsw-2068-id308'
           '+artarmon-nsw-2064-id289+milsons-point-nsw-2061-id286+naremburn-nsw-2065-id292'
           '+wollstonecraft-nsw-2065-id295+kirribilli-nsw-2061-id285+crows-nest-nsw-2065-id290'
           '+cammeray-nsw-2062-id287+lane-cove-nsw-2066-id296+longueville-nsw-2066-id300'
           '+riverview-nsw-2066-id302+neutral-bay-nsw-2089-id360+north-sydney-nsw-2060-id282'
           '+northbridge-nsw-2063-id288+castlecrag-nsw-2068-id305/buy')
    print("  → McGrath (Playwright)")
    html = fetch_pw(url, wait_selector='[class*="property"], [class*="listing"], article', wait_ms=4000)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    # Try multiple card selectors — McGrath uses JS-rendered property cards
    for card in soup.select('article, .property-card, [class*="property-card"], [class*="PropertyCard"], [class*="listing-card"], a[href*="/buy/"]'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 20:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        link = card.find('a', href=True) if card.name != 'a' else card
        href = ''
        if link:
            href = link.get('href', '')
        addr_m = re.search(r'(\d+[a-z]?(?:[/\-]\d+[a-z]?)?)\s+([A-Z][a-zA-Z\s]+?)(?:,|\s+(?:' + '|'.join(re.escape(s) for s in LNS_SUBURBS) + r'))', text)
        if not addr_m:
            # Fallback: generic street address pattern
            addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
        if not addr_m:
            continue
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'McGrath', addr_m.group(0).split(',')[0].strip(), suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, href) if href else url,
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


def scrape_raywhite():
    url = 'https://raywhitelowernorthshore.com.au/properties/residential-for-sale?sort=creationTime+desc'
    print("  → Ray White Lower North Shore")
    html = fetch(url)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    for card in soup.select('article, .listing-tile, .property-listing, [class*="property"], [class*="listing"]'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 20:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        link = card.find('a', href=True)
        addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
        if not addr_m:
            continue
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'Ray White LNS', addr_m.group(0).strip(), suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, link['href']) if link else url,
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


def scrape_stone():
    url = ('https://www.stonerealestate.com.au/buy/residential/?keywords=sale'
           '&keywords=Mosman%2C+NSW%2C+2088%3BWilloughby%2C+NSW%2C+2068'
           '%3BNAREMBURN%2C+NSW%2C+2065%3BCammeray%2C+NSW%2C+2062%3BNORTHBRIDGE%2C+NSW%2C+2063')
    print("  → Stone Real Estate")
    html = fetch(url)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    for card in soup.select('article, .property, [class*="property"], [class*="listing"]'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 20:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        link = card.find('a', href=True)
        addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
        if not addr_m:
            continue
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'Stone Real Estate', addr_m.group(0).strip(), suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, link['href']) if link else url,
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


def scrape_raine_horne():
    listings = []
    for url in [
        'https://www.raineandhorne.com.au/mosman/sale?surrounding_suburbs=true',
        'https://www.raineandhorne.com.au/lns/sale?surrounding_suburbs=true',
    ]:
        label = 'Mosman' if 'mosman' in url else 'LNS'
        print(f"  → Raine & Horne {label} (Playwright)")
        html = fetch_pw(url, wait_selector='article, [class*="property"], [class*="listing"], [class*="Property"]', wait_ms=4000)
        if not html: continue
        soup = BeautifulSoup(html, 'html.parser')
        for card in soup.select('article, .property-listing, [class*="property"], [class*="listing"], [class*="PropertyCard"]'):
            text = card.get_text(' ', strip=True)
            if not text or len(text) < 20:
                continue
            suburb = extract_suburb(text)
            if not suburb:
                continue
            link = card.find('a', href=True)
            addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
            if not addr_m:
                continue
            bbc = extract_beds_baths_cars(text)
            listings.append(make_entry(
                f'Raine & Horne {label}', addr_m.group(0).strip(), suburb,
                extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
                urljoin(url, link['href']) if link else url,
            ))
        time.sleep(random.uniform(1.0, 2.0))
    print(f"     Total R&H: {len(listings)}")
    return listings


def scrape_northside_realtors():
    url = 'https://www.northsiderealtors.com.au/buy'
    print("  → Northside Realtors")
    html = fetch(url)
    if not html: return []
    soup = BeautifulSoup(html, 'html.parser')
    listings = []
    for card in soup.select('article, .property, .listing, [class*="property"], [class*="listing"], .card'):
        text = card.get_text(' ', strip=True)
        if not text or len(text) < 20:
            continue
        suburb = extract_suburb(text)
        if not suburb:
            continue
        link = card.find('a', href=True)
        addr_m = re.search(r'\d+[a-z]?[/\-\d ]*\s+[A-Z][a-zA-Z\s]+', text)
        if not addr_m:
            continue
        bbc = extract_beds_baths_cars(text)
        listings.append(make_entry(
            'Northside Realtors', addr_m.group(0).strip(), suburb,
            extract_price(text), bbc['beds'], bbc['baths'], bbc['cars'],
            urljoin(url, link['href']) if link else url,
        ))
    print(f"     {len(listings)} LNS listings")
    return listings


SCRAPERS = [
    scrape_murphy,
    scrape_bresic_whitney,
    scrape_belle_property,
    scrape_atlas,
    scrape_mcgrath,
    scrape_raywhite,
    scrape_stone,
    scrape_raine_horne,
    scrape_northside_realtors,
]


def main():
    print("=" * 60)
    print("  Agency Website Scraper")
    print("=" * 60)
    all_listings = []
    try:
        for scraper in SCRAPERS:
            try:
                results = scraper()
                all_listings.extend(results)
            except Exception as e:
                print(f"     ERROR: {e}")
            time.sleep(1)
    finally:
        # Close the shared Playwright browser if it was started
        _close_pw()

    # Dedup by (agency, address) since same property may appear multiple times
    seen = set()
    deduped = []
    for p in all_listings:
        key = (p['agency'], re.sub(r'[^a-z0-9]', '', p['address'].lower()))
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    OUTPUT.write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    print(f"\n  Total: {len(deduped)} LNS listings from {len(SCRAPERS)} agencies")
    print(f"  Saved → {OUTPUT}")

    from collections import Counter
    by_agency = Counter(p['agency'] for p in deduped)
    print("\n  By agency:")
    for agency, cnt in by_agency.most_common():
        print(f"    {agency}: {cnt}")


if __name__ == '__main__':
    main()
