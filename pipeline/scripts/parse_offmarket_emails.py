#!/usr/bin/env python3
"""
parse_offmarket_emails.py
Scans Microsoft Outlook for Mac for off-market / pre-market property emails
from agents, extracts key details, and outputs structured JSON.

Matches on BOTH subject and body text. Supports Exchange + IMAP accounts.
Extracts actual email date (not today's date).

Output: offmarket_emails.json in the parent (Downloads) directory.
Existing entries are preserved; new ones are prepended.
"""

import subprocess
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

SCRIPT_DIR  = Path(__file__).parent
OUTPUT_FILE = SCRIPT_DIR.parent / 'offmarket_emails.json'
TEMP_DIR    = Path('/tmp/offmarket_emails')
MAX_EMAILS  = 100   # Max off-market emails to extract per run
SCAN_DAYS   = 90    # Only scan emails from last N days

# Keywords that trigger inclusion — checked in subject AND body
SUBJECT_KEYWORDS = [
    'off-market', 'off market', 'offmarket', 'off mkt',
    'pre-market', 'pre market', 'premarket',
    'coming soon', 'pocket listing', 'pocket sale',
    'exclusive listing', 'exclusive opportunity', 'exclusive sale',
    'not on market', 'not yet listed', 'unlisted',
    'silent sale', 'private sale', 'private treaty',
    'quiet sale', 'discreet sale', 'discreet opportunity',
    'expressions of interest', 'eoi',
    'for your buyers', 'buyer opportunity', 'suitable for your buyers',
    'before it hits the market', 'prior to listing', 'prior to going live',
    'first look', 'sneak peek', 'sneak preview',
    'not yet on domain', 'not yet on rea', 'not yet advertised',
    'off the plan', 'pre listing', 'pre-listing',
]

# Body-only keywords (too common for subject matching, but good in context)
BODY_KEYWORDS = [
    'off-market opportunity',
    'not currently listed',
    'not publicly listed',
    'before going to market',
    'prior to going to market',
    'private off-market',
    'exclusively available',
    'available before listing',
    'available prior to',
    'quietly available',
    'not on the open market',
    'owner is open to',
    'owner willing to sell',
    'vendor has agreed to sell',
    'vendor happy to sell privately',
]

AGENCY_NAMES = [
    'DiJones', 'McGrath', 'Ray White', 'LJ Hooker', 'Raine & Horne',
    'Atlas', 'Belle Property', 'Stone Real Estate', 'Phillips Pantzer Donnelley',
    'PPD', 'Richardson & Wrench', 'The Agency', 'BresicWhitney',
    'Cobden & Hayson', 'Cunninghams', 'Laing+Simmons', 'Laing & Simmons',
    'Cooley', 'Auction Services', 'Murphy Real Estate', 'Northside Realty',
    'Savills', 'Sotheby', 'Christie', 'CBRE', 'JLL', 'Colliers',
    'Uther', 'Geoff Smith', 'Luschwitz', 'Wills Property',
    'Longueville Real Estate', 'Harris Tripp',
]

# LNS suburbs to prioritise — if an email mentions one of these it's more likely relevant
LNS_SUBURBS = [
    'mosman', 'cremorne', 'neutral bay', 'north sydney', 'kirribilli',
    'milsons point', 'waverton', 'wollstonecraft', 'crows nest', 'st leonards',
    'naremburn', 'cammeray', 'northbridge', 'castlecrag', 'willoughby',
    'artarmon', 'chatswood', 'lane cove', 'greenwich', 'longueville',
    'riverview', 'linley point', 'hunters hill', 'woolwich', 'birchgrove',
    'balmain', 'mcmahons point', 'lavender bay', 'kurraba point',
    'cremorne point', 'clifton gardens',
]

