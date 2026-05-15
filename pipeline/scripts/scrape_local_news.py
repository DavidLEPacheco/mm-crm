#!/usr/bin/env python3
"""
scrape_local_news.py
=====================
Scrapes local real estate news for the Lower North Shore from multiple sources.
Produces talking points for client conversations: auction clearance rates,
market trends, notable sales, development news, and interest rate impacts.

Sources:
  - PropertyUpdate.com.au (weekly auction clearance rates)
  - Mosman Collective (local property news)
  - Domain.com.au auction results
  - CoreLogic / SQM Research market data
  - RBA monetary policy updates

Output: local_news.json → injected into app as D._localNews

Usage:
  python3 scrape_local_news.py              # Full scrape
  python3 scrape_local_news.py --dry-run    # Preview sources
"""

import json, re, os, sys, time, random
from pathlib import Path
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4'], check=True)
    from bs4 import BeautifulSoup

SCRIPT_DIR   = Path(__file__).parent
DATA_FILE    = SCRIPT_DIR / 'local_news.json'
APP_PATH     = Path('/Users/gf/Downloads/mazar_martin_app.html')
DEPLOY_PATH  = Path('/Users/gf/Downloads/mazar-martin-deploy/index.html')
PREVIEW_PATH = Path('/tmp/mm_preview/index.html')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
}

# ── Source scrapers ───────────────────────────────────────────────────────────

def scrape_property_update():
    """Scrape PropertyUpdate.com.au for weekly auction clearance report."""
    stories = []
    url = 'https://propertyupdate.com.au/this-weekends-auction-results-what-happened-in-sydney-melbourne-brisbane-adelaide-canberra/'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ PropertyUpdate: HTTP {r.status_code}")
            return stories
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else 'Weekly Auction Report'

        # Extract article content
        article = soup.find('article') or soup.find('div', class_=re.compile(r'entry|content|post'))
        if not article:
            return stories

        text = article.get_text('\n', strip=True)

        # Extract clearance rates with regex
        sydney_rate = re.search(r'Sydney.*?(\d+\.?\d*)%.*?clearance', text, re.I | re.S)
        national_rate = re.search(r'[Nn]ational.*?(\d+\.?\d*)%', text)
        lns_rate = re.search(r'[Ll]ower\s+[Nn]orth.*?(\d+\.?\d*)%', text)
        houses_rate = re.search(r'[Hh]ouses.*?(\d+\.?\d*)%', text)
        units_rate = re.search(r'[Uu]nits.*?(\d+\.?\d*)%', text)

        # Build bullet points
        bullets = []
        if lns_rate:
            bullets.append(f"Lower North Shore clearance rate: {lns_rate.group(1)}%")
        if sydney_rate:
            bullets.append(f"Sydney overall clearance rate: {sydney_rate.group(1)}%")
        if national_rate:
            bullets.append(f"National clearance rate: {national_rate.group(1)}%")
        if houses_rate and units_rate:
            bullets.append(f"Houses {houses_rate.group(1)}% vs Units {units_rate.group(1)}%")

        # Look for top sales
        top_sale = re.search(r'(?:top|highest).*?sale.*?\$([0-9,]+)', text, re.I)
        if top_sale:
            # Find the address near the price
            addr_match = re.search(r'(\d+\s+\w+\s+(?:St|Street|Rd|Road|Ave|Avenue|Dr|Drive|Pl|Place|Ct|Court|Cr|Cres|Pde|Parade)\s+\w+)', text, re.I)
            if addr_match:
                bullets.append(f"Top Sydney sale: {addr_match.group(1)} — ${top_sale.group(1)}")
            else:
                bullets.append(f"Top Sydney sale: ${top_sale.group(1)}")

        # Extract listed count
        listed = re.search(r'(\d+)\s*(?:properties|auctions)\s*(?:listed|scheduled)', text, re.I)
        if listed:
            bullets.append(f"{listed.group(1)} auctions listed this week")

        if bullets:
            stories.append({
                'category': 'auction_clearance',
                'title': 'Weekly Auction Clearance Rates',
                'bullets': bullets,
                'source': 'PropertyUpdate.com.au',
                'url': url,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'icon': '🔨',
            })
        print(f"  ✓ PropertyUpdate: {len(bullets)} data points")
    except Exception as e:
        print(f"  ✗ PropertyUpdate: {e}")
    return stories


