#!/usr/bin/env python3
"""
build_app.py — Assembles the Mazar Martin Property Intelligence dashboard.
Reads the data blob from the existing app and wraps it in a fresh UI.
"""
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
OLD_APP = BASE / 'mazar_martin_app.html'
NEW_APP = BASE / 'mazar_martin_app.html'

# ── Extract data sections from existing app ──────────────────────────────────
html = OLD_APP.read_text(encoding='utf-8')
lines = html.split('\n')

# const D = {...};
d_line = lines[804]

# const PROPING_HISTORY = [...];
proping_line = lines[805]

# SUBURB_COORDS
coords_lines = []
in_coords = False
for i in range(807, 850):
    if i < len(lines):
        if 'const SUBURB_COORDS' in lines[i]:
            in_coords = True
        if in_coords:
            coords_lines.append(lines[i])
            if lines[i].strip().endswith('};'):
                break
coords_block = '\n'.join(coords_lines)

# Proping injection block
proping_block = []
in_block = False
for line in lines:
    if '__PROPING_HIST_START__' in line:
        in_block = True
    if in_block:
        proping_block.append(line)
    if '__PROPING_HIST_END__' in line and in_block:
        break
proping_inject = '\n'.join(proping_block)

# Offmarket email injection block
offmkt_block = []
in_block = False
for line in lines:
    if '__OFFMKT_EMAIL_START__' in line:
        in_block = True
    if in_block:
        offmkt_block.append(line)
    if '__OFFMKT_EMAIL_END__' in line and in_block:
        break
offmkt_inject = '\n'.join(offmkt_block)

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = r"""
* { margin:0; padding:0; box-sizing:border-box; }

:root {
  --green: #1C3A2A;
  --green-light: #2D5A40;
  --gold: #C9A84C;
  --gold-pale: #FBF7EE;
  --bg: #F5F0E8;
  --white: #FFFFFF;
  --border: #E0D5C0;
  --border-light: #F0EBE0;
  --text: #2C2C2C;
  --text-mid: #6B6258;
  --text-light: #8A8070;
  --red: #C62828;
  --red-bg: #FFEBEE;
  --green-bg: #E8F5E9;
  --blue-bg: #E3F2FD;
  --amber-bg: #FFF8E1;
  --purple-bg: #F3E5F5;
  --ff-serif: 'Cormorant Garamond', Georgia, serif;
  --ff-ui: 'Montserrat', -apple-system, sans-serif;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  --radius: 8px;
}

body { font-family: var(--ff-ui); background: var(--bg); color: var(--text); line-height: 1.5; }

/* ── Header ──────────────────────────────────────────────────────────────── */
header {
  background: var(--green); color: var(--white);
  padding: 14px 24px; display: flex; align-items: center; gap: 20px;
  position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
header h1 { font-family: var(--ff-serif); font-size: 26px; font-weight: 600; white-space: nowrap; }
.header-search { flex:1; max-width: 500px; position: relative; }
.header-search input {
  width:100%; padding: 8px 14px 8px 36px; border: 1px solid rgba(255,255,255,.2);
  border-radius: 6px; background: rgba(255,255,255,.12); color: var(--white);
  font-size: 13px; transition: all .2s;
}
.header-search input::placeholder { color: rgba(255,255,255,.5); }
.header-search input:focus { background: rgba(255,255,255,.2); border-color: var(--gold); outline: none; }
.header-search::before {
  content: '🔍'; position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  font-size: 14px; pointer-events: none;
}
.search-dropdown {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  background: var(--white); border: 1px solid var(--border); border-radius: var(--radius);
  max-height: 420px; overflow-y: auto; z-index: 1000; display: none;
  box-shadow: 0 8px 24px rgba(0,0,0,.15);
}
.search-dropdown.active { display: block; }
.search-group { padding: 6px 0; border-bottom: 1px solid var(--border-light); }
.search-group:last-child { border-bottom: none; }
.search-group-title {
  padding: 4px 14px; font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .5px; color: var(--text-light); background: var(--gold-pale);
}
.search-item {
  padding: 8px 14px; cursor: pointer; font-size: 13px;
  border-left: 3px solid transparent; transition: all .15s;
}
.search-item:hover { background: var(--gold-pale); border-left-color: var(--gold); }
.g-hl { background: #FFEB3B; font-weight: 600; border-radius: 2px; padding: 0 1px; }
.search-price { color: var(--gold); font-weight: 600; font-size: 12px; }
.search-suburb { color: var(--text-light); font-size: 12px; }
.header-date { font-size: 11px; color: rgba(255,255,255,.6); white-space: nowrap; }

/* ── Tab Bar ─────────────────────────────────────────────────────────────── */
.tab-bar {
  background: var(--white); border-bottom: 2px solid var(--border);
  display: flex; overflow-x: auto; gap: 0;
  position: sticky; top: 56px; z-index: 90;
  scrollbar-width: thin;
}
.tab-btn {
  padding: 11px 18px; background: none; border: none; cursor: pointer;
  font-size: 13px; font-weight: 500; color: var(--text-light);
  border-bottom: 3px solid transparent; white-space: nowrap; transition: all .2s;
  font-family: var(--ff-ui);
}
.tab-btn.active { color: var(--text); border-bottom-color: var(--gold); font-weight: 600; }
.tab-btn:hover { background: var(--gold-pale); color: var(--text); }
.tab-btn .tab-count {
  display: inline-block; background: var(--border); color: var(--text-mid);
  padding: 1px 6px; border-radius: 10px; font-size: 10px; margin-left: 4px; font-weight: 700;
}
.tab-btn.active .tab-count { background: var(--gold); color: var(--text); }

/* ── Main Content ────────────────────────────────────────────────────────── */
main { padding: 20px 24px; max-width: 1440px; margin: 0 auto; }
.page { display: none; }
.page.active { display: block; }
.page-title {
  font-family: var(--ff-serif); font-size: 22px; font-weight: 600;
  color: var(--green); margin-bottom: 4px;
}
.page-sub { font-size: 12px; color: var(--text-light); margin-bottom: 20px; }

/* ── Cards & KPIs ────────────────────────────────────────────────────────── */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.kpi-card {
  background: var(--white); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 20px; text-align: center; box-shadow: var(--shadow); transition: transform .2s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.1); }
.kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: var(--text-light); font-weight: 600; margin-bottom: 6px; }
.kpi-value { font-size: 36px; font-weight: 700; color: var(--green); line-height: 1; }
.kpi-bar { height: 5px; background: var(--border-light); border-radius: 3px; margin-top: 10px; overflow: hidden; }
.kpi-fill { height: 100%; background: var(--gold); border-radius: 3px; transition: width .6s ease; }
.kpi-detail { font-size: 11px; color: var(--text-mid); margin-top: 6px; }

/* ── Card Grid ───────────────────────────────────────────────────────────── */
.card { background: var(--white); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); }
.card-title { font-family: var(--ff-serif); font-size: 17px; font-weight: 600; color: var(--green); margin-bottom: 12px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }

/* ── Tables ──────────────────────────────────────────────────────────────── */
.table-wrap { background: var(--white); border: 1px solid var(--border); border-radius: var(--radius); overflow-x: auto; box-shadow: var(--shadow); }
table { width: 100%; font-size: 13px; border-collapse: collapse; }
thead { background: var(--gold-pale); border-bottom: 2px solid var(--border); }
th { padding: 10px 12px; text-align: left; font-weight: 600; color: var(--text); font-size: 12px; white-space: nowrap; }
th.sortable { cursor: pointer; user-select: none; }
th.sortable:hover { color: var(--gold); }
th.sortable::after { content: ' ↕'; font-size: 10px; color: var(--text-light); }
td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); }
tbody tr:hover { background: var(--gold-pale); }
tbody tr.called { background: var(--green-bg); }
tbody tr.vm { background: var(--amber-bg); }

/* ── Filters ─────────────────────────────────────────────────────────────── */
.filter-bar {
  display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; align-items: end;
}
.filter-group { display: flex; flex-direction: column; }
.filter-group label { font-size: 11px; font-weight: 600; color: var(--text-light); margin-bottom: 3px; text-transform: uppercase; letter-spacing: .3px; }
.filter-group input, .filter-group select {
  padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: 12px; background: var(--white); color: var(--text); min-width: 140px;
}
.filter-group input:focus, .filter-group select:focus { border-color: var(--gold); outline: none; }

/* ── Badges ──────────────────────────────────────────────────────────────── */
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-red { background: var(--red-bg); color: var(--red); }
.badge-green { background: var(--green-bg); color: #2E7D32; }
.badge-blue { background: var(--blue-bg); color: #1565C0; }
.badge-amber { background: var(--amber-bg); color: #E65100; }
.badge-purple { background: var(--purple-bg); color: #6A1B9A; }
.badge-gray { background: #EEEEEE; color: var(--text-mid); }
.suburb-pill { background: var(--gold-pale); color: var(--text-mid); padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
button, .btn {
  padding: 8px 14px; background: var(--green); color: var(--white); border: none;
  border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
  font-family: var(--ff-ui); transition: all .2s;
}
button:hover, .btn:hover { background: var(--green-light); transform: translateY(-1px); }
.btn-gold { background: var(--gold); color: var(--text); }
.btn-gold:hover { background: #B8941D; }
.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text-mid); }
.btn-outline:hover { background: var(--gold-pale); border-color: var(--gold); color: var(--text); transform: none; }
.btn-danger { background: var(--red); }
.btn-danger:hover { background: #B71C1C; }

/* ── Pagination ──────────────────────────────────────────────────────────── */
.pagination { display: flex; justify-content: center; gap: 4px; margin-top: 16px; flex-wrap: wrap; }
.pagination button { padding: 5px 10px; font-size: 11px; min-width: 34px; border-radius: 4px; }
.pagination button.active { background: var(--gold); color: var(--text); }
.pg-info { text-align: center; font-size: 11px; color: var(--text-light); margin-top: 6px; }

/* ── Forms ────────────────────────────────────────────────────────────────── */
.inline-form {
  background: var(--gold-pale); padding: 16px; border-radius: var(--radius);
  margin-bottom: 16px; border: 1px solid var(--border); display: none;
}
.inline-form.active { display: block; }
.form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 12px; }
.form-group { display: flex; flex-direction: column; }
.form-group label { font-size: 11px; font-weight: 600; color: var(--text); margin-bottom: 3px; }
.form-group input, .form-group textarea, .form-group select {
  padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px;
  font-size: 12px; background: var(--white); color: var(--text); font-family: var(--ff-ui);
}
.form-group textarea { resize: vertical; min-height: 50px; }

/* ── Agent Comments ──────────────────────────────────────────────────────── */
.agent-comment {
  width: 100%; padding: 5px 8px; border: 1px solid var(--border-light); border-radius: 4px;
  font-family: var(--ff-ui); font-size: 11px; resize: none; height: 32px; transition: border-color .2s;
}
.agent-comment:focus { border-color: var(--gold); outline: none; height: 60px; }
.checkbox { cursor: pointer; accent-color: var(--gold); width: 16px; height: 16px; }

/* ── Toast ────────────────────────────────────────────────────────────────── */
.toast {
  position: fixed; bottom: 24px; right: 24px; background: var(--green); color: var(--white);
  padding: 12px 20px; border-radius: var(--radius); z-index: 2000;
  box-shadow: 0 4px 16px rgba(0,0,0,.2); font-size: 13px; font-weight: 500;
  animation: slideIn .3s ease;
}
@keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

/* ── Map ─────────────────────────────────────────────────────────────────── */
.map-container {
  height: 450px; border: 1px solid var(--border); border-radius: var(--radius);
  margin-top: 16px; display: none; overflow: hidden;
}
.map-container.active { display: block; }

/* ── Section Tabs ────────────────────────────────────────────────────────── */
.section-tabs { display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 16px; }
.section-tab {
  padding: 10px 16px; background: none; border: none; cursor: pointer;
  font-size: 13px; font-weight: 500; color: var(--text-light);
  border-bottom: 3px solid transparent; font-family: var(--ff-ui);
}
.section-tab.active { color: var(--text); border-bottom-color: var(--gold); }
.section-tab:hover { background: var(--gold-pale); }
.section-content { display: none; }
.section-content.active { display: block; }

/* ── Proping Tab ─────────────────────────────────────────────────────────── */
.p-suburb-block { margin-bottom: 20px; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border); box-shadow: var(--shadow); }
.p-suburb-hdr {
  background: var(--green); color: var(--white);
  padding: 10px 16px; font-size: 12px; font-weight: 700; letter-spacing: .5px;
  text-transform: uppercase; display: flex; align-items: center; gap: 10px;
}
.p-suburb-counts { display: flex; gap: 6px; margin-left: auto; }
.p-cnt { border-radius: 10px; padding: 2px 10px; font-size: 10px; font-weight: 700; }
.p-cnt-change { background: var(--red-bg); color: var(--red); }
.p-cnt-new { background: var(--green-bg); color: #2E7D32; }
.p-cnt-sold { background: var(--blue-bg); color: #1565C0; }
.p-section-label {
  font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
  padding: 6px 14px; background: #fafaf8; border-bottom: 1px solid var(--border-light); color: var(--text-mid);
}
.p-row {
  display: flex; align-items: baseline; gap: 10px; padding: 8px 14px;
  border-bottom: 1px solid var(--border-light); font-size: 12px;
}
.p-row:last-child { border-bottom: none; }
.p-addr { font-weight: 700; color: var(--green); }
.p-addr a { color: var(--green); text-decoration: none; }
.p-addr a:hover { text-decoration: underline; }
.p-price { font-weight: 700; color: var(--text); }
.p-change-neg { color: var(--red); font-weight: 700; }
.p-change-pos { color: #2E7D32; font-weight: 700; }
.p-agent { color: var(--text-light); font-size: 11px; margin-left: auto; }
.p-date-chip { font-size: 9px; background: var(--gold-pale); color: var(--text-light); border-radius: 8px; padding: 1px 6px; }
.p-beds { color: var(--text-mid); font-size: 11px; }

/* ── Proping Snapshot Widget ─────────────────────────────────────────────── */
.proping-snap { background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); padding: 20px; margin-bottom: 20px; box-shadow: var(--shadow); }
.proping-snap-title { font-family: var(--ff-serif); font-size: 18px; color: var(--green); margin-bottom: 12px; border-bottom: 1px solid var(--border-light); padding-bottom: 8px; }
.snap-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-light); font-size: 12px; }
.snap-row:last-child { border-bottom: none; }
.snap-suburb { font-weight: 700; color: var(--green); }
.snap-pills { display: flex; gap: 6px; }
.email-src-badge { background: var(--blue-bg); color: #1565C0; border-radius: 10px; padding: 1px 8px; font-size: 9px; font-weight: 700; }

/* ── Chart ────────────────────────────────────────────────────────────────── */
.chart-container { position: relative; height: 280px; margin-bottom: 20px; }

/* ── Empty State ─────────────────────────────────────────────────────────── */
.empty-state { text-align: center; padding: 48px 24px; color: var(--text-light); font-size: 14px; }
.empty-state .icon { font-size: 48px; margin-bottom: 12px; }

/* ── Match Row ───────────────────────────────────────────────────────────── */
.match-count { display: inline-block; background: var(--green); color: var(--white); padding: 1px 7px; border-radius: 10px; font-size: 10px; font-weight: 700; margin-left: 4px; }
.expanded-matches { display: none; }
.expanded-matches.active { display: block; }
.match-card { background: var(--gold-pale); padding: 10px 14px; border-radius: 6px; margin: 6px 0; display: flex; justify-content: space-between; align-items: center; font-size: 12px; }

/* ── Editable Input ──────────────────────────────────────────────────────── */
.editable-input { padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; width: 90px; font-size: 12px; font-family: var(--ff-ui); }
.editable-input:focus { border-color: var(--gold); outline: none; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .filter-bar { flex-direction: column; }
  header { padding: 12px 16px; flex-wrap: wrap; }
  header h1 { font-size: 20px; }
  .header-search { max-width: 100%; order: 3; }
  main { padding: 12px; }
  table { min-width: 800px; }
}
@media (max-width: 480px) {
  .kpi-grid { grid-template-columns: 1fr; }
  .tab-btn { padding: 10px 12px; font-size: 12px; }
}
"""