# AppleScript — scans ALL account types (Exchange + IMAP), subject + body matching,
# extracts real email date, limits to recent emails only
APPLESCRIPT_EXTRACT = '''
set TEMP_DIR to "/tmp/offmarket_emails"
do shell script "mkdir -p " & TEMP_DIR
do shell script "rm -f /tmp/offmarket_emails/email_*.txt /tmp/offmarket_emails/email_*_meta.txt"

set emailCount to 0
set maxEmails to ''' + str(MAX_EMAILS) + '''
set scanDays to ''' + str(SCAN_DAYS) + '''

tell application "Microsoft Outlook"
    -- Gather inboxes from all account types
    set inboxList to {}

    -- Exchange accounts
    try
        set exAccts to exchange accounts
        repeat with acct in exAccts
            set end of inboxList to inbox of acct
        end repeat
    end try

    -- IMAP accounts
    try
        set imapAccts to imap accounts
        repeat with acct in imapAccts
            set end of inboxList to inbox of acct
        end repeat
    end try

    -- POP accounts
    try
        set popAccts to pop accounts
        repeat with acct in popAccts
            set end of inboxList to inbox of acct
        end repeat
    end try

    if (count of inboxList) = 0 then return "NO_ACCOUNTS"

    -- Cutoff date
    set cutoffDate to (current date) - (scanDays * days)

    repeat with theInbox in inboxList
        if emailCount ≥ maxEmails then exit repeat
        set allMsgs to messages of theInbox

        repeat with msg in allMsgs
            if emailCount ≥ maxEmails then exit repeat
            try
                set msgDate to time received of msg
                if msgDate < cutoffDate then exit repeat

                set subj to subject of msg
                set lSubj to do shell script "echo " & quoted form of subj & " | tr '[:upper:]' '[:lower:]'"

                -- Check subject for keywords
                set isOffMarket to false
                if lSubj contains "off-market"        then set isOffMarket to true
                if lSubj contains "off market"        then set isOffMarket to true
                if lSubj contains "offmarket"         then set isOffMarket to true
                if lSubj contains "off mkt"           then set isOffMarket to true
                if lSubj contains "pre-market"        then set isOffMarket to true
                if lSubj contains "pre market"        then set isOffMarket to true
                if lSubj contains "premarket"         then set isOffMarket to true
                if lSubj contains "coming soon"       then set isOffMarket to true
                if lSubj contains "pocket listing"    then set isOffMarket to true
                if lSubj contains "pocket sale"       then set isOffMarket to true
                if lSubj contains "exclusive listing" then set isOffMarket to true
                if lSubj contains "exclusive opportunity" then set isOffMarket to true
                if lSubj contains "exclusive sale"    then set isOffMarket to true
                if lSubj contains "not on market"     then set isOffMarket to true
                if lSubj contains "not yet listed"    then set isOffMarket to true
                if lSubj contains "unlisted"          then set isOffMarket to true
                if lSubj contains "silent sale"       then set isOffMarket to true
                if lSubj contains "private sale"      then set isOffMarket to true
                if lSubj contains "private treaty"    then set isOffMarket to true
                if lSubj contains "quiet sale"        then set isOffMarket to true
                if lSubj contains "discreet sale"     then set isOffMarket to true
                if lSubj contains "discreet opportunity" then set isOffMarket to true
                if lSubj contains "for your buyers"   then set isOffMarket to true
                if lSubj contains "buyer opportunity" then set isOffMarket to true
                if lSubj contains "suitable for your buyers" then set isOffMarket to true
                if lSubj contains "before it hits the market" then set isOffMarket to true
                if lSubj contains "prior to listing"  then set isOffMarket to true
                if lSubj contains "first look"        then set isOffMarket to true
                if lSubj contains "sneak peek"        then set isOffMarket to true
                if lSubj contains "sneak preview"     then set isOffMarket to true
                if lSubj contains "not yet on domain" then set isOffMarket to true
                if lSubj contains "not yet advertised" then set isOffMarket to true
                if lSubj contains "pre listing"       then set isOffMarket to true
                if lSubj contains "pre-listing"       then set isOffMarket to true
                if lSubj contains "eoi"               then set isOffMarket to true
                if lSubj contains "open saturday"     then set isOffMarket to true
                if lSubj contains "open sunday"       then set isOffMarket to true
                if lSubj contains "property alert"    then set isOffMarket to true
                if lSubj contains "just listed"       then set isOffMarket to true
                if lSubj contains "new listing"       then set isOffMarket to true

                -- If subject didn't match, check body for off-market keywords
                if not isOffMarket then
                    try
                        set bodyText to plain text content of msg
                        set lBody to do shell script "echo " & quoted form of bodyText & " | tr '[:upper:]' '[:lower:]' | head -c 5000"
                        if lBody contains "off-market opportunity"    then set isOffMarket to true
                        if lBody contains "off market opportunity"    then set isOffMarket to true
                        if lBody contains "not currently listed"      then set isOffMarket to true
                        if lBody contains "not publicly listed"       then set isOffMarket to true
                        if lBody contains "before going to market"    then set isOffMarket to true
                        if lBody contains "prior to going to market"  then set isOffMarket to true
                        if lBody contains "private off-market"        then set isOffMarket to true
                        if lBody contains "exclusively available"     then set isOffMarket to true
                        if lBody contains "available before listing"  then set isOffMarket to true
                        if lBody contains "quietly available"         then set isOffMarket to true
                        if lBody contains "not on the open market"    then set isOffMarket to true
                        if lBody contains "vendor willing to sell"    then set isOffMarket to true
                        if lBody contains "vendor happy to sell"      then set isOffMarket to true
                        if lBody contains "owner is open to"          then set isOffMarket to true
                    end try
                end if

                if isOffMarket then
                    set emailCount to emailCount + 1

                    set senderName to ""
                    set senderAddr to ""
                    try
                        set senderName to display name of sender of msg
                    end try
                    try
                        set senderAddr to address of sender of msg
                    end try

                    -- Write plain text body to temp file
                    set txtPath to TEMP_DIR & "/email_" & emailCount & ".txt"
                    try
                        set txtBody to plain text content of msg
                        set fRef to open for access POSIX file txtPath with write permission
                        set eof fRef to 0
                        write txtBody to fRef
                        close access fRef
                    end try

                    -- Write metadata (including actual email date)
                    set metaPath to TEMP_DIR & "/email_" & emailCount & "_meta.txt"
                    set dateStr to (year of msgDate as string) & "-"
                    set m to (month of msgDate as integer)
                    if m < 10 then set dateStr to dateStr & "0"
                    set dateStr to dateStr & (m as string) & "-"
                    set d to (day of msgDate as integer)
                    if d < 10 then set dateStr to dateStr & "0"
                    set dateStr to dateStr & (d as string)

                    set metaContent to "SUBJECT:" & subj & linefeed & ¬
                        "FROM_NAME:" & senderName & linefeed & ¬
                        "FROM_EMAIL:" & senderAddr & linefeed & ¬
                        "DATE:" & dateStr
                    set fRef to open for access POSIX file metaPath with write permission
                    set eof fRef to 0
                    write metaContent to fRef
                    close access fRef
                end if
            end try
        end repeat
    end repeat
end tell
return emailCount
'''