def scrape_mosman_collective():
    """Scrape Mosman Collective for local property news."""
    stories = []
    url = 'https://mosmancollective.com/category/property/'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ MosmanCollective: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', limit=8)

        for art in articles:
            title_el = art.find(['h2', 'h3'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link_el = title_el.find('a') or art.find('a')
            link = link_el['href'] if link_el and link_el.get('href') else ''

            # Get excerpt — skip metadata paragraphs (author/date strings)
            excerpt = ''
            for p in art.find_all('p'):
                txt = p.get_text(strip=True)
                # Skip author/date metadata lines
                if re.search(r'\d{4}-\d{2}-\d{2}T', txt) or re.search(r'^\w+ \w+\d{4}', txt):
                    continue
                if len(txt) > 30:
                    excerpt = txt
                    break
            if not excerpt:
                exc_el = art.find(class_=re.compile(r'excerpt|summary|desc'))
                if exc_el:
                    excerpt = exc_el.get_text(strip=True)

            # Get date
            time_el = art.find('time')
            date_str = time_el.get('datetime', '')[:10] if time_el else ''
            if not date_str:
                date_match = re.search(r'(\w+\s+\d{1,2},?\s+\d{4})', art.get_text())
                if date_match:
                    try:
                        dt = datetime.strptime(date_match.group(1).replace(',', ''), '%B %d %Y')
                        date_str = dt.strftime('%Y-%m-%d')
                    except:
                        date_str = datetime.now().strftime('%Y-%m-%d')

            if title:
                stories.append({
                    'category': 'local_development',
                    'title': title[:120],
                    'bullets': [excerpt[:200]] if excerpt else [],
                    'source': 'Mosman Collective',
                    'url': link,
                    'date': date_str or datetime.now().strftime('%Y-%m-%d'),
                    'icon': '🏗',
                })

        print(f"  ✓ MosmanCollective: {len(stories)} articles")
    except Exception as e:
        print(f"  ✗ MosmanCollective: {e}")
    return stories


def scrape_ray_white_lns():
    """Scrape Ray White Lower North Shore news for market updates."""
    stories = []
    url = 'https://raywhitelowernorthshore.com.au/news'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ RayWhiteLNS: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', limit=5) or soup.find_all(class_=re.compile(r'news-item|post|card'), limit=5)

        for art in articles:
            title_el = art.find(['h2', 'h3', 'h4'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link_el = art.find('a')
            link = link_el['href'] if link_el and link_el.get('href') else ''
            if link and not link.startswith('http'):
                link = 'https://raywhitelowernorthshore.com.au' + link

            excerpt_el = art.find('p')
            excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ''

            if title:
                stories.append({
                    'category': 'market_update',
                    'title': title[:120],
                    'bullets': [excerpt[:200]] if excerpt else [],
                    'source': 'Ray White LNS',
                    'url': link,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'icon': '📊',
                })

        print(f"  ✓ RayWhiteLNS: {len(stories)} articles")
    except Exception as e:
        print(f"  ✗ RayWhiteLNS: {e}")
    return stories


def scrape_sqm_auction_data():
    """Scrape SQM Research for NSW auction clearance data."""
    stories = []
    url = 'https://sqmresearch.com.au/auction_results.php'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ SQM: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text('\n', strip=True)

        # Look for Sydney clearance rate
        sydney_cr = re.search(r'Sydney.*?(\d+\.?\d*)%', text, re.I)
        total_auctions = re.search(r'(\d+)\s*total\s*auctions', text, re.I)
        sold = re.search(r'(\d+)\s*sold', text, re.I)

        bullets = []
        if sydney_cr:
            bullets.append(f"SQM Sydney clearance rate: {sydney_cr.group(1)}%")
        if total_auctions:
            bullets.append(f"Total auctions tracked: {total_auctions.group(1)}")
        if sold:
            bullets.append(f"Properties sold at auction: {sold.group(1)}")

        # Get the reporting week
        week_match = re.search(r'week\s+ending\s+(\d+\s+\w+\s+\d{4})', text, re.I)
        date_str = datetime.now().strftime('%Y-%m-%d')
        week_label = ''
        if week_match:
            week_label = f" (w/e {week_match.group(1)})"
            try:
                dt = datetime.strptime(week_match.group(1), '%d %b %Y')
                date_str = dt.strftime('%Y-%m-%d')
            except:
                pass

        if bullets:
            stories.append({
                'category': 'auction_clearance',
                'title': f'SQM Auction Results{week_label}',
                'bullets': bullets,
                'source': 'SQM Research',
                'url': url,
                'date': date_str,
                'icon': '📈',
            })
        print(f"  ✓ SQM: {len(bullets)} data points")
    except Exception as e:
        print(f"  ✗ SQM: {e}")
    return stories


def scrape_domain_news():
    """Scrape Domain.com.au property news section for North Shore articles."""
    stories = []
    url = 'https://www.domain.com.au/news/'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ Domain News: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all('article', limit=20) or soup.find_all(class_=re.compile(r'story|article|card'), limit=20)

        lns_keywords = re.compile(
            r'north\s*shore|mosman|cremorne|neutral\s*bay|kirribilli|milsons?\s*point|'
            r'mcmahons?\s*point|waverton|north\s*sydney|crows\s*nest|cammeray|'
            r'willoughby|castlecrag|lane\s*cove|chatswood|artarmon|naremburn|'
            r'wollstonecraft|northbridge|greenwich|longueville|hunters?\s*hill|'
            r'auction\s*clearance|sydney\s*auction|interest\s*rate|rba|'
            r'property\s*market|house\s*prices?|median\s*price',
            re.I
        )

        for art in articles:
            title_el = art.find(['h2', 'h3', 'h4'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            full_text = art.get_text(' ', strip=True)

            # Only include articles relevant to LNS or broader market
            if not lns_keywords.search(title + ' ' + full_text):
                continue

            link_el = art.find('a')
            link = link_el['href'] if link_el and link_el.get('href') else ''
            if link and not link.startswith('http'):
                link = 'https://www.domain.com.au' + link

            excerpt_el = art.find('p')
            excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ''

            stories.append({
                'category': 'market_news',
                'title': title[:120],
                'bullets': [excerpt[:200]] if excerpt else [],
                'source': 'Domain',
                'url': link,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'icon': '📰',
            })

        print(f"  ✓ Domain: {len(stories)} relevant articles")
    except Exception as e:
        print(f"  ✗ Domain: {e}")
    return stories


def scrape_rba_update():
    """Check RBA for latest monetary policy decision."""
    stories = []
    url = 'https://www.rba.gov.au/monetary-policy/rba-board-minutes/'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ RBA: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        # Find latest minutes link
        links = soup.find_all('a', href=re.compile(r'/monetary-policy/rba-board-minutes/\d{4}/'))
        if links:
            latest = links[0]
            title = latest.get_text(strip=True)
            href = latest.get('href', '')
            if not href.startswith('http'):
                href = 'https://www.rba.gov.au' + href

            stories.append({
                'category': 'interest_rates',
                'title': f'RBA Board Minutes: {title[:80]}',
                'bullets': [
                    'Cash rate: 4.10% (raised 25bps on 17 Mar 2026)',
                    'Decision passed 5-4 — four members preferred hold at 3.85%',
                    'Inflation picked up in H2 2025; ME conflict driving fuel prices higher',
                    'Labour market tighter than expected, unit labour costs elevated',
                ],
                'source': 'Reserve Bank of Australia',
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'icon': '🏦',
            })
        print(f"  ✓ RBA: latest policy update")
    except Exception as e:
        print(f"  ✗ RBA: {e}")
    return stories


def scrape_corelogic_hedlines():
    """Scrape CoreLogic / PropTrack for Sydney market summary."""
    stories = []
    url = 'https://www.corelogic.com.au/news-research/news'
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  ✗ CoreLogic: HTTP {r.status_code}")
            return stories

        soup = BeautifulSoup(r.text, 'html.parser')
        articles = soup.find_all(['article', 'div'], class_=re.compile(r'card|article|news'), limit=10)

        sydney_kw = re.compile(r'sydney|nsw|auction|clearance|north\s*shore|market|price|dwelling', re.I)

        for art in articles:
            title_el = art.find(['h2', 'h3', 'h4'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not sydney_kw.search(title):
                continue
            link_el = art.find('a')
            link = link_el['href'] if link_el and link_el.get('href') else ''
            if link and not link.startswith('http'):
                link = 'https://www.corelogic.com.au' + link

            stories.append({
                'category': 'market_data',
                'title': title[:120],
                'bullets': [],
                'source': 'CoreLogic',
                'url': link,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'icon': '📊',
            })

        print(f"  ✓ CoreLogic: {len(stories)} articles")
    except Exception as e:
        print(f"  ✗ CoreLogic: {e}")
    return stories


# ── Static market context (refreshed manually or via web search) ──────────────

def build_market_context():
    """Build curated talking points from latest known data."""
    today = datetime.now().strftime('%Y-%m-%d')
    return [
        {
            'category': 'talking_point',
            'title': 'LNS Market Snapshot',
            'bullets': [
                'Lower North Shore clearance rate: 65.0% — highest of any Sydney region this week',
                'Sydney median house price: $1,612,500 (down from $1,900,000 prior week)',
                'Houses clearing at 62.4%, units at 68.7% — unit demand remains strong',
                'Top LNS sale this week: 14 Erith St Mosman — $5,300,000',
                'Sydney listings down due to April school holidays — expect rebound next week',
            ],
            'source': 'Weekly Auction Data',
            'url': '',
            'date': today,
            'icon': '🏠',
        },
        {
            'category': 'talking_point',
            'title': 'Interest Rates & Borrowing',
            'bullets': [
                'RBA raised cash rate to 4.10% on 17 March — split decision (5-4)',
                'Middle East conflict pushing fuel prices higher, adding to inflation pressure',
                'Each 25bp hike reduces average borrowing capacity by ~$12,000',
                'Bank forecasts: Westpac +5%, NAB +4.2%, CBA +3%, ANZ +2.5% for Sydney in 2026',
                'Rate hikes slowing price growth but supply constraints preventing major falls',
            ],
            'source': 'RBA / Bank Forecasts',
            'url': 'https://www.rba.gov.au/media-releases/2026/mr-26-08.html',
            'date': today,
            'icon': '💰',
        },
        {
            'category': 'talking_point',
            'title': 'Development & Infrastructure',
            'bullets': [
                'Crows Nest Metro now open — CBD in 7min, Chatswood in 4min',
                'Properties near metro stations commanding 20-30% price premiums',
                '40-storey tower proposed at 378-398 Pacific Hwy (156 apartments)',
                'Third.i launching "Elevate" — 130 apartments directly above Crows Nest station',
                'Seven Mosman homes to be demolished for $53M luxury apartment block',
                '$106M twin-tower planned for Balmoral slopes (10 storeys, replacing 5 homes)',
                '$65M hush-hush deal: two Mosman apartment blocks sold to developer',
            ],
            'source': 'Local Development News',
            'url': '',
            'date': today,
            'icon': '🏗',
        },
        {
            'category': 'talking_point',
            'title': 'Broader Market Trends',
            'bullets': [
                'Sydney home values dipped 0.2% in Q1 — Melbourne fell 0.6%',
                'Perth (+7.3%), Brisbane (+5.1%), Adelaide (+3.6%) still surging',
                'Sydney quarterly home sales down 16% YoY — ME conflict dampening sentiment',
                'Affluent suburbs dipping while affordable suburbs gaining — two-speed market',
                'New borrowers need to service at ~9% with 3% buffer — shrinking buyer pool',
                'Regional values rising 3.3% per quarter, outpacing combined capitals (+1.8%)',
            ],
            'source': 'CoreLogic / Cotality',
            'url': '',
            'date': today,
            'icon': '📉',
        },
    ]


# ── Injection into app HTML ──────────────────────────────────────────────────

def inject_news_data(news_items, html_path):
    """Inject news data into app HTML as D._localNews."""
    html = html_path.read_text()
    js_data = json.dumps(news_items, separators=(',', ':'))

    marker_start = '/* __LOCAL_NEWS_START__ */'
    marker_end = '/* __LOCAL_NEWS_END__ */'
    injection = f"{marker_start}\nD._localNews = {js_data};\n{marker_end}"

    if marker_start in html:
        start_idx = html.index(marker_start)
        end_idx = html.index(marker_end) + len(marker_end)
        html = html[:start_idx] + injection + html[end_idx:]
    else:
        # Insert after D._propertyData block, or after const D = {...};
        prop_marker = '/* __PROPERTY_DATA_END__ */'
        if prop_marker in html:
            insert_pos = html.index(prop_marker) + len(prop_marker)
            html = html[:insert_pos] + '\n' + injection + '\n' + html[insert_pos:]
        else:
            # Fallback: insert after const D = {...};
            d_match = re.search(r'const\s+D\s*=\s*\{', html)
            if d_match:
                start = d_match.end() - 1
                depth = 0
                i = start
                while i < len(html):
                    if html[i] == '{': depth += 1
                    elif html[i] == '}':
                        depth -= 1
                        if depth == 0: break
                    i += 1
                semi = html.index(';', i)
                insert_pos = semi + 1
                html = html[:insert_pos] + '\n' + injection + '\n' + html[insert_pos:]

    html_path.write_text(html)
    return True


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("📰 Local News Scraper — Lower North Shore Real Estate")
    print(f"Date: {datetime.now().strftime('%A %d %B %Y')}")
    print("=" * 60)

    all_stories = []

    # Scrape live sources
    print("\n▶ Scraping live sources...")
    scrapers = [
        ('PropertyUpdate', scrape_property_update),
        ('Mosman Collective', scrape_mosman_collective),
        ('Ray White LNS', scrape_ray_white_lns),
        ('SQM Research', scrape_sqm_auction_data),
        ('Domain News', scrape_domain_news),
        ('RBA', scrape_rba_update),
        ('CoreLogic', scrape_corelogic_hedlines),
    ]

    for name, scraper_fn in scrapers:
        time.sleep(random.uniform(1.0, 2.5))
        try:
            stories = scraper_fn()
            all_stories.extend(stories)
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    # Add curated market context
    print("\n▶ Building curated talking points...")
    context = build_market_context()
    all_stories.extend(context)
    print(f"  ✓ {len(context)} talking point sections")

    # Load existing data and merge (keep last 30 days)
    existing = []
    if DATA_FILE.exists():
        try:
            existing = json.loads(DATA_FILE.read_text())
        except:
            pass

    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    existing = [s for s in existing if s.get('date', '') >= cutoff]

    # Dedup by title
    seen_titles = {s['title'].lower().strip() for s in all_stories}
    for old in existing:
        if old['title'].lower().strip() not in seen_titles:
            all_stories.append(old)
            seen_titles.add(old['title'].lower().strip())

    # Sort by date descending
    all_stories.sort(key=lambda s: s.get('date', ''), reverse=True)

    print(f"\n{'=' * 60}")
    print(f"Total stories: {len(all_stories)}")
    for cat in ['auction_clearance', 'local_development', 'market_update', 'market_news', 'market_data', 'interest_rates', 'talking_point']:
        count = sum(1 for s in all_stories if s.get('category') == cat)
        if count:
            print(f"  {cat}: {count}")

    if dry_run:
        print("\n[DRY RUN] Would save and inject:")
        for s in all_stories[:10]:
            print(f"  {s['icon']} {s['title']} ({s['source']})")
        return

    # Save
    DATA_FILE.write_text(json.dumps(all_stories, indent=2))
    print(f"\nSaved to {DATA_FILE}")

    # Inject into app HTML
    print("\nInjecting into app...")
    for path in [APP_PATH, DEPLOY_PATH, PREVIEW_PATH]:
        if path.exists():
            try:
                inject_news_data(all_stories, path)
                print(f"  ✓ {path.name}")
            except Exception as e:
                print(f"  ✗ {path.name}: {e}")

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
