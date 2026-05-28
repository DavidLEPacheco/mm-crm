from pathlib import Path
_APP = Path(__file__).resolve().parent.parent / 'mazar_martin_app.html'
h = open(_APP).read()

# Find exact pipeline edit button text
idx = h.find('function buildPipelineSection')
idx2 = h.find('Edit</button>', idx)
print('Context:', repr(h[idx2-60:idx2+100]))

# Replace with move to active button added
old = h[idx2-60:idx2+100]
new = old.replace(
    "Edit</button></td>",
    "Edit</button>\n        <button class=\"btn-sm\" style=\"background:#1565C0;color:#fff;margin-left:4px\" onclick=\"moveToActive('${eName}')\">→ Active</button></td>"
)
if old != new:
    h = h.replace(old, new, 1)
    print('Pipeline → Active button added')
else:
    print('No change made')

# Add simple add forms at end of each section
# Find refresh matches button area
idx3 = h.find('Refresh Matches</button>')
if idx3 != -1:
    # Add Active Buyer form before refresh button
    add_form = """<div style="margin-top:16px;background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:16px">
<div style="font-weight:600;color:var(--green);margin-bottom:10px">+ Add Active Buyer</div>
<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end">
<div><label style="font-size:11px;color:#888">Name</label><br><input id="ab-name" placeholder="Client name" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px"></div>
<div><label style="font-size:11px;color:#888">BA</label><br><input id="ab-ba" placeholder="GM/JM" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:80px"></div>
<div><label style="font-size:11px;color:#888">Suburbs</label><br><input id="ab-suburbs" placeholder="Mosman, Cremorne" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:180px"></div>
<div><label style="font-size:11px;color:#888">Budget</label><br><input id="ab-budget" placeholder="$5m-$6m" style="padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:120px"></div>
<button class="btn-sm btn-gold" onclick="addActiveBuyer()">Add Buyer</button>
</div></div>"""
    h = h.replace("html += '<div class=\"btn-row\"", add_form + "\n  html += '<div class=\"btn-row\"", 1)
    print('Active buyer form added')

open(_APP, 'w').write(h)
print('Saved.')
