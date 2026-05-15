#!/usr/bin/env python3
"""Parse raw Proping email text (from clipboard dumps) into structured JSON for the app."""
import re, json, os, glob, sys

def parse_proping_email(text, date_hint=''):
    """Parse a single Proping email body into structured data."""
    result = {
        'date': date_hint,
        'price_changes': [],
        'newly_listed': [],
        'sold': [],
        'over_90_days': [],
        'unlisted': [],
    }

    # Extract suburbs from intro line
    m = re.search(r"today's report for (.+?)\.?\n", text)
    if m:
        result['suburbs'] = [s.strip() for s in m.group(1).split(',')]

    # Split into sections
    sections = re.split(r'(Price Change\(\d+\)|Newly Listed\(\d+\)|Sold\(\d+\)|Over 90 Days Listed\(\d+\)|Unlisted\(\d+\)|Auction Moved\(\d+\))', text)

    current_section = None
    for part in sections:
        part_stripped = part.strip()
        if re.match(r'Price Change\(\d+\)', part_stripped):
            current_section = 'price_changes'
            continue
        elif re.match(r'Newly Listed\(\d+\)', part_stripped):
            current_section = 'newly_listed'
            continue
        elif re.match(r'Sold\(\d+\)', part_stripped):
            current_section = 'sold'
            continue
        elif re.match(r'Over 90 Days Listed\(\d+\)', part_stripped):
            current_section = 'over_90_days'
            continue
        elif re.match(r'Unlisted\(\d+\)', part_stripped):
            current_section = 'unlisted'
            continue
        elif re.match(r'Auction Moved\(\d+\)', part_stripped):
            current_section = 'auction_moved'
            if 'auction_moved' not in result:
                result['auction_moved'] = []
            continue

        if current_section is None:
            continue

        # Parse property entries from this section text
        # Pattern: address line, then beds/days, then price info, then agent
        # Split by "Image\t" which precedes each property
        entries = re.split(r'Image\t', part)

        for entry in entries:
            entry = entry.strip()
            if not entry or len(entry) < 10:
                continue
            if "That's all for today" in entry or "Disclaimer" in entry:
                break

            lines = [l.strip() for l in entry.split('\n') if l.strip() and l.strip() != 'Image']
            if not lines:
                continue

            # First line should be address
            address = lines[0] if lines else ''
            if not address or len(address) < 5:
                continue

            # Extract suburb from address
            suburb = ''
            known_suburbs = ['Mosman', 'Cremorne', 'Cremorne Point', 'Neutral Bay', 'Kurraba Point',
                           'Kirribilli', 'North Sydney', 'Waverton', 'Cammeray', 'McMahons Point',
                           'Naremburn', 'Willoughby', 'Wollstonecraft', 'Crows Nest', 'Northbridge',
                           'Castlecrag', 'Artarmon', 'Lane Cove', 'Longueville', 'Chatswood',
                           'St Leonards', 'Riverview', 'Greenwich', 'Wollstonecraft', 'Milsons Point',
                           'Lavender Bay', 'Mcmahons Point', 'Crows Nest']
            for sub in sorted(known_suburbs, key=len, reverse=True):
                if sub.lower() in address.lower():
                    suburb = sub
                    break

            prop = {
                'address': address,
                'suburb': suburb,
                'source': 'proping_email',
                'date': date_hint,
            }

            # Parse remaining lines for beds, price, agent, price_change
            full_text = '\n'.join(lines[1:])

            # Beds
            bed_m = re.search(r'(\d+)\s*bed', full_text)
            if bed_m:
                prop['beds'] = bed_m.group(1)

            # Days listed
            days_m = re.search(r'(\d+)\s*Days?\s*listed', full_text)
            if days_m:
                prop['days_listed'] = days_m.group(1)

            # Price - look for dollar amounts
            prices = re.findall(r'\$[\d,]+(?:,\d{3})*', full_text)
            if prices:
                prop['price'] = prices[0]

            # Price change (for price_changes section)
            change_m = re.search(r'[\$]?\s*([+-]?\s*\$[\d,]+)', full_text)
            if current_section == 'price_changes':
                # Look for the change amount (usually preceded by Image or at end)
                changes = re.findall(r'(?:Image\s*)?\$?\s*(-?\$[\d,]+(?:,\d{3})*)', full_text)
                if len(changes) >= 2:
                    prop['price_change'] = changes[-1]
                elif len(prices) >= 2:
                    prop['price_change'] = prices[-1]

            # Sold price
            if current_section == 'sold':
                sold_m = re.search(r'(?:Price Withheld|(\$[\d,]+))\s*Sold\s*Price', full_text)
                if sold_m:
                    prop['sold_price'] = sold_m.group(1) if sold_m.group(1) else 'Price Withheld'
                elif 'Price Withheld' in full_text:
                    prop['sold_price'] = 'Price Withheld'
                # The price before "Sold Price" is the guide
                if prop.get('price'):
                    prop['price_guide'] = prop['price']

            # Agent - usually last non-empty line before next entry
            agent_line = ''
            for line in reversed(lines[1:]):
                line = line.strip()
                if line and not re.match(r'^[\$\d]', line) and 'Days listed' not in line and 'bed' not in line.lower() and 'Price' not in line and 'Sold' not in line and 'Image' not in line and 'Estimate' not in line:
                    agent_line = line
                    break
            if agent_line:
                parts = agent_line.split(' / ', 1)
                prop['agent'] = parts[0].strip()
                prop['agency'] = parts[1].strip() if len(parts) > 1 else ''

            if current_section in result:
                result[current_section].append(prop)

    return result


def process_all_raw_files(directory):
    """Process all raw email text files in directory."""
    all_data = []
    for fpath in sorted(glob.glob(os.path.join(directory, '*.txt'))):
        with open(fpath) as f:
            text = f.read()
        # Try to extract date from filename or content
        date_m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(fpath))
        date_hint = date_m.group(1) if date_m else ''
        if not date_hint:
            # Try from email content
            date_m2 = re.search(r'Date:\s*\w+,\s*(\d+\s+\w+\s+\d{4})', text)
            if date_m2:
                date_hint = date_m2.group(1)

        parsed = parse_proping_email(text, date_hint)
        all_data.append(parsed)
        pc = len(parsed['price_changes'])
        nl = len(parsed['newly_listed'])
        s = len(parsed['sold'])
        print(f"  {os.path.basename(fpath)}: {pc} price changes, {nl} new, {s} sold")

    return all_data


if __name__ == '__main__':
    # Process from clipboard dump file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file) as f:
            text = f.read()
        result = parse_proping_email(text)
        print(json.dumps(result, indent=2))
    else:
        # Process all files in proping_emails directory
        directory = os.path.join(os.path.dirname(__file__), 'proping_emails')
        if os.path.isdir(directory):
            all_data = process_all_raw_files(directory)
            output = os.path.join(directory, 'all_parsed.json')
            with open(output, 'w') as f:
                json.dump(all_data, f, indent=2)
            print(f"\nSaved {len(all_data)} emails to {output}")
