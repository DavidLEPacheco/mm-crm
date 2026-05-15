#!/usr/bin/env python3
"""
inject_email_data.py  —  Mazar Martin Dashboard Injector
=========================================================
Reads proping_history.json and offmarket_emails.json and injects/updates
the dashboard HTML with:

  1. A "Proping" tab — 7-day rolling snapshot, grouped by suburb, with
     all addresses hyperlinked to Domain.com.au
  2. Price-change annotations on matching For Sale listings
  3. Proping sold properties cross-referenced into the Sold tab
  4. Email off-market properties in the Off Market tab (separate section)
  5. A "Weekly Snapshot" widget on the Dashboard tab

Run after parse_proping.py and parse_offmarket_emails.py.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DOWNLOADS      = Path(__file__).parent.parent
DASHBOARD      = DOWNLOADS / 'mazar_martin_app.html'
HISTORY_FILE   = DOWNLOADS / 'proping_history.json'
OFFMKT_JSON    = DOWNLOADS / 'offmarket_emails.json'

# ── Injection markers ─────────────────────────────────────────────────────────
M_PROPING_DATA  = ('/* __PROPING_HIST_START__ */',  '/* __PROPING_HIST_END__ */')
M_OFFMKT_EMAIL  = ('/* __OFFMKT_EMAIL_START__ */',  '/* __OFFMKT_EMAIL_END__ */')


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"  Warning: could not read {path.name}: {e}")
    return default


def domain_search_url(address):
    """Return a Domain.com.au search URL for the given address."""
    import urllib.parse
    q = address + ', NSW, Australia'
    return 'https://www.domain.com.au/sale/?q=' + urllib.parse.quote(q)


def inject_or_replace(html, start_marker, end_marker, new_block):
    """Replace an existing marked block, or insert before the first </script>
    that appears after `const D =` in the document."""
    if start_marker in html and end_marker in html:
        s = html.index(start_marker)
        e = html.index(end_marker) + len(end_marker)
        return html[:s] + new_block + html[e:]
    # Insert point: just before closing </script> of the data section
    d_pos = html.find('const D =')
    if d_pos == -1:
        d_pos = 0
    sc = html.find('</script>', d_pos)
    if sc == -1:
        return html + '\n<script>\n' + new_block + '\n</script>'
    return html[:sc] + '\n' + new_block + '\n' + html[sc:]


# ── Aggregate 7-day history by suburb ────────────────────────────────────────

def aggregate_by_suburb(history):
    """
    From a list of daily history entries, build a per-suburb summary:
    {
      'Naremburn': {
          'price_changes': [...],
          'newly_listed':  [...],
          'sold':          [...],
      }, ...
    }
    Also returns a flat list of ALL properties (deduplicated by address).
    """
    suburb_map = defaultdict(lambda: {'price_changes': [], 'newly_listed': [], 'sold': []})
    all_addresses = set()
    all_props = {'price_changes': [], 'newly_listed': [], 'sold': []}

    for day in history:
        date_str = day.get('date', '')
        for section in ['price_changes', 'newly_listed', 'sold']:
            for prop in day.get(section, []):
                addr = prop.get('address', '').lower().strip()
                if not addr or addr in all_addresses:
                    continue
                all_addresses.add(addr)
                suburb = prop.get('suburb', 'Unknown').strip() or 'Unknown'
                # Ensure Domain URL present
                if not prop.get('domain_url'):
                    prop['domain_url'] = domain_search_url(prop.get('address', ''))
                prop['date'] = date_str  # preserve which day this came from
                suburb_map[suburb][section].append(prop)
                all_props[section].append(prop)

    return dict(suburb_map), all_props


# ── JS/HTML snippets ──────────────────────────────────────────────────────────

PROPING_CSS = """
/* ── Proping Tab + Dashboard Widget ─────────────────────────────────────── */
.p-suburb-block { margin-bottom: 24px; border-radius: 10px; overflow: hidden; border: 1px solid #e8e4da; }
.p-suburb-hdr {
  background: var(--green-dark); color: var(--cream);
  padding: 10px 16px; font-family: var(--ff-ui); font-size: 12px;
  font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  display: flex; align-items: center; gap: 10px;
}
.p-suburb-counts { display: flex; gap: 8px; margin-left: auto; }
.p-cnt { border-radius: 10px; padding: 1px 9px; font-size: 10px; font-weight: 700; }
.p-cnt-change { background:#fce4ec; color:#c62828; }
.p-cnt-new    { background:#e8f5e9; color:#2e7d32; }
.p-cnt-sold   { background:#e3f2fd; color:#1565c0; }
.p-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
  padding: 6px 14px; background: #fafaf8; border-bottom: 1px solid #eee;
  color: var(--text-mid);
}
.p-row {
  display: flex; align-items: baseline; gap: 10px;
  padding: 8px 14px; border-bottom: 1px solid #f2ede4;
  font-family: var(--ff-ui); font-size: 12px;
}
.p-row:last-child { border-bottom: none; }
.p-addr { font-weight: 700; color: var(--green-dark); }
.p-addr a { color: var(--green-dark); text-decoration: none; }
.p-addr a:hover { text-decoration: underline; }
.p-price { font-weight: 700; color: var(--text-dark); }
.p-change-neg { color: #c62828; font-weight: 700; }
.p-change-pos { color: #2e7d32; font-weight: 700; }
.p-agent { color: var(--text-light); font-size: 11px; margin-left: auto; }
.p-date-chip { font-size: 9px; background: #f0ede6; color: var(--text-light); border-radius: 8px; padding: 1px 6px; }
.p-beds { color: var(--text-mid); font-size: 11px; }
/* Dashboard snapshot widget */
.proping-snap {
  background: #fff; border-radius: 10px; border: 1px solid #e8e4da;
  padding: 16px; margin-bottom: 20px;
}
.proping-snap-title {
  font-family: var(--ff-serif); font-size: 18px; color: var(--green-dark);
  margin-bottom: 12px; border-bottom: 1px solid #e8e4da; padding-bottom: 8px;
}
.snap-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0; border-bottom: 1px solid #f5f0e8; font-size: 12px;
}
.snap-row:last-child { border-bottom: none; }
.snap-suburb { font-weight: 700; color: var(--green-dark); }
.snap-pills  { display: flex; gap: 6px; }
/* Email Off-Market rows */
.email-src-badge { background:#e8f0fe;color:#1a73e8;border-radius:10px;padding:1px 8px;font-size:9px;font-weight:700; }
"""

PROPING_TAB_HTML = """
<div class="page" id="page-proping">
  <div class="tab-header">
    <div>
      <div class="tab-title">📬 Proping — 7-Day Snapshot</div>
      <div class="tab-sub" id="proping-range-lbl">Loading…</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <input type="text" id="proping-q" placeholder="Search suburb or address…"
             style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;width:220px"
             oninput="renderPropingTab()">
      <select id="proping-section-filter"
              style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px"
              onchange="renderPropingTab()">
        <option value="">All Activity</option>
        <option value="price_changes">Price Changes</option>
        <option value="newly_listed">Newly Listed</option>
        <option value="sold">Sold</option>
      </select>
    </div>
  </div>
  <div id="proping-tab-body"></div>
</div>
"""

PROPING_JS = r"""
// ── Proping Tab ──────────────────────────────────────────────────────────────
function propAddrLink(p) {
  const url = p.domain_url || ('https://www.domain.com.au/sale/?q=' + encodeURIComponent((p.address||'') + ', NSW, Australia'));
  return `<a href="${url}" target="_blank" rel="noopener">${p.address}</a>`;
}

function renderPropRow(p, type) {
  const change = p.price_change
    ? `<span class="${p.price_change.startsWith('-') ? 'p-change-neg' : 'p-change-pos'}">${p.price_change}</span>`
    : '';
  const soldInfo = (type === 'sold' && p.sold_price)
    ? `<span class="p-price">${p.sold_price}</span><span class="p-agent" style="margin-left:4px">Guide: ${p.price_guide||'—'}</span>`
    : `<span class="p-price">${p.price||'—'}</span> ${change}`;
  const beds = p.beds ? `<span class="p-beds">${p.beds}bd${p.days_listed ? ' · '+p.days_listed+'d' : ''}</span>` : '';
  const agent = p.agent ? `<span class="p-agent">${p.agent}${p.agency ? ' / '+p.agency : ''}</span>` : '';
  const chip  = p.date  ? `<span class="p-date-chip">${p.date}</span>` : '';
  return `<div class="p-row">
    <span class="p-addr">${propAddrLink(p)}</span>
    ${beds}
    ${soldInfo}
    ${agent}
    ${chip}
  </div>`;
}

function renderPropingTab() {
  if (typeof propingHistory === 'undefined' || !propingHistory.length) {
    document.getElementById('proping-tab-body').innerHTML =
      '<p class="empty-msg" style="padding:24px">No Proping data yet. Run parse_proping.py to populate.</p>';
    document.getElementById('proping-range-lbl').textContent = 'No data';
    return;
  }

  const q       = (document.getElementById('proping-q')?.value || '').toLowerCase();
  const secFilt = document.getElementById('proping-section-filter')?.value || '';

  // Date range label
  const dates = propingHistory.map(e => e.date).filter(Boolean);
  document.getElementById('proping-range-lbl').textContent =
    dates.length > 1 ? `${dates[dates.length-1]} – ${dates[0]}` : (dates[0] || '');

  // Build suburb map from history (dedup by address across days)
  const seen = new Set();
  const suburbMap = {};
  for (const day of propingHistory) {
    for (const section of ['price_changes','newly_listed','sold']) {
      for (const p of (day[section] || [])) {
        const addr = (p.address||'').toLowerCase();
        if (!addr || seen.has(addr)) continue;
        seen.add(addr);
        const suburb = (p.suburb || 'Unknown').trim() || 'Unknown';
        if (!suburbMap[suburb]) suburbMap[suburb] = {price_changes:[],newly_listed:[],sold:[]};
        // Filter
        if (q && !addr.includes(q) && !suburb.toLowerCase().includes(q)) continue;
        if (secFilt && section !== secFilt) continue;
        suburbMap[suburb][section].push(p);
      }
    }
  }

  // Sort suburbs alphabetically; skip empty ones after filtering
  const suburbs = Object.keys(suburbMap)
    .filter(s => suburbMap[s].price_changes.length + suburbMap[s].newly_listed.length + suburbMap[s].sold.length > 0)
    .sort();

  if (!suburbs.length) {
    document.getElementById('proping-tab-body').innerHTML = '<p class="empty-msg" style="padding:24px">No matching properties.</p>';
    return;
  }

  const LABELS = {price_changes:'📉 Price Changes', newly_listed:'🆕 Newly Listed', sold:'🏷 Sold'};

  let html = '';
  for (const suburb of suburbs) {
    const d = suburbMap[suburb];
    const total = d.price_changes.length + d.newly_listed.length + d.sold.length;
    if (!total) continue;

    html += `<div class="p-suburb-block">
      <div class="p-suburb-hdr">
        🏘 ${suburb}
        <div class="p-suburb-counts">
          ${d.price_changes.length ? `<span class="p-cnt p-cnt-change">↓ ${d.price_changes.length} change${d.price_changes.length>1?'s':''}</span>` : ''}
          ${d.newly_listed.length  ? `<span class="p-cnt p-cnt-new">+ ${d.newly_listed.length} new</span>` : ''}
          ${d.sold.length          ? `<span class="p-cnt p-cnt-sold">✓ ${d.sold.length} sold</span>` : ''}
        </div>
      </div>`;

    for (const [key, label] of Object.entries(LABELS)) {
      if (d[key].length) {
        html += `<div class="p-section-label">${label}</div>`;
        html += d[key].map(p => renderPropRow(p, key)).join('');
      }
    }
    html += '</div>';
  }

  document.getElementById('proping-tab-body').innerHTML = html;
}

// ── Dashboard Snapshot Widget ─────────────────────────────────────────────────
function renderPropingSnapshot() {
  const el = document.getElementById('proping-snapshot-widget');
  if (!el) return;
  if (typeof propingHistory === 'undefined' || !propingHistory.length) {
    el.style.display = 'none';
    return;
  }

  // Aggregate by suburb (last 7 days, dedup)
  const seen = new Set();
  const subMap = {};
  for (const day of propingHistory) {
    for (const section of ['price_changes','newly_listed','sold']) {
      for (const p of (day[section] || [])) {
        const addr = (p.address||'').toLowerCase();
        if (!addr || seen.has(addr)) continue;
        seen.add(addr);
        const suburb = (p.suburb || 'Unknown').trim() || 'Unknown';
        if (!subMap[suburb]) subMap[suburb] = {c:0, n:0, s:0};
        if (section === 'price_changes') subMap[suburb].c++;
        if (section === 'newly_listed')  subMap[suburb].n++;
        if (section === 'sold')          subMap[suburb].s++;
      }
    }
  }

  const suburbs = Object.keys(subMap).sort();
  if (!suburbs.length) { el.style.display = 'none'; return; }

  const dates = propingHistory.map(e => e.date).filter(Boolean);
  const rangeLabel = dates.length > 1 ? `${dates[dates.length-1]} – ${dates[0]}` : (dates[0]||'');

  let rows = suburbs.map(s => {
    const d = subMap[s];
    return `<div class="snap-row">
      <span class="snap-suburb">${s}</span>
      <span class="snap-pills">
        ${d.c ? `<span class="p-cnt p-cnt-change">↓ ${d.c}</span>` : ''}
        ${d.n ? `<span class="p-cnt p-cnt-new">+ ${d.n}</span>` : ''}
        ${d.s ? `<span class="p-cnt p-cnt-sold">✓ ${d.s}</span>` : ''}
      </span>
    </div>`;
  }).join('');

  el.innerHTML = `
    <div class="proping-snap-title">📬 Proping Weekly Snapshot <span style="font-size:12px;color:var(--text-light);font-family:var(--ff-ui)">${rangeLabel}</span></div>
    ${rows}
    <div style="text-align:right;margin-top:8px">
      <button class="link" style="font-size:11px;cursor:pointer;background:none;border:none;color:var(--gold)"
        onclick="showPage('proping')">View full Proping report →</button>
    </div>`;
  el.style.display = 'block';
}
"""

SNAPSHOT_WIDGET_HTML = """<!-- Proping Snapshot Widget (injected) -->
<div id="proping-snapshot-widget" class="proping-snap" style="display:none"></div>
<!-- END Proping Snapshot Widget -->"""

EMAIL_OFFMKT_SECTION = """
<!-- Email Off-Markets Section (injected) -->
<div class="sec-hdr" style="margin-top:28px">
  <div class="sec-title">📧 Email Off-Markets <span class="email-src-badge">from inbox</span></div>
  <div class="sec-badge" id="email-off-lbl">0 properties</div>
</div>
<div class="tbl-controls" style="margin-bottom:8px">
  <input type="text" id="email-off-q" placeholder="Search address, agent…"
         style="padding:5px 10px;border:1px solid #ddd;border-radius:6px;font-size:12px;width:240px"
         oninput="renderEmailOff()">
</div>
<div class="table-wrap">
  <table class="data-table">
    <thead><tr>
      <th>Date</th><th>Address</th><th>Suburb</th>
      <th style="text-align:center">Bed</th><th style="text-align:center">Bath</th>
      <th>Price</th><th>Agent</th><th>Agency</th><th>Notes</th>
    </tr></thead>
    <tbody id="email-off-tbody"></tbody>
  </table>
</div>
<div id="email-off-pg" class="pg-bar"></div>
<!-- END Email Off-Markets Section -->"""

EMAIL_OFFMKT_JS = r"""
// ── Email Off-Markets ──────────────────────────────────────────────────────
let emailOffPg = 1;
function filtEmailOff() {
  if (typeof emailOffMarkets === 'undefined') return [];
  const q = (document.getElementById('email-off-q')?.value || '').toLowerCase();
  return emailOffMarkets.filter(o =>
    !q ||
    (o.address||'').toLowerCase().includes(q) ||
    (o.suburb||'').toLowerCase().includes(q)  ||
    (o.agent||'').toLowerCase().includes(q)   ||
    (o.agency||'').toLowerCase().includes(q)
  );
}
function renderEmailOff(pg) {
  emailOffPg = pg || 1;
  const d = filtEmailOff();
  document.getElementById('email-off-lbl').textContent = d.length + ' properties';
  showPage(d, 'email-off-tbody', emailOffPg, o =>
    `<tr>
      <td style="font-size:10px;color:var(--text-light)">${o.date||'—'}</td>
      <td style="font-weight:600">${o.address||'—'}</td>
      <td><span class="suburb-pill">${o.suburb||'—'}</span></td>
      <td style="text-align:center">${o.beds||'—'}</td>
      <td style="text-align:center">${o.baths||'—'}</td>
      <td class="price-cell">${o.price||'—'}</td>
      <td class="agent-name">${o.agent||'—'}</td>
      <td class="ag-sub">${o.agency||'—'}</td>
      <td style="font-size:10px;color:var(--text-mid)">${(o.notes||'').slice(0,100)}</td>
    </tr>`
  );
  renderPg('email-off-pg', d.length, emailOffPg, p => renderEmailOff(p));
}
"""


# ── Structural helpers ────────────────────────────────────────────────────────

def ensure_css(html, css_block, sentinel):
    if sentinel in html:
        return html
    pos = html.find('</style>')
    if pos != -1:
        return html[:pos] + css_block + html[pos:]
    return html


def ensure_nav_button(html):
    if 'page-proping' in html or "showPage('proping')" in html:
        return html
    for pat in ["showPage('allagents')", "showPage('topperformers')", "showPage('sold')"]:
        if pat in html:
            pos = html.find(pat)
            btn_end = html.find('</button>', pos)
            if btn_end != -1:
                insert = btn_end + len('</button>')
                btn = "\n          <button class=\"nav-btn\" onclick=\"showPage('proping')\">📬 Proping</button>"
                return html[:insert] + btn + html[insert:]
    return html


def ensure_proping_page(html):
    if 'id="page-proping"' in html:
        # Replace with latest version
        s = html.find('<div class="page" id="page-proping">')
        if s != -1:
            # Find the matching closing div
            depth = 0
            pos = s
            while pos < len(html):
                if html[pos:pos+4] == '<div':
                    depth += 1
                elif html[pos:pos+6] == '</div>':
                    depth -= 1
                    if depth == 0:
                        e = pos + 6
                        return html[:s] + PROPING_TAB_HTML.strip() + html[e:]
                pos += 1
        return html
    # Insert before </main> or before last page div
    if '</main>' in html:
        pos = html.rfind('</main>')
        return html[:pos] + PROPING_TAB_HTML + '\n' + html[pos:]
    if '</body>' in html:
        pos = html.rfind('</body>')
        return html[:pos] + PROPING_TAB_HTML + '\n' + html[pos:]
    return html + PROPING_TAB_HTML


def ensure_snapshot_widget(html):
    if 'proping-snapshot-widget' in html:
        return html
    # Insert into the dashboard page, after the first stats row / kpi row
    # Look for the dashboard page and the first <div class="kpi-grid"> or similar
    page_start = html.find('id="page-dashboard"')
    if page_start == -1:
        return html
    # Find first </div> after a 'kpi' or 'stat' block, or just after the tab-header
    hdr_end = html.find('</div>', page_start + 100)
    if hdr_end == -1:
        return html
    # Walk past 2 closing divs to get past the tab-header section
    hdr_end2 = html.find('</div>', hdr_end + 6)
    if hdr_end2 == -1:
        hdr_end2 = hdr_end
    insert_pos = hdr_end2 + 6
    return html[:insert_pos] + '\n' + SNAPSHOT_WIDGET_HTML + '\n' + html[insert_pos:]


def ensure_email_offmkt_in_offmarket_tab(html):
    """Merge email off-market properties into the Off Market tab's JS functions.

    The Off Market tab is dynamically built by buildOffMarketTab() and
    filterOffMarket() in JavaScript.  We patch those functions so they
    include emailOffMarkets alongside D.sampleOff and userAdded items.
    """
    EMAIL_OFF_MAP = ("(typeof emailOffMarkets !== 'undefined' ? emailOffMarkets : []).map(e => ({"
                     "date: e.date||'', agent: e.agent||'', address: e.address||'', suburb: e.suburb||'',"
                     "price: e.price||'', comments: (e.notes||'') + (e.agency ? ' ['+e.agency+']' : ''),"
                     "source: 'email', beds: e.beds||'', baths: e.baths||'', cars: e.cars||''"
                     "}))")

    # --- patch buildOffMarketTab ---
    old_build = "const suburbs = [...new Set((D.sampleOff||[]).map(l=>l.suburb))].sort();"
    new_build = (
        f"const emailOff = {EMAIL_OFF_MAP};\n"
        "  const suburbs = [...new Set([...(D.sampleOff||[]).map(l=>l.suburb), ...emailOff.map(l=>l.suburb)])].sort();"
    )
    if old_build in html and 'emailOff' not in html.split('buildOffMarketTab')[1].split('filterOffMarket')[0]:
        html = html.replace(old_build, new_build, 1)
        # Also patch the 'all' array in buildOffMarketTab
        html = html.replace(
            "const all = [...(D.sampleOff||[]), ...userAdded];",
            "const all = [...(D.sampleOff||[]), ...emailOff, ...userAdded];",
            1
        )

    # --- patch filterOffMarket ---
    old_filter = "let items = [...(D.sampleOff||[]), ...userAdded];"
    new_filter = (
        f"const emailOff = {EMAIL_OFF_MAP};\n"
        "  let items = [...(D.sampleOff||[]), ...emailOff, ...userAdded];"
    )
    if old_filter in html and 'emailOff' not in html.split('filterOffMarket')[1].split('}')[0]:
        html = html.replace(old_filter, new_filter, 1)

    return html


def ensure_js_functions(html):
    """Add Proping + Email Off-Market JS if not present; replace if stale."""
    # Replace or insert Proping JS
    if 'function renderPropingTab(' in html:
        # Remove old block and re-insert fresh
        s = html.find('// ── Proping Tab ──')
        if s != -1:
            # Find a safe end marker (next top-level comment or function)
            e = html.find('\n// ──', s + 10)
            if e == -1:
                e = s + len(PROPING_JS) + 200
            html = html[:s] + PROPING_JS.strip() + '\n\n' + html[e:]
    else:
        # Insert before the last </script> before </body>
        body_pos = html.rfind('</body>')
        sc = html.rfind('</script>', 0, body_pos if body_pos != -1 else len(html))
        if sc != -1:
            html = html[:sc] + '\n' + PROPING_JS + '\n' + html[sc:]

    if 'function renderEmailOff(' not in html:
        body_pos = html.rfind('</body>')
        sc = html.rfind('</script>', 0, body_pos if body_pos != -1 else len(html))
        if sc != -1:
            html = html[:sc] + '\n' + EMAIL_OFFMKT_JS + '\n' + html[sc:]

    return html


def patch_init(html):
    """Add render calls to the page init function."""
    changes = [
        ('renderProping()', 'renderPropingTab();\n  renderPropingSnapshot();'),
        ('renderEmailOffMarkets()', 'renderEmailOff();'),
    ]
    # Remove old calls first
    for old, _ in changes:
        html = html.replace(old + ';', '').replace(old, '')

    # Find the init block and append new calls
    m = re.search(r'(renderClients\(\);[^\n]*\n)', html)
    if m:
        insert_after = m.end()
        new_calls = '  renderPropingTab();\n  renderPropingSnapshot();\n  renderEmailOff();\n'
        if 'renderPropingTab()' not in html:
            html = html[:insert_after] + new_calls + html[insert_after:]
    return html


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Dashboard Injector")
    print(f"Date: {datetime.today().strftime('%A %d %B %Y')}")
    print("=" * 60)

    if not DASHBOARD.exists():
        print(f"ERROR: Dashboard not found at {DASHBOARD}")
        return

    history = load_json(HISTORY_FILE, [])
    offmkts = load_json(OFFMKT_JSON, [])

    print(f"Proping history: {len(history)} day(s)")
    total_changes = sum(len(d.get('price_changes',[])) for d in history)
    total_new     = sum(len(d.get('newly_listed',[]))  for d in history)
    total_sold    = sum(len(d.get('sold',[]))           for d in history)
    print(f"  {total_changes} price changes, {total_new} new listings, {total_sold} sold (7-day total)")
    print(f"Email off-markets: {len(offmkts)} properties")

    html = DASHBOARD.read_text(encoding='utf-8')
    orig_size = len(html)

    # 1. Inject JS data
    proping_js_block = (
        f"{M_PROPING_DATA[0]}\n"
        f"const propingHistory = {json.dumps(history, indent=2)};\n"
        f"{M_PROPING_DATA[1]}"
    )
    offmkt_js_block = (
        f"{M_OFFMKT_EMAIL[0]}\n"
        f"const emailOffMarkets = {json.dumps(offmkts, indent=2)};\n"
        f"{M_OFFMKT_EMAIL[1]}"
    )
    html = inject_or_replace(html, *M_PROPING_DATA, proping_js_block)
    html = inject_or_replace(html, *M_OFFMKT_EMAIL, offmkt_js_block)

    # 2. CSS
    html = ensure_css(html, PROPING_CSS, 'p-suburb-block')

    # 3. Nav button
    html = ensure_nav_button(html)

    # 4. Proping page tab
    html = ensure_proping_page(html)

    # 5. Dashboard snapshot widget
    html = ensure_snapshot_widget(html)

    # 6. Email off-markets in Off Market tab
    html = ensure_email_offmkt_in_offmarket_tab(html)

    # 7. JS render functions
    html = ensure_js_functions(html)

    # 8. Init calls
    html = patch_init(html)

    DASHBOARD.write_text(html, encoding='utf-8')
    print(f"\nDashboard: {orig_size:,} → {len(html):,} bytes")
    print(f"Saved → {DASHBOARD}")


if __name__ == '__main__':
    main()
