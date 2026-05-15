#!/usr/bin/env python3
"""
parse_proping.py
Reads today's Proping emails from Microsoft Outlook for Mac via AppleScript,
parses the content, and outputs structured JSON.

Handles all 6 Proping categories:
  - price_changes, newly_listed, sold
  - auction_changes, unlisted, over_90_days

Output: proping_data.json (today only) + proping_history.json (rolling 7 days)
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
import sys
import os

SCRIPT_DIR    = Path(__file__).parent
OUTPUT_FILE   = SCRIPT_DIR.parent / 'proping_data.json'      # today only (for inject compat)
HISTORY_FILE  = SCRIPT_DIR.parent / 'proping_history.json'   # rolling 7-day log
TEMP_DIR      = Path('/tmp/proping_emails')
HISTORY_DAYS  = 7

try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'beautifulsoup4',
                    '--break-system-packages'], check=True)
    from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Step 1: Extract emails from Outlook via AppleScript
# ---------------------------------------------------------------------------

APPLESCRIPT_EXTRACT = '''
set TEMP_DIR to "/tmp/proping_emails"
do shell script "mkdir -p " & TEMP_DIR

set emailCount to 0
tell application "Microsoft Outlook"
    -- Find the Inbox folder (handles both Classic and New Outlook)
    set theInbox to missing value
    try
        -- Try the default inbox first (classic Outlook)
        set msgCount to count of messages of inbox
        if msgCount > 0 then set theInbox to inbox
    end try

    if theInbox is missing value then
        -- Search mail folders for one named "Inbox" with messages
        repeat with f in mail folders
            try
                if (name of f as text) is "Inbox" then
                    if (count of messages of f) > 0 then
                        set theInbox to f
                        exit repeat
                    end if
                end if
            end try
        end repeat
    end if

    if theInbox is missing value then
        return "NO_INBOX"
    end if

    -- Scan most recent ~500 messages for Proping sender
    set allMsgs to messages of theInbox
    set totalCount to count of allMsgs
    set startIdx to 1
    if totalCount > 500 then set startIdx to totalCount - 500

    repeat with i from totalCount to startIdx by -1
        try
            set msg to item i of allMsgs
            set sAddr to ""
            try
                set sAddr to address of sender of msg
            end try
            if sAddr contains "proping.com.au" then
                set emailCount to emailCount + 1
                if emailCount > 7 then exit repeat

                set htmlPath to TEMP_DIR & "/email_" & emailCount & ".html"
                set txtPath  to TEMP_DIR & "/email_" & emailCount & ".txt"
                set metaPath to TEMP_DIR & "/email_" & emailCount & "_meta.txt"

                try
                    set htmlBody to content of msg
                    set fRef to open for access POSIX file htmlPath with write permission
                    set eof fRef to 0
                    write htmlBody to fRef
                    close access fRef
                end try

                try
                    set txtBody to plain text content of msg
                    set fRef to open for access POSIX file txtPath with write permission
                    set eof fRef to 0
                    write txtBody to fRef
                    close access fRef
                end try

                set metaContent to "SUBJECT:" & subject of msg & linefeed & "INDEX:" & emailCount
                set fRef to open for access POSIX file metaPath with write permission
                set eof fRef to 0
                write metaContent to fRef
                close access fRef
            end if
        end try
    end repeat
end tell
return emailCount
'''


def extract_emails_via_applescript():
    """Run AppleScript to dump Proping emails to /tmp files."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Clear previous temp files
    for f in TEMP_DIR.glob('email_*'):
        f.unlink()

    result = subprocess.run(
        ['osascript', '-e', APPLESCRIPT_EXTRACT],
        capture_output=True, text=True, timeout=120
    )

    if result.returncode != 0:
        print(f"AppleScript error: {result.stderr}")
        return []

    output = result.stdout.strip()
    if output in ('NO_ACCOUNTS', 'NO_INBOX'):
        print(f"Outlook: {output} — cannot find inbox.")
        return []

    try:
        count = int(output)
    except ValueError:
        print(f"Unexpected AppleScript output: {output}")
        count = 0

    print(f"Found {count} Proping email(s) in Outlook.")

    emails = []
    for i in range(1, count + 1):
        html_path = TEMP_DIR / f'email_{i}.html'
        txt_path  = TEMP_DIR / f'email_{i}.txt'
        meta_path = TEMP_DIR / f'email_{i}_meta.txt'

        subject = f'Proping email {i}'
        if meta_path.exists():
            for line in meta_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                if line.startswith('SUBJECT:'):
                    subject = line[8:].strip()

        html_body = html_path.read_text(encoding='utf-8', errors='ignore') if html_path.exists() else ''
        txt_body  = txt_path.read_text(encoding='utf-8', errors='ignore')  if txt_path.exists()  else ''

        emails.append({'subject': subject, 'html': html_body, 'text': txt_body})

    return emails


# ---------------------------------------------------------------------------
# Step 2: Parse email content into structured data
# ---------------------------------------------------------------------------

