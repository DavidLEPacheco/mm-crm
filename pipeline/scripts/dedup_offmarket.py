import json, re
from pathlib import Path
from datetime import datetime

APP_PATH = Path("/Users/gf/Downloads/mazar_martin_app.html")
LOG_PATH = Path("/Users/gf/Downloads/lns_agents_scripts/dedup_offmarket.log")

def normalize(addr):
    return re.sub(r"[^a-z0-9]", " ", (addr or "").lower()).split()

def addr_match(a, b):
    ta, tb = normalize(a), normalize(b)
    return len(set(ta) & set(tb)) >= 2 if ta and tb else False

def extract(html, key):
    m = re.search('"'+ key + r'"\s*:\s*(\[.*?\])\s*[,}]', html, re.DOTALL)
    return (json.loads(m.group(1)), m.start(1), m.end(1)) if m else ([], -1, -1)

def log(msg):
    line = "[" + datetime.now().strftime("%Y-%m-%d %H:%M") + "] " + msg
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

html = APP_PATH.read_text(encoding="utf-8")
fs, _, _ = extract(html, "sampleListings")
om, s, e = extract(html, "sampleOff")
log("For sale: " + str(len(fs)))
log("Off-market before: " + str(len(om)))
if s == -1:
    log("ERROR: sampleOff not found")
    raise SystemExit(1)
oa = [p.get("address", "") for p in fs]
rm, kt = [], []
for p in om:
    a = p.get("address", "")
    if any(addr_match(a, x) for x in oa):
        rm.append(a)
        log("  REMOVED: " + a)
    else:
        kt.append(p)
log("Removed: " + str(len(rm)) + " | After: " + str(len(kt)))
if rm:
    APP_PATH.write_text(html[:s] + json.dumps(kt, indent=2) + html[e:], encoding="utf-8")
    log("HTML updated.")
else:
    log("No changes needed.")
log("Done.")