# ── HTML Shell ───────────────────────────────────────────────────────────────
HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mazar Martin — Property Intelligence</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>"""

HTML_MID = """  </style>
</head>
<body>

<header>
  <h1>Mazar Martin</h1>
  <div class="header-search">
    <input type="text" id="globalSearch" placeholder="Search properties, agents, clients..." autocomplete="off">
    <div class="search-dropdown" id="searchDropdown"></div>
  </div>
  <div class="header-date" id="headerDate"></div>
</header>

<div id="tab-bar" class="tab-bar"></div>

<main id="main-content">
</main>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
"""

# ── JavaScript ───────────────────────────────────────────────────────────────
JS = r"""
// ═══════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════
const PER_PAGE = 30;
const _leafletMaps = {};
const today = new Date();
document.getElementById('headerDate').textContent = today.toLocaleDateString('en-AU',{weekday:'long',day:'numeric',month:'long',year:'numeric'});

function getWeekKey() {
  const d = new Date(); d.setDate(d.getDate() - d.getDay());
  return d.toISOString().slice(0,10);
}

function domainUrl(address, suburb, type) {
  function slugify(s) { return (s||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,''); }
  const s = slugify(suburb);
  const a = slugify(address.replace(/,.*$/,''));
  const t = type === 'sold' ? 'sold-listings' : 'sale';
  return `https://www.domain.com.au/${a}-${s}-nsw-2060`;
}

function getSuburbCoords(suburb) {
  const key = (suburb||'').toLowerCase().trim();
  return SUBURB_COORDS[key] || [-33.8388, 151.2093];
}

function jitterCoord(c) { return [c[0]+(Math.random()-.5)*.005, c[1]+(Math.random()-.5)*.005]; }

function showPropertyMap(containerId, items, getLabel, getPrice, getSuburb) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.classList.add('active');
  if (_leafletMaps[containerId]) { _leafletMaps[containerId].invalidateSize(); return; }
  const map = L.map(containerId).setView([-33.83, 151.22], 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
  _leafletMaps[containerId] = map;
  items.forEach(item => {
    const c = jitterCoord(getSuburbCoords(getSuburb(item)));
    L.marker(c).addTo(map).bindPopup(`<b>${getLabel(item)}</b><br>${getPrice(item)}<br><small>${getSuburb(item)}</small>`);
  });
  setTimeout(() => map.invalidateSize(), 200);
}

function showToast(msg) {
  const d = document.createElement('div'); d.className = 'toast'; d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3500);
}

function hl(text, q) {
  if (!q || !text) return text || '';
  const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi');
  return String(text).replace(re, '<span class="g-hl">$1</span>');
}

function fmtPrice(p) {
  if (!p) return '—';
  const s = String(p).trim();
  if (s.startsWith('$')) return s;
  const n = parseFloat(s.replace(/[^0-9.]/g,''));
  if (isNaN(n)) return s;
  return '$' + n.toLocaleString('en-AU');
}

