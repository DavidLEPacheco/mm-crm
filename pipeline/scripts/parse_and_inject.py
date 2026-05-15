#!/usr/bin/env python3
"""Parse structured Proping email files and inject data into the Mazar Martin app."""
import re, json, os, glob, sys

def parse_structured_email(filepath):
    """Parse one of our structured email text files into JSON."""
    with open(filepath) as f:
        text = f.read()

    result = {
        'file': os.path.basename(filepath),
        'date': '',
        'type': 'daily',
        'suburbs': [],
        'price_changes': [],
        'newly_listed': [],
        'sold': [],
        'over_90_days': [],
        'unlisted': [],
    }

    # Extract date
    m = re.search(r'DATE:\s*(\S+)', text)
    if m:
        result['date'] = m.group(1)

    # Extract type
    if 'TYPE: WEEKLY' in text:
        result['type'] = 'weekly'
        return result  # Weekly reports have different format, skip property parsing

    # Extract suburbs
    m = re.search(r'SUBURBS:\s*(.+)', text)
    if m:
        result['suburbs'] = [s.strip() for s in m.group(1).split(',')]

    # Parse sections
    current_section = None
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line == 'PRICE_CHANGE:':
            current_section = 'price_changes'
            continue
        elif line == 'NEWLY_LISTED:':
            current_section = 'newly_listed'
            continue
        elif line == 'SOLD:':
            current_section = 'sold'
            continue
        elif line == 'OVER_90_DAYS:':
            current_section = 'over_90_days'
            continue
        elif line == 'UNLISTED:':
            current_section = 'unlisted'
            continue
        elif line.startswith('DATE:') or line.startswith('SUBURBS:') or line.startswith('TYPE:'):
            continue

        if current_section is None:
            continue

        # Parse property line: address | beds | price | [change/sold] | agent
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 3:
            continue

        prop = {
            'address': parts[0],
            'date': result['date'],
            'source': 'proping_email',
        }

        # Beds
        bed_m = re.search(r'(\d+)\s*bed', parts[1])
        if bed_m:
            prop['beds'] = int(bed_m.group(1))

        # Extract suburb from address
        known_suburbs = ['Mosman', 'Cremorne', 'Cremorne Point', 'Neutral Bay', 'Kurraba Point',
                        'Kirribilli', 'North Sydney', 'Waverton', 'Cammeray', 'McMahons Point',
                        'Mcmahons Point', 'Naremburn', 'Willoughby', 'Wollstonecraft', 'Crows Nest',
                        'Northbridge', 'Castlecrag', 'Artarmon', 'Lane Cove', 'Longueville',
                        'Chatswood', 'St Leonards', 'Riverview', 'Greenwich', 'Milsons Point',
                        'Lavender Bay']
        for sub in sorted(known_suburbs, key=len, reverse=True):
            if sub.lower() in prop['address'].lower():
                prop['suburb'] = sub
                break

        if current_section == 'price_changes':
            # Parts: address | beds | price | change | agent
            price_m = re.search(r'\$([\d,]+)', parts[2])
            if price_m:
                prop['price'] = '$' + price_m.group(1)
            if len(parts) >= 4:
                change = parts[3].strip()
                prop['price_change'] = change
            if len(parts) >= 5:
                agent_parts = parts[4].split('/', 1)
                prop['agent'] = agent_parts[0].strip()
                prop['agency'] = agent_parts[1].strip() if len(agent_parts) > 1 else ''
            result['price_changes'].append(prop)

        elif current_section == 'newly_listed':
            # Parts: address | beds | price | agent
            price_m = re.search(r'\$([\d,]+)', parts[2])
            if price_m:
                prop['price'] = '$' + price_m.group(1)
            if len(parts) >= 4:
                agent_parts = parts[3].split('/', 1)
                prop['agent'] = agent_parts[0].strip()
                prop['agency'] = agent_parts[1].strip() if len(agent_parts) > 1 else ''
            result['newly_listed'].append(prop)

        elif current_section == 'sold':
            # Parts: address | beds | Guide: $X | Sold: $Y or Price Withheld | agent
            guide_m = re.search(r'Guide:\s*\$([\d,]+)', parts[2])
            if guide_m:
                prop['price_guide'] = '$' + guide_m.group(1)
            if len(parts) >= 4:
                sold_part = parts[3].strip()
                sold_m = re.search(r'Sold:\s*\$([\d,]+)', sold_part)
                if sold_m:
                    prop['sold_price'] = '$' + sold_m.group(1)
                elif 'Price Withheld' in sold_part:
                    prop['sold_price'] = 'Price Withheld'
            if len(parts) >= 5:
                agent_parts = parts[4].split('/', 1)
                prop['agent'] = agent_parts[0].strip()
                prop['agency'] = agent_parts[1].strip() if len(agent_parts) > 1 else ''
            result['sold'].append(prop)

        elif current_section == 'over_90_days':
            # Parts: address | beds | price | days | agent
            price_m = re.search(r'\$([\d,]+)', parts[2])
            if price_m:
                prop['price'] = '$' + price_m.group(1)
            if len(parts) >= 5:
                agent_parts = parts[4].split('/', 1)
                prop['agent'] = agent_parts[0].strip()
                prop['agency'] = agent_parts[1].strip() if len(agent_parts) > 1 else ''
            result['over_90_days'].append(prop)

        elif current_section == 'unlisted':
            price_m = re.search(r'\$([\d,]+)', parts[2])
            if price_m:
                prop['price'] = '$' + price_m.group(1)
            if len(parts) >= 4:
                agent_parts = parts[3].split('/', 1)
                prop['agent'] = agent_parts[0].strip()
                prop['agency'] = agent_parts[1].strip() if len(agent_parts) > 1 else ''
            result['unlisted'].append(prop)

    return result