def extract_emails_via_applescript():
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"  Scanning Outlook (last {SCAN_DAYS} days, up to {MAX_EMAILS} matches)...")
    result = subprocess.run(
        ['osascript', '-e', APPLESCRIPT_EXTRACT],
        capture_output=True, text=True, timeout=300
    )

    if result.returncode != 0:
        print(f"  AppleScript error: {result.stderr[:300]}")
        return []

    output = result.stdout.strip()
    if output == 'NO_ACCOUNTS':
        print("  No email accounts found in Outlook.")
        return []

    try:
        count = int(output)
    except ValueError:
        print(f"  Unexpected AppleScript output: {output}")
        return []

    print(f"  Found {count} off-market email(s) in Outlook.")

    emails = []
    for i in range(1, count + 1):
        txt_path  = TEMP_DIR / f'email_{i}.txt'
        meta_path = TEMP_DIR / f'email_{i}_meta.txt'

        meta = {'subject': '', 'sender_name': '', 'sender_email': '', 'date': ''}
        if meta_path.exists():
            for line in meta_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                if line.startswith('SUBJECT:'):
                    meta['subject'] = line[8:].strip()
                elif line.startswith('FROM_NAME:'):
                    meta['sender_name'] = line[10:].strip()
                elif line.startswith('FROM_EMAIL:'):
                    meta['sender_email'] = line[11:].strip()
                elif line.startswith('DATE:'):
                    meta['date'] = line[5:].strip()

        body = txt_path.read_text(encoding='utf-8', errors='ignore') if txt_path.exists() else ''
        emails.append({**meta, 'body': body})

    return emails


