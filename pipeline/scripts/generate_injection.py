#!/usr/bin/env python3
"""Generate propingHistory entries from parsed email data for injection into the app."""
import json, os, re
from urllib.parse import quote

def make_domain_url(address):
    """Generate a Domain.com.au search URL for an address."""
    # Clean address
    addr = address.strip()
    # Add NSW Australia
    q = f"{addr}, NSW, Australia"
    return f"https://www.domain.com.au/sale/?q={quote(q, safe='')}"

def format_date_au(iso_date):
    """Convert YYYY-MM-DD to DD/MM/YYYY."""
    parts = iso_date.split('-')
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return iso_date

def build_proping_entry(email_data):
    """Build a propingHistory entry from parsed email data."""
    date_au = format_date_au(email_data['date'])

    entry = {
        'date': date_au,
        'price_changes': [],
        'newly_listed': [],
        'sold': [],
    }

    # Price changes
    for p in email_data.get('price_changes', []):
        prop = {
            'address': p['address'],
            'suburb': p.get('suburb', ''),
            'beds': str(p.get('beds', '')),
            'price': p.get('price', ''),
            'price_change': p.get('price_change', ''),
            'agent': p.get('agent', ''),
            'agency': p.get('agency', ''),
            'source': 'proping_email',
            'date': date_au,
            'domain_url': make_domain_url(p['address']),
        }
        entry['price_changes'].append(prop)

    # Newly listed
    for p in email_data.get('newly_listed', []):
        prop = {
            'address': p['address'],
            'suburb': p.get('suburb', ''),
            'beds': str(p.get('beds', '')),
            'price': p.get('price', ''),
            'agent': p.get('agent', ''),
            'agency': p.get('agency', ''),
            'source': 'proping_email',
            'date': date_au,
            'domain_url': make_domain_url(p['address']),
        }
        entry['newly_listed'].append(prop)

    # Sold
    for p in email_data.get('sold', []):
        prop = {
            'address': p['address'],
            'suburb': p.get('suburb', ''),
            'beds': str(p.get('beds', '')),
            'price': p.get('price_guide', p.get('price', '')),
            'agent': p.get('agent', ''),
            'agency': p.get('agency', ''),
            'source': 'proping_email',
            'date': date_au,
            'domain_url': make_domain_url(p['address']),
        }
        if p.get('price_guide'):
            prop['price_guide'] = p['price_guide']
        if p.get('sold_price'):
            prop['sold_price'] = p['sold_price']
        entry['sold'].append(prop)

    # Over 90 days - add to newly_listed with days_listed
    for p in email_data.get('over_90_days', []):
        prop = {
            'address': p['address'],
            'suburb': p.get('suburb', ''),
            'beds': str(p.get('beds', '')),
            'days_listed': '90',
            'price': p.get('price', ''),
            'agent': p.get('agent', ''),
            'agency': p.get('agency', ''),
            'source': 'proping_email',
            'date': date_au,
            'domain_url': make_domain_url(p['address']),
        }
        entry['newly_listed'].append(prop)

    # Unlisted
    for p in email_data.get('unlisted', []):
        prop = {
            'address': p['address'],
            'suburb': p.get('suburb', ''),
            'beds': str(p.get('beds', '')),
            'price': p.get('price', ''),
            'agent': p.get('agent', ''),
            'agency': p.get('agency', ''),
            'source': 'proping_email',
            'date': date_au,
            'unlisted': True,
            'domain_url': make_domain_url(p['address']),
        }
        entry['newly_listed'].append(prop)

    return entry


def main():
    email_dir = os.path.join(os.path.dirname(__file__), 'proping_emails')
    parsed_file = os.path.join(email_dir, 'all_parsed.json')

    with open(parsed_file) as f:
        data = json.load(f)

    # Build propingHistory entries
    new_entries = []
    for email in data['proping_history']:
        entry = build_proping_entry(email)
        total = len(entry['price_changes']) + len(entry['newly_listed']) + len(entry['sold'])
        if total > 0:
            new_entries.append(entry)

    # Sort by date (newest first)
    def date_sort_key(e):
        d = e['date']  # DD/MM/YYYY
        parts = d.split('/')
        if len(parts) == 3:
            return f"{parts[2]}{parts[1]}{parts[0]}"
        return d
    new_entries.sort(key=date_sort_key, reverse=True)

    print(f"Generated {len(new_entries)} propingHistory entries")

    # Generate JS to append to propingHistory
    js_snippet = json.dumps(new_entries, indent=2)

    # Save
    output = os.path.join(email_dir, 'new_proping_entries.json')
    with open(output, 'w') as f:
        f.write(js_snippet)
    print(f"Saved to {output}")

    # Also generate a summary of sold properties with prices for cross-referencing
    print("\n=== SOLD PROPERTIES (for cross-referencing with app data) ===")
    for s in data['all_sold']:
        sp = s.get('sold_price', '?')
        pg = s.get('price_guide', s.get('price', '?'))
        print(f"  {s['address']} | Guide: {pg} | Sold: {sp} | Date: {s['date']}")


if __name__ == '__main__':
    main()