function parsePrice(s) {
  if (!s) return 0;
  const nums = String(s).match(/[\d,]+/g);
  if (!nums) return 0;
  for (const n of nums) { const v = parseFloat(n.replace(/,/g,'')); if (v > 50000) return v; }
  return 0;
}

// ── localStorage helpers ────────────────────────────────────────────────────
function lsGet(key, def) { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : def; } catch { return def; } }
function lsSet(key, val) { localStorage.setItem(key, JSON.stringify(val)); }

// Weekly reset of call status
(function() {
  const wk = getWeekKey();
  if (localStorage.getItem('mmWeek') !== wk) {
    localStorage.setItem('mmWeek', wk);
    localStorage.removeItem('mmCallStatus');
  }
})();

// ═══════════════════════════════════════════════════════════════════════════════
// GLOBAL SEARCH
// ═══════════════════════════════════════════════════════════════════════════════
function closeSearch() { document.getElementById('searchDropdown').classList.remove('active'); }

document.addEventListener('click', e => {
  if (!e.target.closest('.header-search')) closeSearch();
});

function renderSearch(q) {
  const dd = document.getElementById('searchDropdown');
  if (!q || q.length < 2) { dd.classList.remove('active'); dd.innerHTML = ''; return; }
  q = q.toLowerCase();
  let html = '';
  const max = 6;

  // For Sale
  const fs = (D.sampleListings||[]).filter(l =>
    (l.address||'').toLowerCase().includes(q) || (l.suburb||'').toLowerCase().includes(q)
  ).slice(0, max);
  if (fs.length) {
    html += '<div class="search-group"><div class="search-group-title">For Sale</div>';
    fs.forEach(l => {
      html += `<div class="search-item" onclick="showTab('forsale');closeSearch()">
        <div>${hl(l.address, q)}</div>
        <div class="search-price">${l.price||'—'}</div>
        <div class="search-suburb">${hl(l.suburb, q)} · ${l.beds||'?'}bd</div>
      </div>`;
    });
    html += '</div>';
  }

  // Off Market
  const om = (D.sampleOff||[]).filter(l =>
    (l.address||'').toLowerCase().includes(q) || (l.suburb||'').toLowerCase().includes(q)
  ).slice(0, max);
  if (om.length) {
    html += '<div class="search-group"><div class="search-group-title">Off Market</div>';
    om.forEach(l => {
      html += `<div class="search-item" onclick="showTab('offmarket');closeSearch()">
        <div>${hl(l.address||l.agent||'', q)}</div>
        <div class="search-price">${l.price||'—'}</div>
        <div class="search-suburb">${hl(l.suburb, q)}</div>
      </div>`;
    });
    html += '</div>';
  }

  // Sold
  const sold = (D.soldListings||[]).filter(l =>
    (l.address||'').toLowerCase().includes(q) || (l.suburb||'').toLowerCase().includes(q)
  ).slice(0, max);
  if (sold.length) {
    html += '<div class="search-group"><div class="search-group-title">Sold</div>';
    sold.forEach(l => {
      html += `<div class="search-item" onclick="showTab('sold');closeSearch()">
        <div>${hl(l.address, q)}</div>
        <div class="search-price">${l.price||'—'}</div>
        <div class="search-suburb">${hl(l.suburb, q)} · ${l.method||''}</div>
      </div>`;
    });
    html += '</div>';
  }

  // Agents
  const ag = (D.allAgents||[]).filter(a =>
    (a.name||'').toLowerCase().includes(q) || (a.agency||'').toLowerCase().includes(q)
  ).slice(0, max);
  if (ag.length) {
    html += '<div class="search-group"><div class="search-group-title">Agents</div>';
    ag.forEach(a => {
      html += `<div class="search-item" onclick="showTab('allagents');closeSearch()">
        <div>${hl(a.name, q)}</div>
        <div class="search-suburb">${hl(a.agency, q)} · ${a.suburb||''}</div>
      </div>`;
    });
    html += '</div>';
  }

  if (!html) html = '<div class="search-item" style="color:var(--text-light)">No results found</div>';
  dd.innerHTML = html;
  dd.classList.add('active');
}

document.getElementById('globalSearch').addEventListener('input', e => renderSearch(e.target.value));

// ═══════════════════════════════════════════════════════════════════════════════
// TAB NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════
const TABS = [
  {id:'dashboard',     label:'Dashboard'},
  {id:'clients',       label:'Clients',       count: ()=>(D.xlsxClients||[]).length},
  {id:'forsale',       label:'For Sale',       count: ()=>D.listingsCount||0},
  {id:'offmarket',     label:'Off Market',     count: ()=>D.offmarketCount||0},
  {id:'matching',      label:'Buyer Matching'},
  {id:'sold',          label:'Sold',           count: ()=>D.soldCount||0},
  {id:'topperformers', label:'Top Performers'},
  {id:'allagents',     label:'All Agents',     count: ()=>D.agentsCount||0},
  {id:'proping',       label:'Proping'},
  {id:'mazarmartin',   label:'Report'},
];

const TAB_PAGES = {
  dashboard: buildDashboard,
  clients: buildClientsTab,
  forsale: buildForSaleTab,
  offmarket: buildOffMarketTab,
  matching: buildBuyerMatchingTab,
  sold: buildSoldTab,
  topperformers: buildTopPerformersTab,
  allagents: buildAllAgentsTab,
  proping: buildPropingTab,
  mazarmartin: buildMazarMartinTab,
};

function showTab(id, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const page = document.getElementById('page-' + id);
  if (page) page.classList.add('active');
  if (el) el.classList.add('active');
  else document.querySelector(`[data-tab="${id}"]`)?.classList.add('active');
  if (TAB_PAGES[id]) TAB_PAGES[id]();
  closeSearch();
}

function buildTabBar() {
  const bar = document.getElementById('tab-bar');
  bar.innerHTML = TABS.map((t, i) => {
    const cnt = t.count ? `<span class="tab-count">${t.count()}</span>` : '';
    return `<button class="tab-btn${i===0?' active':''}" data-tab="${t.id}" onclick="showTab('${t.id}', this)">${t.label}${cnt}</button>`;
  }).join('');
}

function buildPages() {
  const main = document.getElementById('main-content');
  main.innerHTML = TABS.map((t, i) =>
    `<div class="page${i===0?' active':''}" id="page-${t.id}"></div>`
  ).join('');
}

// ═══════════════════════════════════════════════════════════════════════════════
// PAGINATION HELPER
// ═══════════════════════════════════════════════════════════════════════════════
function paginateTable(tableBodyId, pagingId, items, renderRow, perPage) {
  perPage = perPage || PER_PAGE;
  const pgKey = 'page_' + tableBodyId;
  let pg = parseInt(localStorage.getItem(pgKey) || '0');
  const totalPages = Math.ceil(items.length / perPage);
  if (pg >= totalPages) pg = Math.max(0, totalPages - 1);
  localStorage.setItem(pgKey, pg);

  const start = pg * perPage;
  const slice = items.slice(start, start + perPage);
  const tbody = document.getElementById(tableBodyId);
  if (tbody) tbody.innerHTML = slice.map(renderRow).join('');

  const pagDiv = document.getElementById(pagingId);
  if (pagDiv && totalPages > 1) {
    let html = '';
    if (pg > 0) html += `<button onclick="goPage('${tableBodyId}','${pagingId}',${pg-1})" class="btn-sm btn-outline">‹</button>`;
    const range = 3;
    let lo = Math.max(0, pg-range), hi = Math.min(totalPages-1, pg+range);
    if (lo > 0) html += `<button onclick="goPage('${tableBodyId}','${pagingId}',0)" class="btn-sm btn-outline">1</button><span style="padding:0 4px;color:var(--text-light)">…</span>`;
    for (let i = lo; i <= hi; i++) {
      html += `<button onclick="goPage('${tableBodyId}','${pagingId}',${i})" class="btn-sm ${i===pg?'active':'btn-outline'}">${i+1}</button>`;
    }
    if (hi < totalPages-1) html += `<span style="padding:0 4px;color:var(--text-light)">…</span><button onclick="goPage('${tableBodyId}','${pagingId}',${totalPages-1})" class="btn-sm btn-outline">${totalPages}</button>`;
    if (pg < totalPages-1) html += `<button onclick="goPage('${tableBodyId}','${pagingId}',${pg+1})" class="btn-sm btn-outline">›</button>`;
    pagDiv.innerHTML = html;
    pagDiv.innerHTML += `<div class="pg-info">Showing ${start+1}–${Math.min(start+perPage, items.length)} of ${items.length}</div>`;
  } else if (pagDiv) {
    pagDiv.innerHTML = items.length ? `<div class="pg-info">${items.length} results</div>` : '';
  }
}

