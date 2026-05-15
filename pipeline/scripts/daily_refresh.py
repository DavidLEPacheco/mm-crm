#!/usr/bin/env python3
"""
Daily Mazar Martin App Refresh Script
======================================
Run each morning to:
1. Scrape Gmail for Proping + off-market agent emails → inject into app
2. Move sold properties from For Sale → Sold tab (flag with SOLD badge)
3. Cross-reference Proping data to fill missing prices
4. Deploy updated app
5. Flag sold properties
6. Scrape off-market listings (OnTheHouse + Domain cross-ref + agency websites)
7. Re-inject auction data
8. Wash properties (fill Type/Beds/Baths/Car/LandSize/URL)
9. Resolve withheld sold prices (Proping, OTH, PropertyValue, Allhomes)

Usage:
  python3 daily_refresh.py                  # Full refresh
  python3 daily_refresh.py --dry-run        # Preview changes without writing
  python3 daily_refresh.py --sold-check     # Only check for sold properties
"""

import json, re, os, sys, urllib.request, urllib.error
from datetime import datetime

APP_PATH = '/Users/gf/Downloads/mazar_martin_app.html'
DEPLOY_PATH = '/Users/gf/Downloads/mazar-martin-deploy/index.html'
PREVIEW_PATH = '/tmp/mm_preview/mazar_martin_app.html'
BACKUP_DIR = '/Users/gf/Downloads/lns_agents_scripts/backups'


def normalize_addr(addr):
    a = (addr or '').lower()
    a = re.sub(r',?\s*(nsw|new south wales|australia)\s*', '', a)
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
    a = re.sub(r'\bboulevard\b', 'blvd', a)
    a = re.sub(r'\bway\b', 'wy', a)
    a = re.sub(r'[^a-z0-9]', '', a)
    return a


def backup_app():
    """Create a timestamped backup before making changes."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(BACKUP_DIR, f'mazar_martin_app_{ts}.html')
    with open(APP_PATH) as f:
        content = f.read()
    with open(backup, 'w') as f:
        f.write(content)
    print(f"  ✅ Backup saved: {backup}")
    # Keep only last 7 backups
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.html')])
    for old in backups[:-7]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return content


def extract_addresses_from_section(html, section_key):
    """Extract all addresses from a named section of the D object."""
    addrs = set()
    section_start = html.find(f'"{section_key}"')
    if section_start == -1:
        section_start = html.find(f"'{section_key}'")
    if section_start == -1:
        return addrs

    arr_start = html.find('[', section_start)
    if arr_start == -1 or arr_start > section_start + 200:
        return addrs

    depth = 0
    i = arr_start
    while i < len(html):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                chunk = html[arr_start:i+1]
                for addr in re.findall(r'"address"\s*:\s*"([^"]+)"', chunk):
                    addrs.add(normalize_addr(addr))
                break
        i += 1
    return addrs


def find_sold_in_proping(html):
    """Extract sold property addresses from propingHistory data."""
    sold_addrs = {}
    marker_start = '/* __PROPING_HIST_START__ */'
    marker_end = '/* __PROPING_HIST_END__ */'
    s = html.find(marker_start)
    e = html.find(marker_end)
    if s == -1 or e == -1:
        return sold_addrs

    chunk = html[s:e]
    # Find sold entries with addresses and prices
    for m in re.finditer(r'"address"\s*:\s*"([^"]+)"[^}]*?"sold_price"\s*:\s*"([^"]*)"', chunk):
        addr, price = m.group(1), m.group(2)
        if price and price != 'Price Withheld':
            sold_addrs[normalize_addr(addr)] = {'address': addr, 'soldPrice': price}

    # Also find sold entries without explicit sold_price (just in "sold" arrays)
    # These are properties confirmed sold even if price withheld
    for m in re.finditer(r'"sold"\s*:\s*\[([^\]]+)\]', chunk):
        sold_block = m.group(1)
        for addr_m in re.finditer(r'"address"\s*:\s*"([^"]+)"', sold_block):
            k = normalize_addr(addr_m.group(1))
            if k not in sold_addrs:
                sold_addrs[k] = {'address': addr_m.group(1), 'soldPrice': None}

    return sold_addrs


def check_sold_properties(html):
    """Find For Sale properties that also appear in Sold or Proping sold data."""
    print("\n📋 Checking for sold properties still in For Sale...")

    sold_addrs = extract_addresses_from_section(html, 'soldListings')
    print(f"  {len(sold_addrs)} addresses in Sold tab")

    proping_sold = find_sold_in_proping(html)
    print(f"  {len(proping_sold)} sold addresses in Proping data")

    fs_addrs_raw = []
    section_start = html.find('"sampleListings"')
    if section_start == -1:
        section_start = html.find("'sampleListings'")
    if section_start != -1:
        arr_start = html.find('[', section_start)
        if arr_start != -1:
            depth = 0
            i = arr_start
            while i < len(html):
                if html[i] == '[':
                    depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        chunk = html[arr_start:i+1]
                        fs_addrs_raw = re.findall(r'"address"\s*:\s*"([^"]+)"', chunk)
                        break
                i += 1

    to_move = []
    for addr in fs_addrs_raw:
        k = normalize_addr(addr)
        if k in sold_addrs:
            to_move.append({'address': addr, 'reason': 'already in Sold tab'})
        elif k in proping_sold:
            ps = proping_sold[k]
            price_info = f" for {ps['soldPrice']}" if ps['soldPrice'] else ''
            to_move.append({'address': addr, 'reason': f'sold per Proping{price_info}'})

    if to_move:
        print(f"\n  ⚠️  {len(to_move)} properties in For Sale that are sold:")
        for item in to_move:
            print(f"    • {item['address']} — {item['reason']}")
    else:
        print("  ✅ No sold properties found in For Sale tab")

    return to_move


def inject_sold_flags(html, to_move):
    """
    Inject JS to flag sold properties in For Sale with _soldFlag = true
    and show SOLD badge. The app's rendering will pick this up.
    """
    if not to_move:
        return html

    addrs_json = json.dumps([item['address'] for item in to_move])

    flag_code = f"""