def clean_price(text):
    """Extract '$X,XXX,XXX' from a string."""
    if not text:
        return ''
    m = re.search(r'-?\$[\d,]+', text)
    return m.group(0) if m else ''


def parse_text_body(text):
    """
    Parse the plain-text version of a Proping email.
    Returns dict with keys: price_changes, newly_listed, sold,
    auction_changes, unlisted, over_90_days.
    """
    sections = {
        'price_changes': [], 'newly_listed': [], 'sold': [],
        'auction_changes': [], 'unlisted': [], 'over_90_days': [],
    }

    # Normalise line endings
    lines = [l.strip() for l in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    lines = [l for l in lines if l]  # drop empty

    SECTION_MAP = {
        r'price\s+change':                         'price_changes',
        r'newly\s+listed':                          'newly_listed',
        r'\bsold\b':                                'sold',
        r'auction\s+(?:moved|change|date|brought)': 'auction_changes',
        r'\bunlisted\b|\bwithdrawn\b':              'unlisted',
        r'(?:over\s+)?90\s+days?\b|stale':          'over_90_days',
    }

    current_section = None
    current_prop = {}

    def save_prop():
        nonlocal current_prop
        if current_prop and current_section and current_prop.get('address'):
            sections[current_section].append(current_prop)
        current_prop = {}

    # Address pattern: starts with alphanumeric unit/street number (e.g. 3/8, G02/26, 302/58-60)
    ADDR_RE = re.compile(
        r'^[A-Za-z]?\d+[/\d\-]*\s+\S.+,\s*[A-Z][a-zA-Z\s]+$'
    )

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect section headers
        matched_section = None
        for pattern, section_key in SECTION_MAP.items():
            if re.search(pattern, line, re.I) and re.search(r'\(\d+\)', line):
                matched_section = section_key
                break

        if matched_section:
            save_prop()
            current_section = matched_section
            i += 1
            continue

        if current_section is None:
            i += 1
            continue

        # Detect new property by address
        if ADDR_RE.match(line):
            save_prop()
            parts = line.rsplit(',', 1)
            suburb = parts[1].strip() if len(parts) > 1 else ''
            # Clean up suburb (remove trailing state like "NSW 2065")
            suburb = re.sub(r'\s+(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d*$', '', suburb).strip()
            current_prop = {
                'address': line,
                'suburb':  suburb,
                'source':  'proping_email',
                'date':    datetime.today().strftime('%d/%m/%Y'),
            }
            i += 1
            continue

        if not current_prop:
            i += 1
            continue

        # Beds & days listed: "4 bed  8 Days listed"
        m = re.match(r'^(\d+)\s+bed\b.*?(\d+)\s+day', line, re.I)
        if m:
            current_prop['beds']        = m.group(1)
            current_prop['days_listed'] = m.group(2)
            i += 1
            continue

        # Proping Estimate: "$2,700,000 Proping Estimate*"
        m = re.match(r'^(\$[\d,]+)\s+Proping Estimate', line, re.I)
        if m:
            current_prop['price'] = m.group(1)
            # Next line might be a price change (e.g. "-$200,000")
            if i + 1 < len(lines) and re.match(r'^[+-]?\$[\d,]+$', lines[i + 1]):
                current_prop['price_change'] = lines[i + 1]
                i += 1
            i += 1
            continue

        # Auction change detail: "Auction Date Removed (was 11 Apr)" or
        # "Auction brought forward to 16 Apr (-14 days)"
        m_auc = re.match(
            r'^(Auction\s+(?:Date\s+Removed|brought\s+forward|postponed|moved).*)$',
            line, re.I
        )
        if m_auc and current_section == 'auction_changes':
            current_prop['auction_change'] = m_auc.group(1).strip()
            i += 1
            continue

        # Price Guide (Sold section)
        m = re.match(r'^(\$[\d,]+)\s+Price Guide', line, re.I)
        if m:
            current_prop['price_guide'] = m.group(1)
            i += 1
            continue

        # Sold Price (Sold section): "$1,200,000 Sold Price" or "Price Withheld Sold Price"
        m = re.match(r'^(\$[\d,]+)\s+Sold Price', line, re.I)
        if m:
            current_prop['price']      = m.group(1)
            current_prop['sold_price'] = m.group(1)
            i += 1
            continue
        if re.match(r'^Price\s+Withheld\s+Sold\s+Price', line, re.I):
            current_prop['sold_price'] = 'Price Withheld'
            i += 1
            continue

        # Agent / Agency: "Konstantin Melnikov / Morton Crows Nest"
        m = re.match(r'^(.+?)\s*/\s*(.+)$', line)
        if m and 'agent' not in current_prop:
            current_prop['agent']  = m.group(1).strip()
            current_prop['agency'] = m.group(2).strip()
            save_prop()
            i += 1
            continue

        i += 1

    save_prop()
    return sections


def extract_domain_links(html):
    """
    Pull all domain.com.au property URLs from the email HTML.
    Returns a dict keyed by a normalised address fragment → URL.
    """
    links = {}
    if not html:
        return links
    try:
        soup = BeautifulSoup(html, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'domain.com.au' in href and '/property/' in href.lower():
                # Grab surrounding text as key
                txt = a.get_text(strip=True)
                if txt:
                    links[txt.lower()[:40]] = href
    except Exception:
        pass
    return links


def make_domain_search_url(address):
    """Generate a Domain.com.au search URL for an address."""
    import urllib.parse
    query = address + ', NSW, Australia'
    return 'https://www.domain.com.au/sale/?q=' + urllib.parse.quote(query)


def enrich_with_domain_urls(sections, domain_links):
    """
    Try to attach a Domain URL to each property.
    First checks scraped links from the email HTML; falls back to a search URL.
    """
    for section_props in sections.values():
        for prop in section_props:
            addr = prop.get('address', '')
            # Check if any scraped link key is a substring of the address
            matched_url = None
            addr_lower = addr.lower()
            for key, url in domain_links.items():
                if key in addr_lower or addr_lower[:20] in key:
                    matched_url = url
                    break
            prop['domain_url'] = matched_url or make_domain_search_url(addr)


def parse_html_body(html):
    """
    Parse the HTML version of a Proping email using BeautifulSoup.
    Falls back to extracting plain text then using parse_text_body.
    Also extracts Domain URLs from the HTML.
    """
    if not html:
        return None, {}
    try:
        soup = BeautifulSoup(html, 'lxml')
        domain_links = extract_domain_links(html)
        text = soup.get_text(separator='\n', strip=True)
        return parse_text_body(text), domain_links
    except Exception as e:
        print(f"  HTML parse error: {e}")
        return None, {}


# ---------------------------------------------------------------------------
# Step 3: Main
# ---------------------------------------------------------------------------

def update_history(today_data):
    """
    Append today's data to the rolling 7-day history file.
    Removes any existing entry for the same date, then prepends today's.
    Trims to the most recent HISTORY_DAYS days.
    """
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception:
            history = []

    today_str = today_data['date']
    # Remove stale entry for today (replace with fresh)
    history = [e for e in history if e.get('date') != today_str]
    history.insert(0, today_data)

    # Parse dates for sorting/trimming
    def parse_date(d):
        try:
            return datetime.strptime(d, '%d/%m/%Y')
        except Exception:
            return datetime.min

    history.sort(key=lambda e: parse_date(e.get('date', '')), reverse=True)
    history = history[:HISTORY_DAYS]

    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(f"History updated: {len(history)} day(s) stored → {HISTORY_FILE}")
    return history


def main():
    print("=" * 60)
    print("Proping Email Parser")
    print(f"Date: {datetime.today().strftime('%A %d %B %Y')}")
    print("=" * 60)

    emails = extract_emails_via_applescript()

    today_str = datetime.today().strftime('%d/%m/%Y')

    ALL_CATEGORIES = [
        'price_changes', 'newly_listed', 'sold',
        'auction_changes', 'unlisted', 'over_90_days',
    ]

    if not emails:
        print("\nNo emails to parse. Saving empty data.")
        empty = {'date': today_str}
        for cat in ALL_CATEGORIES:
            empty[cat] = []
        OUTPUT_FILE.write_text(json.dumps(empty, indent=2))
        update_history(empty)
        return

    all_data = {'date': today_str}
    for cat in ALL_CATEGORIES:
        all_data[cat] = []

    for email in emails:
        print(f"\nParsing: {email['subject']}")

        data = None
        domain_links = {}
        if email['html']:
            data, domain_links = parse_html_body(email['html'])
        if not data or not any(data.values()):
            data = parse_text_body(email['text'])
            domain_links = {}

        if data:
            # Attach Domain URLs
            enrich_with_domain_urls(data, domain_links)
            for cat in ALL_CATEGORIES:
                all_data[cat].extend(data.get(cat, []))

    # Deduplicate by address (keep first occurrence)
    for key in ALL_CATEGORIES:
        seen, deduped = set(), []
        for p in all_data[key]:
            addr = p.get('address', '').lower()
            if addr and addr not in seen:
                seen.add(addr)
                deduped.append(p)
        all_data[key] = deduped

    print(f"\n{'='*60}")
    print(f"Results for {today_str}:")
    print(f"  Price Changes   : {len(all_data['price_changes'])}")
    print(f"  Newly Listed    : {len(all_data['newly_listed'])}")
    print(f"  Sold            : {len(all_data['sold'])}")
    print(f"  Auction Changes : {len(all_data['auction_changes'])}")
    print(f"  Unlisted        : {len(all_data['unlisted'])}")
    print(f"  Over 90 Days    : {len(all_data['over_90_days'])}")

    OUTPUT_FILE.write_text(json.dumps(all_data, indent=2, ensure_ascii=False))
    print(f"\nSaved today → {OUTPUT_FILE}")

    update_history(all_data)


if __name__ == '__main__':
    main()