// Global page change handler
window.goPage = function(tbId, pgId, pg) {
  localStorage.setItem('page_' + tbId, pg);
  // Re-render the current tab
  const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab;
  if (activeTab && TAB_PAGES[activeTab]) TAB_PAGES[activeTab]();
};

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════════════
function buildDashboard() {
  const el = document.getElementById('page-dashboard');
  const callStatus = lsGet('mmCallStatus', {});
  const totalAgents = (D.allAgents||[]).length;
  const called = Object.values(callStatus).filter(v => v.called).length;
  const vmed = Object.values(callStatus).filter(v => v.vm).length;
  const pct = totalAgents ? Math.round((called+vmed)/totalAgents*100) : 0;

  let html = `
    <div class="page-title">Dashboard</div>
    <div class="page-sub">Lower North Shore Property Intelligence · Updated ${today.toLocaleDateString('en-AU')}</div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">For Sale</div>
        <div class="kpi-value">${D.listingsCount||0}</div>
        <div class="kpi-detail">Active listings</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Off Market</div>
        <div class="kpi-value">${D.offmarketCount||0}</div>
        <div class="kpi-detail">Not on Domain/REA</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Recent Sales</div>
        <div class="kpi-value">${D.soldCount||0}</div>
        <div class="kpi-detail">Last ~3 months</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Agents Contacted</div>
        <div class="kpi-value">${called+vmed} <span style="font-size:16px;color:var(--text-light)">/ ${totalAgents}</span></div>
        <div class="kpi-bar"><div class="kpi-fill" style="width:${pct}%"></div></div>
        <div class="kpi-detail">${called} called · ${vmed} VM · ${pct}% reached</div>
      </div>
    </div>`;

  // Proping Snapshot Widget
  if (typeof propingHistory !== 'undefined' && propingHistory.length) {
    const seen = new Set();
    const subMap = {};
    for (const day of propingHistory) {
      for (const section of ['price_changes','newly_listed','sold']) {
        for (const p of (day[section]||[])) {
          const addr = (p.address||'').toLowerCase();
          if (!addr || seen.has(addr)) continue;
          seen.add(addr);
          const suburb = (p.suburb||'Unknown').trim()||'Unknown';
          if (!subMap[suburb]) subMap[suburb] = {c:0,n:0,s:0};
          if (section==='price_changes') subMap[suburb].c++;
          if (section==='newly_listed') subMap[suburb].n++;
          if (section==='sold') subMap[suburb].s++;
        }
      }
    }
    const suburbs = Object.keys(subMap).sort();
    if (suburbs.length) {
      const dates = propingHistory.map(e=>e.date).filter(Boolean);
      const range = dates.length>1?`${dates[dates.length-1]} – ${dates[0]}`:(dates[0]||'');
      html += `<div class="proping-snap"><div class="proping-snap-title">Proping Weekly Snapshot <span style="font-size:12px;color:var(--text-light);font-family:var(--ff-ui)">${range}</span></div>`;
      suburbs.forEach(s => {
        const d = subMap[s];
        html += `<div class="snap-row"><span class="snap-suburb">${s}</span><span class="snap-pills">
          ${d.c?`<span class="p-cnt p-cnt-change">↓ ${d.c}</span>`:''}
          ${d.n?`<span class="p-cnt p-cnt-new">+ ${d.n}</span>`:''}
          ${d.s?`<span class="p-cnt p-cnt-sold">✓ ${d.s}</span>`:''}
        </span></div>`;
      });
      html += `<div style="text-align:right;margin-top:8px"><button class="btn-sm btn-gold" onclick="showTab('proping')">View full report →</button></div></div>`;
    }
  }

  // Week/Month Stats
  html += '<div class="two-col">';
  // Week stats
  if (D.WEEK_HISTORY && D.WEEK_HISTORY.length) {
    html += `<div class="card"><div class="card-title">This Week</div><div id="weekStatsBody"></div>
      <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap" id="weekBtns"></div></div>`;
  }
  // Month stats
  if (D.MONTH_HISTORY && D.MONTH_HISTORY.length) {
    html += `<div class="card"><div class="card-title">This Month</div><div id="monthStatsBody"></div>
      <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap" id="monthBtns"></div></div>`;
  }
  html += '</div>';

  // Chart placeholder
  html += `<div class="card" style="margin-bottom:24px"><div class="card-title">Listings by Suburb</div><div class="chart-container"><canvas id="suburbChart"></canvas></div></div>`;

  el.innerHTML = html;

  // Render week/month stats
  if (D.WEEK_HISTORY && D.WEEK_HISTORY.length) {
    renderWeekStats(0);
    const btns = document.getElementById('weekBtns');
    if (btns) btns.innerHTML = D.WEEK_HISTORY.map((w,i) => `<button class="btn-sm ${i===0?'':'btn-outline'}" onclick="renderWeekStats(${i});this.parentNode.querySelectorAll('button').forEach(b=>b.className='btn-sm btn-outline');this.className='btn-sm'">${w.week}</button>`).join('');
  }
  if (D.MONTH_HISTORY && D.MONTH_HISTORY.length) {
    renderMonthStats(0);
    const btns = document.getElementById('monthBtns');
    if (btns) btns.innerHTML = D.MONTH_HISTORY.map((m,i) => `<button class="btn-sm ${i===0?'':'btn-outline'}" onclick="renderMonthStats(${i});this.parentNode.querySelectorAll('button').forEach(b=>b.className='btn-sm btn-outline');this.className='btn-sm'">${m.month}</button>`).join('');
  }

  // Suburb chart
  try {
    const suburbCounts = {};
    (D.sampleListings||[]).forEach(l => { suburbCounts[l.suburb] = (suburbCounts[l.suburb]||0)+1; });
    const labels = Object.keys(suburbCounts).sort((a,b) => suburbCounts[b]-suburbCounts[a]).slice(0,15);
    const data = labels.map(l => suburbCounts[l]);
    const ctx = document.getElementById('suburbChart');
    if (ctx) new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{label:'For Sale', data, backgroundColor:'#C9A84C', borderRadius: 4}] },
      options: { responsive: true, maintainAspectRatio: false, plugins: {legend:{display:false}}, scales: {y:{beginAtZero:true,grid:{color:'#F0EBE0'}},x:{grid:{display:false}}} }
    });
  } catch(e) {}
}

function renderWeekStats(idx) {
  const w = D.WEEK_HISTORY[idx]; if (!w) return;
  const body = document.getElementById('weekStatsBody');
  const sorted = [...(w.stats||[])].sort((a,b) => (b.new+b.sold)-(a.new+a.sold));
  body.innerHTML = `<table><thead><tr><th>Suburb</th><th style="text-align:center">New</th><th style="text-align:center">Sold</th></tr></thead><tbody>` +
    sorted.filter(s=>s.new||s.sold).map(s => `<tr><td>${s.suburb}</td><td style="text-align:center;color:#2E7D32;font-weight:600">${s.new||'—'}</td><td style="text-align:center;color:#1565C0;font-weight:600">${s.sold||'—'}</td></tr>`).join('') +
    '</tbody></table>';
}

function renderMonthStats(idx) {
  const m = D.MONTH_HISTORY[idx]; if (!m) return;
  const body = document.getElementById('monthStatsBody');
  const sorted = [...(m.stats||[])].sort((a,b) => (b.new+b.sold)-(a.new+a.sold));
  body.innerHTML = `<table><thead><tr><th>Suburb</th><th style="text-align:center">New</th><th style="text-align:center">Sold</th></tr></thead><tbody>` +
    sorted.filter(s=>s.new||s.sold).map(s => `<tr><td>${s.suburb}</td><td style="text-align:center;color:#2E7D32;font-weight:600">${s.new||'—'}</td><td style="text-align:center;color:#1565C0;font-weight:600">${s.sold||'—'}</td></tr>`).join('') +
    '</tbody></table>';
}

// ═══════════════════════════════════════════════════════════════════════════════
// CLIENTS TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildClientsTab() {
  const el = document.getElementById('page-clients');
  const edits = lsGet('mmClientEdits', {});
  const saved = lsGet('mmClients', []);

  el.innerHTML = `
    <div class="page-title">Clients</div>
    <div class="page-sub">Manage buyers, sellers, and your pipeline</div>
    <div class="section-tabs">
      <button class="section-tab active" onclick="switchClientSection(this,'buyers')">Active Buyers</button>
      <button class="section-tab" onclick="switchClientSection(this,'sellers')">Sellers</button>
      <button class="section-tab" onclick="switchClientSection(this,'pipeline')">Pipeline</button>
      <button class="section-tab" onclick="switchClientSection(this,'myclients')">My Clients</button>
    </div>
    <div class="section-content active" id="sec-buyers"></div>
    <div class="section-content" id="sec-sellers"></div>
    <div class="section-content" id="sec-pipeline"></div>
    <div class="section-content" id="sec-myclients"></div>`;

  buildActiveBuyersSection(edits);
  buildSellersSection(edits);
  buildPipelineSection(edits);
  buildMyClientsSection(saved);
}

