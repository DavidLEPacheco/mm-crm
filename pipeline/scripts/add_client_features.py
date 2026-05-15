h = open('/Users/gf/Downloads/mazar_martin_app.html').read()

# Fix hyperlinked properties in buildPipelineSection
h = h.replace('[c.name](http://c.name)', 'c.name')
h = h.replace('[e.name](http://e.name)', 'e.name')
h = h.replace('[e.ba](http://e.ba)', 'e.ba')
h = h.replace('[c.ba](http://c.ba)', 'c.ba')
h = h.replace('[c.date](http://c.date)', 'c.date')

# 1. Add "Move to Active" button in Pipeline rows
old_pipe_edit = "onclick=\"editClient(this,'${eName}')\">Edit</button></td></tr>`;\n  });\n  html += '</tbody></table></div>';\n  el.innerHTML = html;\n}\n\nfunction buildMyClientsSection"
new_pipe_edit = "onclick=\"editClient(this,'${eName}')\">Edit</button>\n        <button class=\"btn-sm\" style=\"background:#1565C0;color:#fff;margin-left:4px\" onclick=\"moveToActive('${eName}')\">→ Active</button>\n      </td></tr>`;\n  });\n\n  // Add new pipeline lead form\n  html += `</tbody></table></div>\n  <div style=\"margin-top:16px;background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:16px\">\n    <div style=\"font-weight:600;color:var(--green);margin-bottom:10px\">+ Add Pipeline Lead</div>\n    <div style=\"display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end\">\n      <div><label style=\"font-size:11px;color:#888\">Name</label><br><input id=\"pl-name\" placeholder=\"Client name\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px\"></div>\n      <div><label style=\"font-size:11px;color:#888\">BA</label><br><input id=\"pl-ba\" placeholder=\"GM / JM\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:80px\"></div>\n      <div><label style=\"font-size:11px;color:#888\">Suburbs</label><br><input id=\"pl-suburbs\" placeholder=\"Mosman, Cremorne\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:180px\"></div>\n      <div><label style=\"font-size:11px;color:#888\">Budget</label><br><input id=\"pl-budget\" placeholder=\"$5m-$6m\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:120px\"></div>\n      <button class=\"btn-sm btn-gold\" onclick=\"addPipelineLead()\">Add Lead</button>\n    </div>\n  </div>`;\n  el.innerHTML = html;\n}\n\nfunction buildMyClientsSection"

if old_pipe_edit in h:
    h = h.replace(old_pipe_edit, new_pipe_edit, 1)
    print('✅ Pipeline move + add form added')
else:
    print('❌ Pipeline edit button not found')
    # Try to find it
    idx = h.find('function buildPipelineSection')
    idx2 = h.find('Edit</button>', idx)
    print('Found at:', idx2)
    print(repr(h[idx2-30:idx2+80]))

# 2. Add "Add Active Buyer" form to Active Buyers section
old_active_end = "  html += '<div class=\"btn-row\" style=\"margin-top:16px\"><button class=\"btn-gold\" onclick=\"refreshClientMatches()\">Refresh Matches</button><div style=\"font-size:11px;color:var(--text-mid);margin-top:4px\">Re-match all clients against current For Sale and Off Market listings</div></div>';"
new_active_end = "  html += '<div style=\"margin-top:16px;background:#fff;border:1px solid #e0d9ce;border-radius:8px;padding:16px\"><div style=\"font-weight:600;color:var(--green);margin-bottom:10px\">+ Add Active Buyer</div><div style=\"display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end\"><div><label style=\"font-size:11px;color:#888\">Name</label><br><input id=\"ab-name\" placeholder=\"Client name\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px\"></div><div><label style=\"font-size:11px;color:#888\">BA</label><br><input id=\"ab-ba\" placeholder=\"GM / JM\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:80px\"></div><div><label style=\"font-size:11px;color:#888\">Suburbs</label><br><input id=\"ab-suburbs\" placeholder=\"Mosman, Cremorne\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:180px\"></div><div><label style=\"font-size:11px;color:#888\">Budget</label><br><input id=\"ab-budget\" placeholder=\"\\$5m-\\$6m\" style=\"padding:6px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;width:120px\"></div><button class=\"btn-sm btn-gold\" onclick=\"addActiveBuyer()\">Add Buyer</button></div></div>';\n  html += '<div class=\"btn-row\" style=\"margin-top:16px\"><button class=\"btn-gold\" onclick=\"refreshClientMatches()\">Refresh Matches</button><div style=\"font-size:11px;color:var(--text-mid);margin-top:4px\">Re-match all clients against current For Sale and Off Market listings</div></div>';"

if old_active_end in h:
    h = h.replace(old_active_end, new_active_end, 1)
    print('✅ Active buyer add form added')
else:
    print('❌ Active buyer end not found')

# 3. Add addActiveBuyer and addPipelineLead functions
new_funcs = """
function addActiveBuyer() {
  const name = document.getElementById('ab-name').value.trim();
  if (!name) { showToast('Enter a name'); return; }
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].ba = document.getElementById('ab-ba').value.trim();
  edits[name].locations = document.getElementById('ab-suburbs').value.trim();
  edits[name].budget = document.getElementById('ab-budget').value.trim();
  edits[name].section = 'Active Buyer';
  edits[name].addedDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  // Add to xlsxClients if not already there
  if (!D.xlsxClients) D.xlsxClients = [];
  if (!D.xlsxClients.find(c => c.name === name)) {
    D.xlsxClients.push({name, section:'Active Buyer', ba: edits[name].ba});
  }
  showToast(name + ' added to Active Buyers');
  buildActiveBuyersSection(edits);
}

function addPipelineLead() {
  const name = document.getElementById('pl-name').value.trim();
  if (!name) { showToast('Enter a name'); return; }
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].ba = document.getElementById('pl-ba').value.trim();
  edits[name].locations = document.getElementById('pl-suburbs').value.trim();
  edits[name].budget = document.getElementById('pl-budget').value.trim();
  edits[name].section = 'Pipeline';
  edits[name].pipelineAddedDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  if (!D.xlsxClients) D.xlsxClients = [];
  if (!D.xlsxClients.find(c => c.name === name)) {
    D.xlsxClients.push({name, section:'Pipeline', ba: edits[name].ba});
  }
  showToast(name + ' added to Pipeline');
  buildPipelineSection(edits);
  updateClientStats(edits);
}

"""

if 'function addActiveBuyer()' not in h:
    h = h.replace('function updateClientStats(', new_funcs + 'function updateClientStats(', 1)
    print('✅ Add functions inserted')

open('/Users/gf/Downloads/mazar_martin_app.html', 'w').write(h)
print('Saved.')