def parse_email_date(date_str):
    """Parse email date from AppleScript (YYYY-MM-DD) to DD/MM/YYYY."""
    if not date_str:
        return datetime.today().strftime('%d/%m/%Y')
    try:
        dt = datetime.strptime(date_str.strip()[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return datetime.today().strftime('%d/%m/%Y')


def is_lns_property(body, subject, address):
    """Check if the email likely relates to the Lower North Shore."""
    combined = (body + ' ' + subject + ' ' + address).lower()
    for suburb in LNS_SUBURBS:
        if suburb in combined:
            return True
    # Check postcodes
    if re.search(r'\b2(0[6-9][0-9]|1[0-2][0-9])\b', combined):
        return True
    return False


def extract_property(email):
    """Extract a property dict from an off-market agent email."""
    body    = email['body']
    subject = email['subject']

    prop = {
        'address':       '',
        'suburb':        '',
        'beds':          '',
        'baths':         '',
        'cars':          '',
        'land':          '',
        'price':         '',
        'propertyType':  '',
        'agent':         email['sender_name'],
        'agency':        '',
        'notes':         '',
        'source':        'email',
        'date':          parse_email_date(email['date']),
        'email_subject': subject,
        'sender_email':  email['sender_email'],
    }

    # ---- Address -------------------------------------------------------
    # Patterns like "3/8 Westleigh Street, Neutral Bay" or "19 Central Street, Naremburn"
    addr_re = re.compile(
        r'\b(\d+[A-Za-z]?[/\d]*\s+[A-Z][a-zA-Z\s\']+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr'
        r'|Lane|Ln|Place|Pl|Court|Ct|Way|Close|Cl|Crescent|Cres|Boulevard|Blvd|Parade|Pde'
        r'|Highway|Hwy|Terrace|Tce|Circuit|Cct|Walk|Grove|Track|Ridge|Glen|Rise|View|Row)'
        r'[\.,]?\s*[A-Z][a-zA-Z\s]+)',
        re.I
    )
    m = addr_re.search(subject)  # Check subject first (more reliable)
    if not m:
        m = addr_re.search(body)
    if m:
        addr = m.group(1).strip().rstrip(',').strip()
        # Clean up trailing state/postcode
        addr = re.sub(r'\s+(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d*$', '', addr).strip()
        prop['address'] = addr
        # Extract suburb (last comma-separated component)
        suburb_m = re.search(r',\s*([A-Z][a-zA-Z\s]+)$', addr)
        if suburb_m:
            raw_sub = suburb_m.group(1).strip()
            raw_sub = re.sub(r'\s+(?:NSW|VIC|QLD|SA|WA|TAS|ACT|NT)\s*\d*$', '', raw_sub).strip()
            prop['suburb'] = raw_sub

    # ---- Property Type -------------------------------------------------
    type_patterns = [
        (r'\b(?:house|family home|freestanding)\b', 'House'),
        (r'\b(?:apartment|apt|unit|flat)\b', 'Apartment'),
        (r'\b(?:townhouse|town house|terrace)\b', 'Townhouse'),
        (r'\b(?:duplex|semi[- ]detached|semi)\b', 'Duplex'),
        (r'\b(?:villa|villa home)\b', 'Villa'),
        (r'\b(?:land|vacant land|block)\b', 'Land'),
        (r'\b(?:studio)\b', 'Studio'),
        (r'\b(?:penthouse)\b', 'Penthouse'),
    ]
    combined = (subject + ' ' + body[:2000]).lower()
    for pattern, ptype in type_patterns:
        if re.search(pattern, combined, re.I):
            prop['propertyType'] = ptype
            break

    # ---- Beds / Baths / Parking ----------------------------------------
    # Try compact format first: "3 bed 2 bath 1 car"
    compact = re.search(r'(\d+)\s*bed.*?(\d+)\s*bath.*?(\d+)\s*(?:car|park|garage)', body, re.I)
    if compact:
        prop['beds'] = compact.group(1)
        prop['baths'] = compact.group(2)
        prop['cars'] = compact.group(3)
    else:
        bed_m = re.search(r'(\d+)\s+bed(?:room)?s?', body, re.I)
        if not bed_m:
            bed_m = re.search(r'(\d+)\s*(?:br|bd)', body, re.I)
        if bed_m:
            prop['beds'] = bed_m.group(1)

        bath_m = re.search(r'(\d+)\s+bath(?:room)?s?', body, re.I)
        if not bath_m:
            bath_m = re.search(r'(\d+)\s*(?:ba)', body, re.I)
        if bath_m:
            prop['baths'] = bath_m.group(1)

        car_m = re.search(r'(\d+)\s+(?:parking|garage|car\s*space|car)', body, re.I)
        if car_m:
            prop['cars'] = car_m.group(1)

    # ---- Area ----------------------------------------------------------
    area_m = re.search(r'(\d[\d,]*)\s*(?:sqm|m²|sq\.?\s*m)', body, re.I)
    if area_m:
        prop['land'] = area_m.group(1).replace(',', '')

    # ---- Price ---------------------------------------------------------
    # Match ranges like "$5M - $5.5M" or "$4,850,000" or "$2.8m"
    price_m = re.search(
        r'\$\s*[\d,.]+\s*(?:million|mil|m)?\s*(?:[-–—to]+\s*\$?\s*[\d,.]+\s*(?:million|mil|m)?)?',
        body, re.I
    )
    if not price_m:
        price_m = re.search(r'\$\s*[\d,.]+\s*(?:million|mil|m)?', subject, re.I)
    if price_m:
        prop['price'] = price_m.group(0).strip()

    # ---- Agency from signature / body -----------------------------------
    for agency in AGENCY_NAMES:
        if agency.lower() in body.lower() or agency.lower() in (email.get('sender_email', '') or '').lower():
            prop['agency'] = agency
            break
    # Try extracting from email domain
    if not prop['agency'] and email.get('sender_email'):
        domain = email['sender_email'].split('@')[-1].split('.')[0] if '@' in email['sender_email'] else ''
        if domain and len(domain) > 2:
            prop['agency'] = domain.title()

    # ---- Notes (first meaningful paragraph) ----------------------------
    paras = [p.strip() for p in re.split(r'\n{2,}', body) if p.strip()]
    for para in paras[:5]:
        if len(para) > 30 and not re.match(r'^[\d\s()+\-]+$', para) and not para.startswith('http'):
            prop['notes'] = para[:250].replace('\n', ' ')
            break

    return prop


def merge_with_existing(new_props):
    """Merge new properties with existing file; skip exact address duplicates."""
    existing = []
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding='utf-8'))
        except Exception:
            existing = []

    # Normalise addresses for matching
    def norm(addr):
        a = (addr or '').lower().strip()
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
        a = re.sub(r'[^a-z0-9]', '', a)
        return a

    existing_addresses = {norm(p.get('address', '')) for p in existing if p.get('address')}

    added = 0
    for prop in new_props:
        addr_norm = norm(prop.get('address', ''))
        if addr_norm and addr_norm not in existing_addresses:
            existing.insert(0, prop)   # prepend so newest first
            existing_addresses.add(addr_norm)
            added += 1

    return existing, added