function switchClientSection(btn, section) {
  document.querySelectorAll('#page-clients .section-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#page-clients .section-content').forEach(s => s.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('sec-' + section).classList.add('active');
}

function buildActiveBuyersSection(edits) {
  const buyers = (D.xlsxClients||[]).filter(c => (c.section||'').includes('Buyer'));
  const el = document.getElementById('sec-buyers');
  let html = `<div class="table-wrap"><table><thead><tr>
    <th>BA</th><th>Client</th><th>Budget</th><th>Locations</th><th>Spec</th><th>Matches</th><th></th>
  </tr></thead><tbody>`;
  buyers.forEach(c => {
    const e = edits[c.name] || {};
    const name = e.name || c.name;
    const matches = getClientMatches(c);
    html += `<tr>
      <td>${e.ba||c.ba||'—'}</td>
      <td style="font-weight:600">${name}</td>
      <td>${e.budget||c.budget||'—'}</td>
      <td><span class="suburb-pill">${e.locations||c.locations||'—'}</span></td>
      <td style="font-size:11px;max-width:200px">${e.spec||c.spec||'—'}</td>
      <td><span class="match-count" onclick="toggleMatchRow('${name}')" style="cursor:pointer">${matches.length}</span></td>
      <td><button class="btn-sm btn-outline" onclick="editClient(this,'${name}')">Edit</button></td>
    </tr>
    <tr class="expanded-matches" id="matches-${name.replace(/[^a-z0-9]/gi,'_')}"><td colspan="7" style="padding:0"></td></tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

function buildSellersSection(edits) {
  const sellers = (D.xlsxClients||[]).filter(c => (c.section||'').includes('Seller'));
  const el = document.getElementById('sec-sellers');
  let html = `<div class="table-wrap"><table><thead><tr><th>BA</th><th>Client</th><th>Referrer</th><th>Date</th><th></th></tr></thead><tbody>`;
  sellers.forEach(c => {
    const e = edits[c.name]||{};
    html += `<tr><td>${e.ba||c.ba||'—'}</td><td style="font-weight:600">${e.name||c.name}</td><td>${e.referrer||c.referrer||'—'}</td><td>${c.date||'—'}</td><td><button class="btn-sm btn-outline" onclick="editClient(this,'${c.name}')">Edit</button></td></tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

function buildPipelineSection(edits) {
  const pipeline = (D.xlsxClients||[]).filter(c => (c.section||'').includes('Pipeline'));
  const el = document.getElementById('sec-pipeline');
  let html = `<div class="table-wrap"><table><thead><tr><th>Client</th><th>Budget</th><th>Status</th><th></th></tr></thead><tbody>`;
  pipeline.forEach(c => {
    const e = edits[c.name]||{};
    html += `<tr><td style="font-weight:600">${e.name||c.name}</td><td>${e.budget||c.budget||'—'}</td><td><span class="badge badge-blue">${e.status||c.status||'Active'}</span></td><td><button class="btn-sm btn-outline" onclick="editClient(this,'${c.name}')">Edit</button></td></tr>`;
  });
  html += '</tbody></table></div>';
  el.innerHTML = html;
}

function buildMyClientsSection(saved) {
  const el = document.getElementById('sec-myclients');
  let html = `
    <button class="btn-sm btn-gold" onclick="document.getElementById('newClientForm').classList.toggle('active')" style="margin-bottom:12px">+ Add Client</button>
    <div class="inline-form" id="newClientForm">
      <div class="form-row">
        <div class="form-group"><label>Name</label><input id="nc-name"></div>
        <div class="form-group"><label>Type</label><select id="nc-type"><option>Buyer</option><option>Seller</option><option>Pipeline</option></select></div>
        <div class="form-group"><label>Budget</label><input id="nc-budget" placeholder="$2,000,000"></div>
        <div class="form-group"><label>Suburbs</label><input id="nc-suburbs" placeholder="Mosman, Cremorne"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Notes</label><input id="nc-notes"></div>
        <div class="form-group" style="justify-content:end"><button onclick="addNewClient()">Save Client</button></div>
      </div>
    </div>`;
  if (saved.length) {
    html += `<div class="table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>Budget</th><th>Suburbs</th><th>Notes</th><th></th></tr></thead><tbody>`;
    saved.forEach((c,i) => {
      html += `<tr><td style="font-weight:600">${c.name}</td><td><span class="badge badge-blue">${c.type}</span></td><td>${c.budget||'—'}</td><td>${c.suburbs||'—'}</td><td style="font-size:11px">${c.notes||''}</td><td><button class="btn-sm btn-danger" onclick="deleteMyClient(${i})">×</button></td></tr>`;
    });
    html += '</tbody></table></div>';
  }
  el.innerHTML = html;
}

function addNewClient() {
  const name = document.getElementById('nc-name').value.trim();
  if (!name) { showToast('Enter a name'); return; }
  const saved = lsGet('mmClients', []);
  saved.push({
    name,
    type: document.getElementById('nc-type').value,
    budget: document.getElementById('nc-budget').value,
    suburbs: document.getElementById('nc-suburbs').value,
    notes: document.getElementById('nc-notes').value,
  });
  lsSet('mmClients', saved);
  showToast('Client added');
  buildClientsTab();
}

function deleteMyClient(idx) {
  const saved = lsGet('mmClients', []);
  saved.splice(idx, 1);
  lsSet('mmClients', saved);
  buildClientsTab();
}

function editClient(btn, name) {
  const edits = lsGet('mmClientEdits', {});
  const e = edits[name] || {};
  const client = (D.xlsxClients||[]).find(c => c.name === name) || {};
  const id = name.replace(/[^a-z0-9]/gi, '_');

  // Toggle existing edit form
  const existing = document.getElementById('edit-' + id);
  if (existing) { existing.remove(); return; }

  const row = btn.closest('tr');
  const form = document.createElement('tr');
  form.id = 'edit-' + id;
  form.innerHTML = `<td colspan="7" style="background:var(--gold-pale);padding:12px">
    <div class="form-row">
      <div class="form-group"><label>Budget</label><input value="${e.budget||client.budget||''}" onchange="saveClientEdit('${name}','budget',this.value)"></div>
      <div class="form-group"><label>Locations</label><input value="${e.locations||client.locations||''}" onchange="saveClientEdit('${name}','locations',this.value)"></div>
      <div class="form-group"><label>Spec</label><input value="${e.spec||client.spec||''}" onchange="saveClientEdit('${name}','spec',this.value)"></div>
      <div class="form-group"><label>Notes</label><input value="${e.notes||client.notes||''}" onchange="saveClientEdit('${name}','notes',this.value)"></div>
    </div>
  </td>`;
  row.after(form);
}

function saveClientEdit(name, field, value) {
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name][field] = value;
  lsSet('mmClientEdits', edits);
  showToast('Saved');
}

// ── Client Matching Logic ─────────────────────────────────────────────────
function getClientMatches(client) {
  const dismissed = lsGet('mmDismissedProps', {})[client.name] || [];
  const savedMatches = (lsGet('mmSavedMatches', {})[client.name] || []).map(m => m.address);
  const locs = (client.locations||'').toLowerCase().split(/[,;]+/).map(s => s.trim()).filter(Boolean);
  if (!locs.length) return [];

  const all = [...(D.sampleListings||[]).map(l=>({...l,_src:'For Sale'})), ...(D.sampleOff||[]).map(l=>({...l,_src:'Off Market'}))];
  return all.filter(l => {
    const sub = (l.suburb||'').toLowerCase();
    const addr = (l.address||'').toLowerCase();
    if (dismissed.includes(addr) || savedMatches.includes(addr)) return false;
    return locs.some(loc => sub.includes(loc) || loc.includes(sub));
  });
}

function toggleMatchRow(clientName) {
  const id = 'matches-' + clientName.replace(/[^a-z0-9]/gi, '_');
  const row = document.getElementById(id);
  if (!row) return;
  if (row.classList.contains('active')) { row.classList.remove('active'); return; }
  row.classList.add('active');

  const client = (D.xlsxClients||[]).find(c => c.name === clientName) || {name:clientName,locations:''};
  const saved = (lsGet('mmSavedMatches', {})[clientName] || []);
  const matches = getClientMatches(client);

  let html = '<div style="padding:12px">';
  if (saved.length) {
    html += '<div style="font-weight:600;font-size:12px;margin-bottom:6px">Saved Matches:</div>';
    saved.forEach((m,i) => {
      html += `<div class="match-card"><span>${m.address} · ${m.suburb} · ${m.price||'—'}</span>
        <button class="btn-sm btn-danger" onclick="removeFromClient('${clientName}',${i})">Remove</button></div>`;
    });
  }
  if (matches.length) {
    html += `<div style="font-weight:600;font-size:12px;margin:8px 0 6px">Suggested (${matches.length}):</div>`;
    matches.slice(0,10).forEach(m => {
      html += `<div class="match-card">
        <span>${m.address||''} · ${m.suburb} · ${m.price||'—'} · <span class="badge badge-gray">${m._src}</span></span>
        <span>
          <button class="btn-sm btn-gold" onclick="saveMatchForClient('${clientName}','${(m.address||'').replace(/'/g,"\\'")}','${m.suburb}','${(m.price||'').replace(/'/g,"\\'")}','${m._src}','')">Save</button>
          <button class="btn-sm btn-outline" onclick="dismissMatch('${clientName}','${(m.address||'').toLowerCase().replace(/'/g,"\\'")}')">Skip</button>
        </span></div>`;
    });
  } else if (!saved.length) {
    html += '<div class="empty-state" style="padding:16px">No matching properties found for this client\'s location preferences.</div>';
  }
  html += '</div>';
  row.querySelector('td').innerHTML = html;
}

function saveMatchForClient(clientName, address, suburb, price, type, note) {
  const all = lsGet('mmSavedMatches', {});
  if (!all[clientName]) all[clientName] = [];
  all[clientName].push({address, suburb, price, type, note, savedAt: new Date().toISOString()});
  lsSet('mmSavedMatches', all);
  showToast('Match saved');
  toggleMatchRow(clientName); toggleMatchRow(clientName); // refresh
}

function removeFromClient(clientName, idx) {
  const all = lsGet('mmSavedMatches', {});
  if (all[clientName]) { all[clientName].splice(idx,1); lsSet('mmSavedMatches', all); }
  toggleMatchRow(clientName); toggleMatchRow(clientName);
}

function dismissMatch(clientName, address) {
  const all = lsGet('mmDismissedProps', {});
  if (!all[clientName]) all[clientName] = [];
  all[clientName].push(address);
  lsSet('mmDismissedProps', all);
  toggleMatchRow(clientName); toggleMatchRow(clientName);
}

// ═══════════════════════════════════════════════════════════════════════════════
// FOR SALE TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildForSaleTab() {
  const el = document.getElementById('page-forsale');
  const suburbs = [...new Set((D.sampleListings||[]).map(l=>l.suburb))].sort();
  const userAdded = lsGet('mmNewSale', []);
  const all = [...(D.sampleListings||[]), ...userAdded];

  el.innerHTML = `
    <div class="page-title">For Sale</div>
    <div class="page-sub">${all.length} active listings across the Lower North Shore</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Suburb</label><select id="fs-suburb" onchange="filterForSale()"><option value="">All Suburbs</option>${suburbs.map(s=>`<option>${s}</option>`).join('')}</select></div>
      <div class="filter-group"><label>Min Beds</label><select id="fs-beds" onchange="filterForSale()"><option value="">Any</option><option>2</option><option>3</option><option>4</option><option>5</option></select></div>
      <div class="filter-group"><label>Search</label><input id="fs-q" placeholder="Address or agent..." oninput="filterForSale()"></div>
      <div class="filter-group" style="justify-content:end"><button class="btn-sm btn-gold" onclick="document.getElementById('newSaleForm').classList.toggle('active')">+ Add Property</button></div>
    </div>
    <div class="inline-form" id="newSaleForm">
      <div class="form-row">
        <div class="form-group"><label>Address</label><input id="ns-addr"></div>
        <div class="form-group"><label>Suburb</label><input id="ns-sub"></div>
        <div class="form-group"><label>Price</label><input id="ns-price"></div>
        <div class="form-group"><label>Beds</label><input id="ns-beds" type="number"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Agency</label><input id="ns-agency"></div>
        <div class="form-group" style="justify-content:end"><button onclick="addNewSale()">Add Listing</button></div>
      </div>
    </div>
    <div class="table-wrap"><table><thead><tr>
      <th>Status</th><th>Address</th><th>Suburb</th><th>Type</th><th style="text-align:center">Beds</th><th style="text-align:center">Bath</th><th>Price</th><th>Agency</th><th>Agents</th><th>Link</th>
    </tr></thead><tbody id="fs-tbody"></tbody></table></div>
    <div class="pagination" id="fs-paging"></div>`;
  filterForSale();
}

function filterForSale() {
  const sub = document.getElementById('fs-suburb')?.value || '';
  const beds = parseInt(document.getElementById('fs-beds')?.value) || 0;
  const q = (document.getElementById('fs-q')?.value || '').toLowerCase();
  const userAdded = lsGet('mmNewSale', []);
  let items = [...(D.sampleListings||[]), ...userAdded];
  if (sub) items = items.filter(l => l.suburb === sub);
  if (beds) items = items.filter(l => parseInt(l.beds||0) >= beds);
  if (q) items = items.filter(l => (l.address||'').toLowerCase().includes(q) || (l.agentNames||'').toLowerCase().includes(q) || (l.agencyName||'').toLowerCase().includes(q));

  paginateTable('fs-tbody', 'fs-paging', items, l => {
    const tag = l.tagText || '';
    let badge = '';
    if (tag.toLowerCase().includes('price reduced') || tag.toLowerCase().includes('price drop')) badge = '<span class="badge badge-red">↓ Reduced</span>';
    else if (tag.toLowerCase() === 'new') badge = '<span class="badge badge-green">New</span>';
    else if (tag.toLowerCase() === 'updated') badge = '<span class="badge badge-amber">Updated</span>';
    else if (tag.toLowerCase().includes('under offer')) badge = '<span class="badge badge-purple">Under Offer</span>';
    else if (tag.toLowerCase().includes('auction')) badge = '<span class="badge badge-blue">Auction</span>';
    const url = l.url || domainUrl(l.address||'', l.suburb||'');
    return `<tr>
      <td>${badge}</td>
      <td style="font-weight:600">${l.address||'—'}</td>
      <td><span class="suburb-pill">${l.suburb||'—'}</span></td>
      <td>${l.propertyType||l.type||'—'}</td>
      <td style="text-align:center">${l.beds||'—'}</td>
      <td style="text-align:center">${l.baths||'—'}</td>
      <td style="font-weight:600;color:var(--green)">${l.price||'—'}</td>
      <td style="font-size:11px">${l.agencyName||l.agency||'—'}</td>
      <td style="font-size:11px">${l.agentNames||'—'}</td>
      <td>${url ? `<a href="${url}" target="_blank" class="badge badge-blue" style="text-decoration:none">Domain</a>` : ''}</td>
    </tr>`;
  });
}

function addNewSale() {
  const addr = document.getElementById('ns-addr').value.trim();
  if (!addr) { showToast('Enter address'); return; }
  const items = lsGet('mmNewSale', []);
  items.push({
    address: addr,
    suburb: document.getElementById('ns-sub').value.trim(),
    price: document.getElementById('ns-price').value.trim(),
    beds: document.getElementById('ns-beds').value,
    agencyName: document.getElementById('ns-agency').value.trim(),
    tagText: 'New',
    _user: true,
  });
  lsSet('mmNewSale', items);
  showToast('Listing added');
  buildForSaleTab();
}

// ═══════════════════════════════════════════════════════════════════════════════
// OFF MARKET TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildOffMarketTab() {
  const el = document.getElementById('page-offmarket');
  const suburbs = [...new Set((D.sampleOff||[]).map(l=>l.suburb))].sort();
  const userAdded = lsGet('mmNewOff', []);
  const all = [...(D.sampleOff||[]), ...userAdded];

  el.innerHTML = `
    <div class="page-title">Off Market</div>
    <div class="page-sub">${all.length} properties not listed on Domain or REA</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Suburb</label><select id="om-suburb" onchange="filterOffMarket()"><option value="">All Suburbs</option>${suburbs.map(s=>`<option>${s}</option>`).join('')}</select></div>
      <div class="filter-group"><label>Search</label><input id="om-q" placeholder="Address or agent..." oninput="filterOffMarket()"></div>
      <div class="filter-group" style="justify-content:end">
        <button class="btn-sm btn-outline" onclick="toggleMapOM()">Toggle Map</button>
        <button class="btn-sm btn-gold" onclick="document.getElementById('newOffForm').classList.toggle('active')">+ Add Property</button>
      </div>
    </div>
    <div class="inline-form" id="newOffForm">
      <div class="form-row">
        <div class="form-group"><label>Address</label><input id="no-addr"></div>
        <div class="form-group"><label>Suburb</label><input id="no-sub"></div>
        <div class="form-group"><label>Agent</label><input id="no-agent"></div>
        <div class="form-group"><label>Price</label><input id="no-price"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Comments</label><input id="no-comments"></div>
        <div class="form-group" style="justify-content:end"><button onclick="addNewOff()">Add Property</button></div>
      </div>
    </div>
    <div class="map-container" id="om-map"></div>
    <div class="table-wrap"><table><thead><tr>
      <th>Date</th><th>Agent</th><th>Address</th><th>Suburb</th><th>Price</th><th>Comments</th>
    </tr></thead><tbody id="om-tbody"></tbody></table></div>
    <div class="pagination" id="om-paging"></div>`;
  filterOffMarket();
}

function filterOffMarket() {
  const sub = document.getElementById('om-suburb')?.value || '';
  const q = (document.getElementById('om-q')?.value || '').toLowerCase();
  const userAdded = lsGet('mmNewOff', []);
  let items = [...(D.sampleOff||[]), ...userAdded];
  if (sub) items = items.filter(l => l.suburb === sub);
  if (q) items = items.filter(l => (l.address||'').toLowerCase().includes(q) || (l.agent||'').toLowerCase().includes(q) || (l.suburb||'').toLowerCase().includes(q));

  paginateTable('om-tbody', 'om-paging', items, l => `<tr>
    <td style="font-size:11px;color:var(--text-light)">${l.date||'—'}</td>
    <td>${l.agent||'—'}</td>
    <td style="font-weight:600">${l.address||'—'}</td>
    <td><span class="suburb-pill">${l.suburb||'—'}</span></td>
    <td style="font-weight:600">${l.price||'—'}</td>
    <td style="font-size:11px;max-width:200px">${l.comments||''}</td>
  </tr>`);
}

function toggleMapOM() {
  const el = document.getElementById('om-map');
  if (el.classList.contains('active')) { el.classList.remove('active'); return; }
  showPropertyMap('om-map', D.sampleOff||[], l=>l.address||l.agent||'', l=>l.price||'', l=>l.suburb||'');
}

function addNewOff() {
  const addr = document.getElementById('no-addr').value.trim();
  if (!addr) { showToast('Enter address'); return; }
  const items = lsGet('mmNewOff', []);
  items.push({
    date: today.toLocaleDateString('en-AU',{day:'2-digit',month:'short',year:'numeric'}),
    agent: document.getElementById('no-agent').value.trim(),
    address: addr,
    suburb: document.getElementById('no-sub').value.trim(),
    price: document.getElementById('no-price').value.trim(),
    comments: document.getElementById('no-comments').value.trim(),
    source: 'manual',
  });
  lsSet('mmNewOff', items);
  showToast('Property added');
  buildOffMarketTab();
}

// ═══════════════════════════════════════════════════════════════════════════════
// BUYER MATCHING TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildBuyerMatchingTab() {
  const el = document.getElementById('page-matching');
  const suburbs = [...new Set([...(D.sampleListings||[]).map(l=>l.suburb), ...(D.sampleOff||[]).map(l=>l.suburb)])].sort();

  el.innerHTML = `
    <div class="page-title">Buyer Matching</div>
    <div class="page-sub">Find properties matching specific buyer criteria</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Min Price</label><input id="bm-min" placeholder="$1,500,000" value=""></div>
      <div class="filter-group"><label>Max Price</label><input id="bm-max" placeholder="$3,000,000" value=""></div>
      <div class="filter-group"><label>Suburb</label><select id="bm-suburb"><option value="">All</option>${suburbs.map(s=>`<option>${s}</option>`).join('')}</select></div>
      <div class="filter-group"><label>Min Beds</label><select id="bm-beds"><option value="">Any</option><option>2</option><option>3</option><option>4</option><option>5</option></select></div>
      <div class="filter-group" style="justify-content:end"><button class="btn-gold" onclick="runBuyerMatch()">Search</button></div>
    </div>
    <div id="bm-results"></div>
    <div class="map-container" id="bm-map"></div>`;
}