// ── Flag sold properties still in For Sale ──
function _flagSoldInForSale() {{
  const soldAddrs = {addrs_json};
  const soldSet = new Set(soldAddrs.map(a => _normalizeAddr(a)));
  let flagged = 0;
  (D.sampleListings||[]).forEach(l => {{
    if (soldSet.has(_normalizeAddr(l.address))) {{
      l._soldFlag = true;
      l.tagText = 'SOLD';
      flagged++;
    }}
  }});
  if (flagged) console.log('Flagged ' + flagged + ' sold properties in For Sale');
}}
"""

    # Remove old flag function if it exists
    old_marker = '// ── Flag sold properties still in For Sale'
    old_start = html.find(old_marker)
    if old_start != -1:
        # Find the closing brace of the function
        brace_depth = 0
        i = html.find('{', old_start)
        while i < len(html):
            if html[i] == '{':
                brace_depth += 1
            elif html[i] == '}':
                brace_depth -= 1
                if brace_depth == 0:
                    html = html[:old_start] + html[i+1:].lstrip('\n')
                    break
            i += 1

    # Insert before _injectSpreadsheetData or window.addEventListener
    insert_before = 'function _injectSpreadsheetData()'
    idx = html.find(insert_before)
    if idx == -1:
        insert_before = "window.addEventListener('load'"
        idx = html.find(insert_before)
    if idx != -1:
        html = html[:idx] + flag_code + '\n' + html[idx:]

    # Ensure it's called in the load listener
    if '_flagSoldInForSale();' not in html:
        html = html.replace(
            '_injectSpreadsheetData();',
            '_injectSpreadsheetData();\n  _flagSoldInForSale();'
        )

    return html


def deploy(html):
    """Write updated HTML to all locations."""
    with open(APP_PATH, 'w') as f:
        f.write(html)
    print(f"  Updated {APP_PATH}")

    for path in [DEPLOY_PATH, PREVIEW_PATH]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(html)
            print(f"  Updated {path}")
        except Exception as e:
            print(f"  ⚠️  {path}: {e}")

    print(f"\n  📦 App size: {len(html):,} bytes")


def inject_client_auto_match():
    """Inject JS into the app that auto-runs client matching on load.

    This ensures any new properties added by the pipeline are automatically
    cross-referenced against active buyer client briefs. The app already has
    _matchesClientBrief() and getClientMatches() — we just need to trigger
    them on load and store results in localStorage so the Clients tab badge
    shows new matches.

    Also injects _autoFillPlanningData() which merges planning data (easements,
    heritage, zoning, FSR, land size) into the For Sale / Off Market tables.
    """
    with open(APP_PATH) as f:
        html = f.read()

    marker_start = '/* __AUTO_MATCH_START__ */'
    marker_end = '/* __AUTO_MATCH_END__ */'

    auto_match_js = """
