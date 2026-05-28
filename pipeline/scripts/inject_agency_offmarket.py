import json, re
from pathlib import Path
from datetime import datetime

APP_PATH = Path(__file__).resolve().parent.parent / "mazar_martin_app.html"
AGENCY_FILE = Path(__file__).resolve().parent.parent / "agency_websites_listings.json"

def normalize(addr):
    return re.sub(r"[^a-z0-9]", " ", (addr or "").lower()).split()

def addr_match(a, b):
    ta, tb = normalize(a), normalize(b)
    return len(set(ta) & set(tb)) >= 2 if ta and tb else False

def extract(html, key):
    m = re.search('"' + key + r'"\s*:\s*(\[.*?\])\s*[,}]', html, re.DOTALL)
    return (json.loads(m.group(1)), m.start(1), m.end(1)) if m else ([], -1, -1)

html = APP_PATH.read_text(encoding="utf-8")
fs, _, _ = extract(html, "sampleListings")
om, s, e = extract(html, "sampleOff")

agency_listings = json.load(open(AGENCY_FILE))

# Build for-sale address list for dedup
fs_addrs = [p.get("address", "") for p in fs]
om_addrs = [p.get("address", "") for p in om]

added = 0
skipped_online = 0
skipped_duplicate = 0

for p in agency_listings:
    addr = p.get("address", "")
    if not addr:
        continue

    # Skip if already in for sale
    if any(addr_match(addr, fa) for fa in fs_addrs):
        skipped_online += 1
        continue

    # Skip if already in off market
    if any(addr_match(addr, oa) for oa in om_addrs):
        skipped_duplicate += 1
        continue

    # Add to off market
    om.append({
        "date": datetime.now().strftime("%-d %b"),
        "agent": p.get("agent", ""),
        "address": addr,
        "suburb": p.get("suburb", ""),
        "price": p.get("price", ""),
        "beds": p.get("beds", ""),
        "baths": p.get("baths", ""),
        "car": p.get("parking", ""),
        "type": p.get("propertyType", ""),
        "comments": "",
        "source": "agency_website",
        "agency": p.get("agency", "")
    })
    om_addrs.append(addr)
    added += 1

print(f"Added: {added} | Already online: {skipped_online} | Already in off-market: {skipped_duplicate}")

html = APP_PATH.read_text(encoding="utf-8")
_, s, e = extract(html, "sampleOff")
APP_PATH.write_text(html[:s] + json.dumps(om, indent=2) + html[e:], encoding="utf-8")
print("Done.")