function runBuyerMatch() {
  const minPrice = parsePrice(document.getElementById('bm-min').value);
  const maxPrice = parsePrice(document.getElementById('bm-max').value);
  const suburb = document.getElementById('bm-suburb').value;
  const minBeds = parseInt(document.getElementById('bm-beds').value) || 0;

  let items = [...(D.sampleListings||[]).map(l=>({...l,_src:'For Sale'})), ...(D.sampleOff||[]).map(l=>({...l,_src:'Off Market'}))];
  items = items.filter(l => {
    const p = parsePrice(l.price);
    if (minPrice && p && p < minPrice) return false;
    if (maxPrice && p && p > maxPrice) return false;
    if (suburb && l.suburb !== suburb) return false;
    if (minBeds && parseInt(l.beds||0) < minBeds) return false;
    return true;
  });

  const div = document.getElementById('bm-results');
  if (!items.length) { div.innerHTML = '<div class="empty-state"><div class="icon">🏠</div>No properties match your criteria</div>'; return; }

  div.innerHTML = `<div style="margin-bottom:8px;font-weight:600">${items.length} matching properties</div>
    <div class="table-wrap"><table><thead><tr><th>Source</th><th>Address</th><th>Suburb</th><th>Beds</th><th>Price</th><th>Agency</th></tr></thead><tbody>` +
    items.map(l => `<tr>
      <td><span class="badge ${l._src==='For Sale'?'badge-green':'badge-amber'}">${l._src}</span></td>
      <td style="font-weight:600">${l.address||'—'}</td>
      <td><span class="suburb-pill">${l.suburb||'—'}</span></td>
      <td style="text-align:center">${l.beds||'—'}</td>
      <td style="font-weight:600;color:var(--green)">${l.price||'—'}</td>
      <td style="font-size:11px">${l.agencyName||l.agency||'—'}</td>
    </tr>`).join('') + '</tbody></table></div>';

  showPropertyMap('bm-map', items, l=>l.address||'', l=>l.price||'', l=>l.suburb||'');
}