def normalize_address(addr):
    """Normalize address for matching."""
    return re.sub(r'[^a-z0-9]', '', addr.lower())


def main():
    email_dir = os.path.join(os.path.dirname(__file__), 'proping_emails')
    all_data = []

    for fpath in sorted(glob.glob(os.path.join(email_dir, 'email_*.txt'))):
        parsed = parse_structured_email(fpath)
        if parsed['type'] == 'weekly':
            print(f"  {parsed['file']}: weekly summary (skipped for property injection)")
            continue

        pc = len(parsed['price_changes'])
        nl = len(parsed['newly_listed'])
        s = len(parsed['sold'])
        o90 = len(parsed['over_90_days'])
        ul = len(parsed['unlisted'])
        print(f"  {parsed['file']}: {pc} price changes, {nl} new, {s} sold, {o90} over90, {ul} unlisted")
        all_data.append(parsed)

    # Aggregate all properties
    all_price_changes = []
    all_newly_listed = []
    all_sold = []
    all_over_90 = []
    all_unlisted = []

    for email in all_data:
        all_price_changes.extend(email['price_changes'])
        all_newly_listed.extend(email['newly_listed'])
        all_sold.extend(email['sold'])
        all_over_90.extend(email['over_90_days'])
        all_unlisted.extend(email['unlisted'])

    # Build propingHistory entries (grouped by date + suburb group)
    proping_history = []
    for email in all_data:
        entry = {
            'date': email['date'],
            'suburbs': email['suburbs'],
            'price_changes': email['price_changes'],
            'newly_listed': email['newly_listed'],
            'sold': email['sold'],
            'over_90_days': email['over_90_days'],
            'unlisted': email['unlisted'],
        }
        proping_history.append(entry)

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"  Emails processed: {len(all_data)}")
    print(f"  Total price changes: {len(all_price_changes)}")
    print(f"  Total newly listed: {len(all_newly_listed)}")
    print(f"  Total sold: {len(all_sold)}")
    print(f"  Total over 90 days: {len(all_over_90)}")
    print(f"  Total unlisted: {len(all_unlisted)}")

    # Sold properties with actual prices
    sold_with_price = [s for s in all_sold if s.get('sold_price') and s['sold_price'] != 'Price Withheld']
    print(f"  Sold with actual price: {len(sold_with_price)}")
    for s in sold_with_price:
        print(f"    {s['address']}: Guide {s.get('price_guide','?')} → Sold {s['sold_price']}")

    # Save all parsed data
    output = os.path.join(email_dir, 'all_parsed.json')
    with open(output, 'w') as f:
        json.dump({
            'proping_history': proping_history,
            'all_price_changes': all_price_changes,
            'all_newly_listed': all_newly_listed,
            'all_sold': all_sold,
            'all_over_90_days': all_over_90,
            'all_unlisted': all_unlisted,
        }, f, indent=2)
    print(f"\nSaved to {output}")

    # Generate JS snippet for injection
    js_output = os.path.join(email_dir, 'proping_inject.js')
    with open(js_output, 'w') as f:
        f.write("// Proping email data extracted from Outlook\n")
        f.write("// Generated by parse_and_inject.py\n\n")
        f.write("const propingEmailData = ")
        json.dump(proping_history, f, indent=2)
        f.write(";\n")
    print(f"Saved JS snippet to {js_output}")


if __name__ == '__main__':
    main()
