h = open('/Users/gf/Downloads/mazar_martin_app.html').read()

# ── 1. Sort Active Buyers by temperature (Hot → Warm → Cold) ──────────────────
old_sort = "let items = [...(D.sampleListings||[]), ...userAdded]"
# Find in buildActiveBuyersSection context
idx = h.find('function buildActiveBuyersSection')
# Find where clients array is sorted
sort_idx = h.find("clients.sort", idx)
if sort_idx == -1:
    # Add sort after clients are built
    clients_idx = h.find("const clients = ", idx)
    if clients_idx != -1:
        end_idx = h.find(";", clients_idx) + 1
        old_clients = h[clients_idx:end_idx]
        new_clients = old_clients + """
  const tempOrder = {hot:0, warm:1, cold:2};
  clients.sort((a,b) => {
    const ea = edits[a.name]||{}, eb = edits[b.name]||{};
    const ta = (ea.temperature||a.temperature||'warm').toLowerCase();
    const tb = (eb.temperature||b.temperature||'warm').toLowerCase();
    return (tempOrder[ta]??1) - (tempOrder[tb]??1);
  });"""
        h = h.replace(old_clients, new_clients)
        print("✅ Sort added")
    else:
        print("❌ clients array not found")
else:
    print("Sort already exists")

# ── 2. Add tracker stats at top of clients page ───────────────────────────────
old_header = 'Manage buyers, sellers, and your pipeline'
new_header = '''Manage buyers, sellers, and your pipeline</p>
    <div id="client-stats" style="display:flex;gap:16px;margin:12px 0 4px;flex-wrap:wrap">
      <div style="background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:12px 20px;min-width:160px">
        <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">Bought This Month</div>
        <div id="stat-settled" style="font-size:28px;font-weight:700;color:#006039">0</div>
      </div>
      <div style="background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:12px 20px;min-width:160px">
        <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">New Pipeline Leads</div>
        <div id="stat-pipeline" style="font-size:28px;font-weight:700;color:#b9955a">0</div>
      </div>
      <div style="background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:12px 20px;min-width:160px">
        <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">Signed This Month</div>
        <div id="stat-signed" style="font-size:28px;font-weight:700;color:#1565C0">0</div>
      </div>
    </div>
    <script>
    (function(){
      const now = new Date();
      const ym = now.getFullYear()+'-'+(now.getMonth()+1).toString().padStart(2,'0');
      const edits = JSON.parse(localStorage.getItem('mmClientEdits')||'{}');
      let settled=0, pipeline=0, signed=0;
      Object.values(edits).forEach(e => {
        if(e.settledDate && e.settledDate.startsWith(ym)) settled++;
        if(e.pipelineAddedDate && e.pipelineAddedDate.startsWith(ym)) pipeline++;
        if(e.signedDate && e.signedDate.startsWith(ym)) signed++;
      });
      document.getElementById('stat-settled').textContent=settled;
      document.getElementById('stat-pipeline').textContent=pipeline;
      document.getElementById('stat-signed').textContent=signed;
    })();
    </script'''

if old_header in h:
    h = h.replace(old_header, new_header)
    print("✅ Stats tracker added")
else:
    print("❌ Header not found")

# ── 3. Add Move to Settlements button in Active Buyers rows ───────────────────
old_edit_btn = "onclick=\"editClient(this,'${eName}')\">Edit</button></td></tr>`;"
new_edit_btn = """onclick="editClient(this,'${eName}')">Edit</button>
        <button class="btn-sm" style="background:#006039;color:#fff;margin-left:4px" onclick="moveToSettlements('${eName}')">→ Settled</button>
      </td></tr>`;"""

if old_edit_btn in h:
    h = h.replace(old_edit_btn, new_edit_btn, 1)
    print("✅ Move to Settlements button added")
else:
    print("❌ Edit button pattern not found in Active Buyers")

open('/Users/gf/Downloads/mazar_martin_app.html', 'w').write(h)
print("Saved.")