// ═══════════════════════════════════════════════════════════════════════════════
// SOLD TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildSoldTab() {
  const el = document.getElementById('page-sold');
  const suburbs = [...new Set((D.soldListings||[]).map(l=>l.suburb))].sort();

  el.innerHTML = `
    <div class="page-title">Sold Properties</div>
    <div class="page-sub">${(D.soldListings||[]).length} recent sales across the Lower North Shore</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Suburb</label><select id="sold-suburb" onchange="filterSold()"><option value="">All Suburbs</option>${suburbs.map(s=>`<option>${s}</option>`).join('')}</select></div>
      <div class="filter-group"><label>Method</label><select id="sold-method" onchange="filterSold()"><option value="">All Methods</option><option>Auction</option><option>Private Treaty</option><option>Prior to Auction</option></select></div>
      <div class="filter-group"><label>Search</label><input id="sold-q" placeholder="Address or agent..." oninput="filterSold()"></div>
    </div>
    <div class="table-wrap"><table><thead><tr>
      <th>Date</th><th>Method</th><th>Address</th><th>Suburb</th><th style="text-align:center">Beds</th><th>Price</th><th>Guide</th><th>Result</th><th>Agency</th>
    </tr></thead><tbody id="sold-tbody"></tbody></table></div>
    <div class="pagination" id="sold-paging"></div>`;
  filterSold();
}