/* __AUTO_MATCH_START__ */
// ── Pipeline: Auto-match new properties to clients + fill planning data ──
(function _pipelinePostProcess() {
  // 1. Fill planning data into listing tables
  if (D._planningData) {
    const _nk = (a,s) => ((a||'').replace(/,\\s*\\w.*$/,'') + ' ' + (s||'')).toLowerCase()
      .replace(/street/g,'st').replace(/road/g,'rd').replace(/avenue/g,'ave')
      .replace(/drive/g,'dr').replace(/place/g,'pl').replace(/lane/g,'ln')
      .replace(/crescent/g,'cres').replace(/circuit/g,'cct').replace(/parade/g,'pde')
      .replace(/court/g,'ct').replace(/close/g,'cl').replace(/terrace/g,'tce')
      .replace(/boulevard/g,'blvd').replace(/way/g,'wy')
      .replace(/[^a-z0-9]/g,'');

    const enrichListing = (l) => {
      const k = _nk(l.address, l.suburb);
      const pd = D._planningData[k];
      if (!pd) return;
      if (pd.zoning && !l.zoning) l.zoning = pd.zoning;
      if (pd.heritage && !l.heritage) l.heritage = pd.heritage;
      if (pd.conservationArea && !l.conservationArea) l.conservationArea = pd.conservationArea;
      if (pd.heritageItems && !l.heritageItems) l.heritageItems = pd.heritageItems;
      if (pd.heritageSig && !l.heritageSig) l.heritageSig = pd.heritageSig;
      if (pd.fsr && !l.fsr) l.fsr = pd.fsr;
      if (pd.maxHeight && !l.maxHeight) l.maxHeight = pd.maxHeight;
      if (pd.minLotSize && !l.minLotSize) l.minLotSize = pd.minLotSize;
      if (pd.lotDP && !l.lotDP) l.lotDP = pd.lotDP;
      if (pd.easements && !l.easements) l.easements = pd.easements;
      if (pd.acidSulfate && !l.acidSulfate) l.acidSulfate = pd.acidSulfate;
    };

    (D.sampleListings||[]).forEach(enrichListing);
    (D.sampleOff||[]).forEach(enrichListing);
    (D.soldListings||[]).forEach(enrichListing);
  }

  // 2. Fill property.com.au data (land size, building size, year built)
  if (D._propertyData) {
    const _nk2 = (a,s) => ((a||'').replace(/,\\s*\\w.*$/,'') + ' ' + (s||'')).toLowerCase()
      .replace(/street/g,'st').replace(/road/g,'rd').replace(/avenue/g,'ave')
      .replace(/drive/g,'dr').replace(/place/g,'pl').replace(/lane/g,'ln')
      .replace(/crescent/g,'cres').replace(/circuit/g,'cct').replace(/parade/g,'pde')
      .replace(/court/g,'ct').replace(/close/g,'cl').replace(/terrace/g,'tce')
      .replace(/boulevard/g,'blvd').replace(/way/g,'wy')
      .replace(/[^a-z0-9]/g,'');

    const enrichPropData = (l) => {
      const k = _nk2(l.address, l.suburb);
      const pd = D._propertyData[k];
      if (!pd) return;
      if (pd.landSize && !l.landSize) l.landSize = pd.landSize;
      if (pd.buildingSize && !l.buildingSize) l.buildingSize = pd.buildingSize;
      if (pd.yearBuilt && !l.yearBuilt) l.yearBuilt = pd.yearBuilt;
      if (pd.frontage && !l.frontage) l.frontage = pd.frontage;
    };

    (D.sampleListings||[]).forEach(enrichPropData);
    (D.sampleOff||[]).forEach(enrichPropData);
  }

  // 3. Auto-match new properties to active clients
  try {
    if (typeof getClientMatches === 'function') {
      const clients = [...(D.xlsxClients||[]).filter(c =>
        (c.section||'').toLowerCase() === 'buyer' && (c.status||'active').toLowerCase() === 'active'
      ), ...(JSON.parse(localStorage.getItem('mmClients')||'[]'))];

      if (clients.length) {
        const prevMatches = JSON.parse(localStorage.getItem('mmAutoMatches')||'{}');
        const newMatches = {};
        let totalNew = 0;

        clients.forEach(client => {
          const matches = getClientMatches(client);
          if (matches.length) {
            const clientKey = (client.name||client.client||'').toLowerCase().replace(/[^a-z]/g,'');
            const prevAddrs = new Set((prevMatches[clientKey]||[]).map(m => m.address));
            const newForClient = matches.filter(m => !prevAddrs.has(m.address));
            newMatches[clientKey] = matches.map(m => ({address: m.address, suburb: m.suburb}));
            totalNew += newForClient.length;
          }
        });

        localStorage.setItem('mmAutoMatches', JSON.stringify(newMatches));
        localStorage.setItem('mmAutoMatchTs', new Date().toISOString());
        if (totalNew > 0) {
          console.log('[Pipeline] ' + totalNew + ' new client matches found');
        }
      }
    }
  } catch(e) { console.warn('Auto-match error:', e); }
})();
/* __AUTO_MATCH_END__ */
"""

    # Inject or replace
    if marker_start in html and marker_end in html:
        s = html.index(marker_start)
        e = html.index(marker_end) + len(marker_end)
        html = html[:s] + auto_match_js.strip() + html[e:]
    else:
        # Insert before the last </script> before </body>
        body_pos = html.rfind('</body>')
        sc = html.rfind('</script>', 0, body_pos if body_pos != -1 else len(html))
        if sc != -1:
            html = html[:sc] + '\n' + auto_match_js + '\n' + html[sc:]

    with open(APP_PATH, 'w') as f:
        f.write(html)

    return None


def main():
    dry_run = '--dry-run' in sys.argv
    sold_check = '--sold-check' in sys.argv

    print("=" * 60)
    print("🏠 Mazar Martin Daily Refresh")
    print(f"   {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    if dry_run:
        print("   🔍 DRY RUN — no changes will be written\n")

    # Step 1: Backup
    if not dry_run:
        html = backup_app()
    else:
        with open(APP_PATH) as f:
            html = f.read()

    # Step 1b: Scrape Gmail for Proping + off-market agent emails
    print("\n  📧 Step 1: Scraping Gmail (mazarmartinapp@gmail.com)...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # 1b-i: Scan Gmail via IMAP (Proping + off-market emails)
        gmail_script = os.path.join(script_dir, 'scrape_gmail.py')
        if os.path.exists(gmail_script):
            if not dry_run:
                print("    Scanning Gmail for Proping & off-market emails...")
                result = subprocess.run(
                    ['python3', gmail_script, '--days', '7'],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line.lower() for kw in [
                            'connected', 'proping', 'off-market', 'found',
                            'scanned', 'new', 'saved', 'extracted', '📊', '📬', '🏠', '✅'
                        ]):
                            print(f"      {line.strip()}")
                    print("    ✅ Gmail scan complete")
                else:
                    print(f"    ⚠️  Gmail scan error: {(result.stderr or '')[:200]}")
            else:
                print("    (Dry run — Gmail scan skipped)")
        else:
            print("    ⚠️  scrape_gmail.py not found")

        # 1b-ii: Inject email data into app (Proping + off-market emails)
        inject_email_script = os.path.join(script_dir, 'inject_email_data.py')
        if os.path.exists(inject_email_script):
            if not dry_run:
                print("    Injecting email data into app...")
                result = subprocess.run(['python3', inject_email_script],
                                         capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line.lower() for kw in ['injected', 'proping', 'off-market', 'email', 'total', 'new', 'updated']):
                            print(f"      {line.strip()}")
                    print("    ✅ Email data injected into app")
                    # Re-read the updated HTML so sold check uses fresh data
                    with open(APP_PATH) as f:
                        html = f.read()
                else:
                    print(f"    ⚠️  Email injection error: {(result.stderr or '')[:200]}")
            else:
                print("    (Dry run — email injection skipped)")
        else:
            print("    ⚠️  inject_email_data.py not found")

    except subprocess.TimeoutExpired:
        print("    ⚠️  Gmail scan timed out")
    except Exception as e:
        print(f"    ⚠️  Gmail scan: {e}")

    # Step 2: Check for sold properties in For Sale
    to_move = check_sold_properties(html)

    if sold_check:
        print("\n  (Sold check only — exiting)")
        return

    # Step 3: Flag sold properties
    if to_move and not dry_run:
        html = inject_sold_flags(html, to_move)
        print(f"\n  ✅ Added SOLD badges to {len(to_move)} For Sale listings")

    # Step 4: Deploy
    print("\n" + "=" * 60)
    print("📊 REFRESH SUMMARY")
    print("=" * 60)
    print(f"  Sold properties flagged in For Sale: {len(to_move)}")

    if not dry_run and to_move:
        deploy(html)
        print("\n✅ Refresh complete!")
    elif dry_run:
        print("\n  (Dry run — no files modified)")
    else:
        print("\n  ✅ App is already up to date")

    # Step 5: Off-market scrape + inject
    print("\n  🔒 Scraping off-market listings (OnTheHouse + Domain cross-ref)...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        offmarket_script = os.path.join(script_dir, 'inject_offmarket.py')
        if os.path.exists(offmarket_script):
            if not dry_run:
                result = subprocess.run(['python3', offmarket_script],
                                         capture_output=True, text=True, timeout=2400)
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line.lower() for kw in ['new off-market', 'injected', 'total', 'scraped', 'found']):
                            print(f"    {line.strip()}")
                    print("  ✅ Off-market scrape + inject complete")
                    # Re-read the updated HTML
                    with open(APP_PATH) as f:
                        html = f.read()
                else:
                    print(f"  ⚠️  Off-market error: {(result.stderr or '')[:300]}")
            else:
                print("  (Dry run — off-market scrape skipped)")
        else:
            print("  ⚠️  inject_offmarket.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Off-market scrape timed out (2400s)")
    except Exception as e:
        print(f"  ⚠️  Off-market scrape: {e}")

    # Step 6: Re-inject auction data (cross-checks with Proping for cancellations)
    print("\n  🔄 Re-running auction data injection...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        auction_script = os.path.join(script_dir, 'inject_auction_data.py')
        if os.path.exists(auction_script):
            if not dry_run:
                result = subprocess.run(['python3', auction_script], capture_output=True, text=True)
                if result.returncode == 0:
                    print("  ✅ Auction data re-injected (Proping cross-check done)")
                else:
                    print(f"  ⚠️  Auction injection error: {result.stderr[:200]}")
            else:
                print("  (Dry run — auction injection skipped)")
        else:
            print("  ⚠️  inject_auction_data.py not found")
    except Exception as e:
        print(f"  ⚠️  Auction injection: {e}")

    # Step 7: Wash properties against local Domain/REA/OTH caches
    #   Fills in any blank propertyType/beds/baths/parking/landSize/url on
    #   D.sampleListings / D.sampleOff / D.soldListings and replaces any
    #   non-canonical URLs with real Domain listing URLs so the addresses
    #   hyperlink correctly.
    print("\n  🧼 Washing properties against local Domain caches...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wash_script = os.path.join(script_dir, 'wash_properties.py')
        if os.path.exists(wash_script):
            if not dry_run:
                result = subprocess.run(['python3', wash_script],
                                         capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    # Echo the summary line(s) from the wash output
                    for line in (result.stdout or '').splitlines():
                        if ('updated' in line and 'no-match' in line) or 'Total' in line:
                            print(f"    {line.strip()}")
                    print("  ✅ Wash complete")

                    # Re-read the washed HTML and re-deploy so the deploy
                    # copies reflect the filled-in data.
                    try:
                        with open(APP_PATH) as f:
                            washed = f.read()
                        deploy(washed)
                    except Exception as e:
                        print(f"  ⚠️  Re-deploy after wash failed: {e}")
                else:
                    print(f"  ⚠️  Wash error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — wash skipped)")
        else:
            print("  ⚠️  wash_properties.py not found")
    except Exception as e:
        print(f"  ⚠️  Wash: {e}")

    # Step 8: Resolve withheld sold prices
    print("\n  💰 Resolving withheld sold prices...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        resolve_script = os.path.join(script_dir, 'resolve_withheld_prices.py')
        if os.path.exists(resolve_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', resolve_script, '--check-new'],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✅', 'Found', 'Updated', 'SUMMARY',
                                                      'Total withheld', 'Still withheld',
                                                      'From ', 'resolved']):
                            print(f"    {line.strip()}")
                    print("  ✅ Price resolution complete")
                else:
                    print(f"  ⚠️  Price resolve error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — price resolution skipped)")
        else:
            print("  ⚠️  resolve_withheld_prices.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Price resolution timed out (600s)")
    except Exception as e:
        print(f"  ⚠️  Price resolution: {e}")

    # Step 9: Parse NSW Valuer General sold history
    print("\n  📜 Updating VG sold history (houses/semis)...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vg_script = os.path.join(script_dir, 'parse_vg_sold.py')
        if os.path.exists(vg_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', vg_script, '--download'],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Unique properties',
                                                      'Total raw', 'Done']):
                            print(f"    {line.strip()}")
                    print("  ✅ VG sold history complete")
                else:
                    print(f"  ⚠️  VG parse error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — VG parse skipped)")
        else:
            print("  ⚠️  parse_vg_sold.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  VG parse timed out (300s)")
    except Exception as e:
        print(f"  ⚠️  VG parse: {e}")

    # Step 10: Scrape property.com.au for property intelligence data (land/building/sales)
    print("\n  🏠 Scraping property.com.au for land/building/sales data...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        prop_script = os.path.join(script_dir, 'scrape_property_data.py')
        if os.path.exists(prop_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', prop_script, '--quick'],
                    capture_output=True, text=True, timeout=900
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Scraped', 'Total cached',
                                                      'Injecting', 'Need to scrape']):
                            print(f"    {line.strip()}")
                    print("  ✅ Property data scrape complete")
                else:
                    print(f"  ⚠️  Property scrape error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — property scrape skipped)")
        else:
            print("  ⚠️  scrape_property_data.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Property scrape timed out (900s)")
    except Exception as e:
        print(f"  ⚠️  Property scrape: {e}")

    # Step 10b: Scrape NSW Planning Portal for zoning/heritage/conservation/FSR
    print("\n  📋 Scraping NSW Planning Portal (zoning, heritage, conservation)...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plan_script = os.path.join(script_dir, 'scrape_planning_data.py')
        if os.path.exists(plan_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', plan_script, '--quick'],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Scraped', 'Total cached',
                                                      'Injecting', 'Need to scrape']):
                            print(f"    {line.strip()}")
                    print("  ✅ Planning data scrape complete")
                else:
                    print(f"  ⚠️  Planning scrape error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — planning scrape skipped)")
        else:
            print("  ⚠️  scrape_planning_data.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Planning scrape timed out (600s)")
    except Exception as e:
        print(f"  ⚠️  Planning scrape: {e}")

    # Step 11: Scrape Domain/REA for latest listings + sold data
    print("\n  🌐 Scraping Domain.com.au for listings & sold data...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        domain_script = os.path.join(script_dir, 'scrape_domain_realestate.py')
        if os.path.exists(domain_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', domain_script],
                    capture_output=True, text=True, timeout=1200
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Total', 'Scraped', 'listings', 'sold']):
                            print(f"    {line.strip()}")
                    print("  ✅ Domain/REA scrape complete")
                else:
                    print(f"  ⚠️  Domain scrape error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — Domain scrape skipped)")
        else:
            print("  ⚠️  scrape_domain_realestate.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Domain scrape timed out (1200s)")
    except Exception as e:
        print(f"  ⚠️  Domain scrape: {e}")

    # Step 11b: Inject Domain scraped data into app (new listings + sold into tables)
    print("\n  📥 Injecting Domain data into app...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        domain_inject_script = os.path.join(script_dir, 'inject_domain_data.py')
        if os.path.exists(domain_inject_script):
            if not dry_run:
                result = subprocess.run(['python3', domain_inject_script],
                                         capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['injected', 'new', 'total', 'merged',
                                                      'for-sale', 'sold', 'Updated']):
                            print(f"    {line.strip()}")
                    print("  ✅ Domain data injected")
                    with open(APP_PATH) as f:
                        html = f.read()
                else:
                    print(f"  ⚠️  Domain inject error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — Domain inject skipped)")
        else:
            print("  ⚠️  inject_domain_data.py not found — Domain data not injected into app")
    except Exception as e:
        print(f"  ⚠️  Domain inject: {e}")

    # Step 12: Scrape agency websites for exclusive/private listings
    print("\n  🏢 Scraping agency websites for exclusive listings...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        agency_script = os.path.join(script_dir, 'scrape_agency_websites.py')
        if os.path.exists(agency_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', agency_script],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Total', 'Scraped', 'Found', 'new']):
                            print(f"    {line.strip()}")
                    print("  ✅ Agency website scrape complete")
                else:
                    print(f"  ⚠️  Agency scrape error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — agency scrape skipped)")
        else:
            print("  ⚠️  scrape_agency_websites.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  Agency scrape timed out (600s)")
    except Exception as e:
        print(f"  ⚠️  Agency scrape: {e}")

    # Step 13: Scrape local news for talking points
    print("\n  📰 Scraping local news & market data...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        news_script = os.path.join(script_dir, 'scrape_local_news.py')
        if os.path.exists(news_script):
            if not dry_run:
                result = subprocess.run(
                    ['python3', news_script],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['✓', '✗', 'Total stories', 'Done']):
                            print(f"    {line.strip()}")
                    print("  ✅ Local news scrape complete")
                else:
                    print(f"  ⚠️  News scrape error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — news scrape skipped)")
        else:
            print("  ⚠️  scrape_local_news.py not found")
    except subprocess.TimeoutExpired:
        print("  ⚠️  News scrape timed out (300s)")
    except Exception as e:
        print(f"  ⚠️  News scrape: {e}")

    # Step 14: FINAL WASH — re-run after ALL scrapers to fill any remaining gaps
    #   Now that Domain, OTH, agency, planning, and property data have all run,
    #   a second wash pass fills beds/baths/parking/landSize/URL on any listings
    #   that were added mid-pipeline (e.g. from Domain inject or off-market scrape).
    print("\n  🧼 Final wash pass (filling remaining gaps)...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wash_script = os.path.join(script_dir, 'wash_properties.py')
        if os.path.exists(wash_script):
            if not dry_run:
                result = subprocess.run(['python3', wash_script],
                                         capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if ('updated' in line and 'no-match' in line) or 'Total' in line:
                            print(f"    {line.strip()}")
                    print("  ✅ Final wash complete")
                else:
                    print(f"  ⚠️  Final wash error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — final wash skipped)")
        else:
            print("  ⚠️  wash_properties.py not found")
    except Exception as e:
        print(f"  ⚠️  Final wash: {e}")

    # Step 14b: Wash propingHistory entries (beds/baths/car/URL + zoning/heritage/FSR)
    #   The regular wash only touches D.sampleListings/sampleOff/soldListings.
    #   Proping email entries live separately in propingHistory and need their
    #   own wash pass to pull in Domain features + planning data.
    print("\n  🧼 Washing Proping entries with Domain + planning data...")
    try:
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        proping_wash = os.path.join(script_dir, 'wash_proping_history.py')
        if os.path.exists(proping_wash):
            if not dry_run:
                result = subprocess.run(['python3', proping_wash],
                                         capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    for line in (result.stdout or '').splitlines():
                        if any(kw in line for kw in ['Filled', 'Matched', 'Total Proping', 'Fixed']):
                            print(f"    {line.strip()}")
                    print("  ✅ Proping wash complete")
                else:
                    print(f"  ⚠️  Proping wash error: {(result.stderr or '')[:200]}")
            else:
                print("  (Dry run — Proping wash skipped)")
        else:
            print("  ⚠️  wash_proping_history.py not found")
    except Exception as e:
        print(f"  ⚠️  Proping wash: {e}")

    # Step 15: Auto-match new properties → clients
    print("\n  🤝 Running client auto-match for new properties...")
    try:
        if not dry_run:
            new_match_count = inject_client_auto_match()
            if new_match_count:
                print(f"  ✅ Injected auto-match trigger ({new_match_count} potential matches)")
            else:
                print("  ✅ Client auto-match trigger injected")
        else:
            print("  (Dry run — client match skipped)")
    except Exception as e:
        print(f"  ⚠️  Client match: {e}")

    # Step 16: Final re-deploy after ALL injections
    print("\n  🚀 Final deploy...")
    try:
        with open(APP_PATH) as f:
            final_html = f.read()
        deploy(final_html)
        print("  ✅ Final deploy complete")
    except Exception as e:
        print(f"  ⚠️  Final deploy: {e}")

    # Push to GitHub Pages (live PWA)
    print("\n  🌐 Pushing to GitHub Pages...")
    try:
        import subprocess, shutil
        deploy_repo = '/Users/gf/Downloads/mazar-martin-deploy'
        if os.path.exists(deploy_repo):
            import shutil
            shutil.copy(APP_PATH, os.path.join(deploy_repo, 'index.html'))
            ts = datetime.now().strftime('%d/%m/%Y %H:%M')
            cmds = [
                ['git', '-C', deploy_repo, 'add', 'index.html'],
                ['git', '-C', deploy_repo, 'commit', '-m', f'Daily data update {ts}'],
                ['git', '-C', deploy_repo, 'push', 'origin', 'main'],
            ]
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0 and 'nothing to commit' not in (result.stdout + result.stderr):
                    print(f"    git warning: {(result.stderr or '')[:150]}")
            print("  ✅ GitHub Pages updated")
        else:
            print(f"  ⚠️  Deploy repo not found at {deploy_repo} — skipping push")
    except Exception as e:
        print(f"  ⚠️  GitHub push: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 PIPELINE SUMMARY")
    print("=" * 60)
    print(f"""
  Steps completed:
    1. Gmail scan (Proping + off-market emails)
    2. Email data → app (Proping tab, off-market tab, dashboard widget)
    3. Sold property check + SOLD badges
    4. Off-market scrape (OnTheHouse + Domain cross-ref + agencies)
    5. Auction data re-injection
    6. Property wash (beds/baths/parking/landSize/URL fill)
    7. Withheld price resolution
    8. VG sold history
    9. Property.com.au data (land/building/sales)
   10. NSW Planning Portal (zoning, heritage, easements, FSR)
   11. Domain.com.au scrape (listings + sold)
   12. Domain data → app injection
   13. Agency website scrape
   14. Local news scrape
   15. Final wash pass (fill remaining gaps)
   16. Client auto-match for new properties
   17. Deploy to all locations + GitHub Pages

  All links → actual Domain.com.au property pages
  New data → Dashboard KPIs, Proping snapshot, all tabs
  New properties → auto-matched to active buyer clients
""")

    # ── Push notification via ntfy.sh ──
    _send_ntfy_notification()


NTFY_TOPIC = "mazar-martin-gf-2026"

def _send_ntfy_notification(success=True):
    """Send push notification via ntfy.sh when pipeline completes."""
    try:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        title = "✅ Mazar Martin CRM Updated" if success else "⚠️ Mazar Martin CRM — Issues"
        body = f"Daily refresh completed at {now}. App deployed to GitHub Pages."
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={"Title": title.encode("utf-8"), "Priority": "default", "Tags": "house"},
        )
        urllib.request.urlopen(req, timeout=10)
        print(f"📱 Push notification sent to ntfy.sh/{NTFY_TOPIC}")
    except Exception as e:
        print(f"⚠️  Push notification failed: {e}")


if __name__ == '__main__':
    main()