def main():
    print("=" * 60)
    print("📧 Off-Market Email Parser")
    print(f"   {datetime.today().strftime('%A %d %B %Y')}")
    print("=" * 60)

    emails = extract_emails_via_applescript()

    if not emails:
        print("No off-market emails found.")
        if not OUTPUT_FILE.exists():
            OUTPUT_FILE.write_text('[]')
        return

    properties = []
    skipped_non_lns = 0
    skipped_no_addr = 0

    for email in emails:
        prop = extract_property(email)

        if not prop['address']:
            skipped_no_addr += 1
            continue

        # Optional: filter to LNS only
        if not is_lns_property(email['body'], email['subject'], prop['address']):
            skipped_non_lns += 1
            # Still include it — may be relevant — but note it
            prop['notes'] = (prop['notes'] + ' [non-LNS]').strip()

        print(f"  ✉ {prop['date']} | {prop['address']}")
        print(f"    {prop['beds']}bd {prop['baths']}ba {prop['cars']}pk | {prop['price']} | {prop['agent']} ({prop['agency']})")
        properties.append(prop)

    print(f"\n{'='*60}")
    print(f"  Parsed {len(emails)} emails → {len(properties)} properties extracted")
    if skipped_no_addr:
        print(f"  ⚠ {skipped_no_addr} emails had no extractable address")

    merged, added = merge_with_existing(properties)
    OUTPUT_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False))

    print(f"  ✅ {added} new entries added (total: {len(merged)})")
    print(f"  Saved → {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