function filterSold() {
  const sub = document.getElementById('sold-suburb')?.value || '';
  const method = document.getElementById('sold-method')?.value || '';
  const q = (document.getElementById('sold-q')?.value || '').toLowerCase();
  const edits = lsGet('mmSoldEdits', {});

  let items = [...(D.soldListings||[])];
  if (sub) items = items.filter(l => l.suburb === sub);
  if (method) items = items.filter(l => (l.method||'') === method);
  if (q) items = items.filter(l => (l.address||'').toLowerCase().includes(q) || (l.agency||'').toLowerCase().includes(q));

  paginateTable('sold-tbody', 'sold-paging', items, l => {
    const key = `${l.date}|${l.suburb}|${l.beds}|${l.baths}|${l.agency}`;
    const e = edits[key] || {};
    const guide = e.guidePrice || l.price || '—';
    const sold = e.soldPrice || l.soldPrice || l.price || '—';
    const guideNum = parsePrice(guide);
    const soldNum = parsePrice(sold);
    let pctBadge = '';
    if (guideNum && soldNum && guideNum !== soldNum) {
      const pct = ((soldNum - guideNum) / guideNum * 100).toFixed(0);
      pctBadge = parseInt(pct) >= 0 ? `<span class="badge badge-green">+${pct}%</span>` : `<span class="badge badge-red">${pct}%</span>`;
    }

    let methodBadge = '';
    if (l.method === 'Auction') methodBadge = '<span class="badge badge-blue">Auction</span>';
    else if (l.method === 'Private Treaty') methodBadge = '<span class="badge badge-green">Private Treaty</span>';
    else if (l.method === 'Prior to Auction') methodBadge = '<span class="badge badge-amber">Prior to Auction</span>';
    else methodBadge = `<span class="badge badge-gray">${l.method||'—'}</span>`;

    return `<tr>
      <td style="font-size:11px">${l.date||'—'}</td>
      <td>${methodBadge}</td>
      <td style="font-weight:600">${l.address||'—'}</td>
      <td><span class="suburb-pill">${l.suburb||'—'}</span></td>
      <td style="text-align:center">${l.beds||'—'}</td>
      <td style="font-weight:600;color:var(--green)">${sold}</td>
      <td style="font-size:11px;color:var(--text-light)">${guide}</td>
      <td>${pctBadge}</td>
      <td style="font-size:11px">${l.agency||''}</td>
    </tr>`;
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// TOP PERFORMERS TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildTopPerformersTab() {
  const el = document.getElementById('page-topperformers');
  const status = lsGet('mmCallStatus', {});
  const comments = lsGet('mmCallComments', {});

  el.innerHTML = `
    <div class="page-title">Top Performers</div>
    <div class="page-sub">Highest-ranked agents by call priority score</div>
    <div class="table-wrap"><table><thead><tr>
      <th style="text-align:center">Score</th><th>Name</th><th>Agency</th><th>Suburb</th><th style="text-align:center">Sales</th><th style="text-align:center">For Sale</th><th style="text-align:center">Called</th><th style="text-align:center">VM</th><th>Notes</th><th>Profile</th>
    </tr></thead><tbody id="tp-tbody"></tbody></table></div>
    <div class="pagination" id="tp-paging"></div>`;

  paginateTable('tp-tbody', 'tp-paging', D.topPerformers||[], a => {
    const key = `${a.name}|${a.agency}`;
    const s = status[key] || {};
    const comment = comments[key] || '';
    const rowClass = s.called ? 'called' : (s.vm ? 'vm' : '');
    return `<tr class="${rowClass}">
      <td style="text-align:center;font-weight:700;color:${a.score>=50?'#2E7D32':(a.score>=30?'#E65100':'var(--text-light)')}">${a.score||0}</td>
      <td style="font-weight:600">${a.name}</td>
      <td style="font-size:11px">${a.agency||'—'}</td>
      <td><span class="suburb-pill">${a.suburb||''}</span></td>
      <td style="text-align:center;font-weight:600">${a.totalSales||0}</td>
      <td style="text-align:center">${a.forSale||0}</td>
      <td style="text-align:center"><input type="checkbox" class="checkbox" ${s.called?'checked':''} onchange="toggleAgentCall('${key.replace(/'/g,"\\'")}')" title="Called"></td>
      <td style="text-align:center"><input type="checkbox" class="checkbox" ${s.vm?'checked':''} onchange="toggleAgentVM('${key.replace(/'/g,"\\'")}')" title="Left VM"></td>
      <td><textarea class="agent-comment" onblur="saveAgentComment('${key.replace(/'/g,"\\'")}',this.value)">${comment}</textarea></td>
      <td>${a.url?`<a href="${a.url}" target="_blank" class="badge badge-blue" style="text-decoration:none">Profile</a>`:''}</td>
    </tr>`;
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// ALL AGENTS TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildAllAgentsTab() {
  const el = document.getElementById('page-allagents');
  const suburbs = [...new Set((D.allAgents||[]).map(a=>a.suburb))].sort();
  const status = lsGet('mmCallStatus', {});
  const comments = lsGet('mmCallComments', {});

  el.innerHTML = `
    <div class="page-title">All Agents</div>
    <div class="page-sub">${(D.allAgents||[]).length} agents across the Lower North Shore</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Suburb</label><select id="ag-suburb" onchange="filterAllAgents()"><option value="">All</option>${suburbs.map(s=>`<option>${s}</option>`).join('')}</select></div>
      <div class="filter-group"><label>Search</label><input id="ag-q" placeholder="Name or agency..." oninput="filterAllAgents()"></div>
    </div>
    <div class="table-wrap"><table><thead><tr>
      <th style="text-align:center">Score</th><th>Name</th><th>Agency</th><th>Mobile</th><th>Suburb</th><th>Also In</th><th style="text-align:center">Sales</th><th style="text-align:center">Called</th><th style="text-align:center">VM</th><th>Notes</th>
    </tr></thead><tbody id="ag-tbody"></tbody></table></div>
    <div class="pagination" id="ag-paging"></div>`;
  filterAllAgents();
}

function filterAllAgents() {
  const sub = document.getElementById('ag-suburb')?.value || '';
  const q = (document.getElementById('ag-q')?.value || '').toLowerCase();
  const status = lsGet('mmCallStatus', {});
  const comments = lsGet('mmCallComments', {});

  let items = [...(D.allAgents||[])];
  if (sub) items = items.filter(a => a.suburb === sub);
  if (q) items = items.filter(a => (a.name||'').toLowerCase().includes(q) || (a.agency||'').toLowerCase().includes(q));

  paginateTable('ag-tbody', 'ag-paging', items, a => {
    const key = `${a.name}|${a.agency}`;
    const s = status[key] || {};
    const comment = comments[key] || '';
    const rowClass = s.called ? 'called' : (s.vm ? 'vm' : '');
    return `<tr class="${rowClass}">
      <td style="text-align:center;font-weight:700;color:${a.score>=50?'#2E7D32':(a.score>=30?'#E65100':'var(--text-light)')}">${a.score||0}</td>
      <td style="font-weight:600">${a.name}</td>
      <td style="font-size:11px">${a.agency||'—'}</td>
      <td style="font-size:12px;color:#1565C0">${a.mobile||'—'}</td>
      <td><span class="suburb-pill">${a.suburb||''}</span></td>
      <td style="font-size:11px;color:var(--text-light);max-width:180px">${a.also||''}</td>
      <td style="text-align:center;font-weight:600">${a.totalSales||0}</td>
      <td style="text-align:center"><input type="checkbox" class="checkbox" ${s.called?'checked':''} onchange="toggleAgentCall('${key.replace(/'/g,"\\'")}')" title="Called"></td>
      <td style="text-align:center"><input type="checkbox" class="checkbox" ${s.vm?'checked':''} onchange="toggleAgentVM('${key.replace(/'/g,"\\'")}')" title="VM"></td>
      <td><textarea class="agent-comment" onblur="saveAgentComment('${key.replace(/'/g,"\\'")}',this.value)">${comment}</textarea></td>
    </tr>`;
  });
}

function toggleAgentCall(key) {
  const s = lsGet('mmCallStatus', {}); if (!s[key]) s[key]={}; s[key].called = !s[key].called;
  lsSet('mmCallStatus', s);
}

function toggleAgentVM(key) {
  const s = lsGet('mmCallStatus', {}); if (!s[key]) s[key]={}; s[key].vm = !s[key].vm;
  lsSet('mmCallStatus', s);
}

function saveAgentComment(key, value) {
  const c = lsGet('mmCallComments', {}); c[key] = value; lsSet('mmCallComments', c);
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROPING TAB
// ═══════════════════════════════════════════════════════════════════════════════
function propAddrLink(p) {
  const url = p.domain_url || ('https://www.domain.com.au/sale/?q=' + encodeURIComponent((p.address||'') + ', NSW, Australia'));
  return `<a href="${url}" target="_blank" rel="noopener">${p.address}</a>`;
}

function renderPropRow(p, type) {
  const change = p.price_change ? `<span class="${p.price_change.startsWith('-')?'p-change-neg':'p-change-pos'}">${p.price_change}</span>` : '';
  const soldInfo = (type==='sold'&&p.sold_price) ? `<span class="p-price">${p.sold_price}</span><span class="p-agent" style="margin-left:4px">Guide: ${p.price_guide||'—'}</span>` : `<span class="p-price">${p.price||'—'}</span> ${change}`;
  const beds = p.beds ? `<span class="p-beds">${p.beds}bd${p.days_listed?' · '+p.days_listed+'d':''}</span>` : '';
  const agent = p.agent ? `<span class="p-agent">${p.agent}${p.agency?' / '+p.agency:''}</span>` : '';
  const chip = p.date ? `<span class="p-date-chip">${p.date}</span>` : '';
  return `<div class="p-row"><span class="p-addr">${propAddrLink(p)}</span> ${beds} ${soldInfo} ${agent} ${chip}</div>`;
}

function buildPropingTab() {
  const el = document.getElementById('page-proping');
  if (typeof propingHistory === 'undefined' || !propingHistory.length) {
    el.innerHTML = '<div class="page-title">Proping — 7-Day Snapshot</div><div class="empty-state"><div class="icon">📬</div>No Proping data yet. Run the email pipeline to populate.</div>';
    return;
  }

  const dates = propingHistory.map(e=>e.date).filter(Boolean);
  const rangeLabel = dates.length>1?`${dates[dates.length-1]} – ${dates[0]}`:(dates[0]||'');

  el.innerHTML = `
    <div class="page-title">Proping — 7-Day Snapshot</div>
    <div class="page-sub">${rangeLabel}</div>
    <div class="filter-bar">
      <div class="filter-group"><label>Search</label><input id="proping-q" placeholder="Suburb or address..." oninput="renderPropingContent()"></div>
      <div class="filter-group"><label>Activity</label><select id="proping-section-filter" onchange="renderPropingContent()">
        <option value="">All Activity</option><option value="price_changes">Price Changes</option><option value="newly_listed">Newly Listed</option><option value="sold">Sold</option>
      </select></div>
    </div>
    <div id="proping-body"></div>`;
  renderPropingContent();
}

function renderPropingContent() {
  const q = (document.getElementById('proping-q')?.value||'').toLowerCase();
  const secFilt = document.getElementById('proping-section-filter')?.value||'';
  const seen = new Set();
  const suburbMap = {};

  for (const day of propingHistory) {
    for (const section of ['price_changes','newly_listed','sold']) {
      for (const p of (day[section]||[])) {
        const addr = (p.address||'').toLowerCase();
        if (!addr || seen.has(addr)) continue;
        seen.add(addr);
        const suburb = (p.suburb||'Unknown').trim()||'Unknown';
        if (!suburbMap[suburb]) suburbMap[suburb] = {price_changes:[],newly_listed:[],sold:[]};
        if (q && !addr.includes(q) && !suburb.toLowerCase().includes(q)) continue;
        if (secFilt && section !== secFilt) continue;
        suburbMap[suburb][section].push(p);
      }
    }
  }

  const suburbs = Object.keys(suburbMap).filter(s => suburbMap[s].price_changes.length+suburbMap[s].newly_listed.length+suburbMap[s].sold.length > 0).sort();
  const LABELS = {price_changes:'Price Changes',newly_listed:'Newly Listed',sold:'Sold'};

  let html = '';
  for (const suburb of suburbs) {
    const d = suburbMap[suburb];
    html += `<div class="p-suburb-block"><div class="p-suburb-hdr">${suburb}
      <div class="p-suburb-counts">
        ${d.price_changes.length?`<span class="p-cnt p-cnt-change">↓ ${d.price_changes.length}</span>`:''}
        ${d.newly_listed.length?`<span class="p-cnt p-cnt-new">+ ${d.newly_listed.length}</span>`:''}
        ${d.sold.length?`<span class="p-cnt p-cnt-sold">✓ ${d.sold.length}</span>`:''}
      </div></div>`;
    for (const [key, label] of Object.entries(LABELS)) {
      if (d[key].length) {
        html += `<div class="p-section-label">${label}</div>`;
        html += d[key].map(p => renderPropRow(p, key)).join('');
      }
    }
    html += '</div>';
  }

  if (!html) html = '<div class="empty-state">No matching properties</div>';
  document.getElementById('proping-body').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAZAR MARTIN REPORT TAB
// ═══════════════════════════════════════════════════════════════════════════════
function buildMazarMartinTab() {
  const el = document.getElementById('page-mazarmartin');
  const hist = typeof PROPING_HISTORY !== 'undefined' ? PROPING_HISTORY : [];

  if (!hist.length) {
    el.innerHTML = '<div class="page-title">Mazar Martin Report</div><div class="empty-state"><div class="icon">📊</div>No report data available.</div>';
    return;
  }

  let html = `<div class="page-title">Mazar Martin Report</div><div class="page-sub">Market activity summary</div>`;

  for (const day of hist) {
    html += `<div class="card" style="margin-bottom:16px"><div class="card-title">${day.date||'—'}</div>`;
    for (const section of ['price_changes','newly_listed','sold']) {
      const items = day[section] || [];
      if (!items.length) continue;
      const label = section === 'price_changes' ? 'Price Changes' : section === 'newly_listed' ? 'Newly Listed' : 'Sold';
      const badgeClass = section === 'price_changes' ? 'badge-red' : section === 'newly_listed' ? 'badge-green' : 'badge-blue';
      html += `<div style="margin:8px 0 4px;font-weight:600;font-size:12px"><span class="badge ${badgeClass}">${label} (${items.length})</span></div>`;
      html += '<div class="table-wrap" style="margin-bottom:8px"><table><thead><tr><th>Address</th><th>Suburb</th><th>Price</th><th>Agent</th></tr></thead><tbody>';
      items.forEach(p => {
        html += `<tr><td style="font-weight:600">${p.address||'—'}</td><td><span class="suburb-pill">${p.suburb||''}</span></td><td style="font-weight:600">${p.price||p.sold_price||'—'}</td><td style="font-size:11px">${p.agent||''} ${p.agency?'/ '+p.agency:''}</td></tr>`;
      });
      html += '</tbody></table></div>';
    }
    html += '</div>';
  }

  el.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════════
window.addEventListener('load', () => {
  buildTabBar();
  buildPages();
  showTab('dashboard', document.querySelector('[data-tab="dashboard"]'));
});
"""

# ── Assemble ─────────────────────────────────────────────────────────────────
print("Assembling Mazar Martin app...")

output = HTML_HEAD + '\n'
output += CSS + '\n'
output += HTML_MID + '\n'

# Data
output += d_line + '\n'
output += proping_line + '\n\n'
output += coords_block + '\n\n'

# Injection markers
output += proping_inject + '\n\n'
output += offmkt_inject + '\n\n'

# Main JS
output += JS + '\n'

output += '</script>\n</body>\n</html>\n'

NEW_APP.write_text(output, encoding='utf-8')
print(f"Saved: {NEW_APP} ({len(output):,} bytes)")
print(f"Lines: {output.count(chr(10))}")
