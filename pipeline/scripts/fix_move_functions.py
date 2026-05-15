h = open('/Users/gf/Downloads/mazar_martin_app.html').read()

old = """function moveToSettlements(name) {
  if (!confirm('Move ' + name + ' to Settlements? This means they have bought.')) return;
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].section = 'settlements';
  edits[name].settledDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  showToast(name + ' moved to Settlements.');
  buildActiveBuyersSection(edits);
  buildSellersSection(edits);
}

function moveToPipeline(name) {
  if (!confirm('Move ' + name + ' to Active Buyers? This means they have signed.')) return;
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].section = 'active';
  edits[name].signedDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  showToast(name + ' moved to Active Buyers.');
  buildActiveBuyersSection(edits);
  buildPipelineSection(edits);
}

function moveToActive(name) {
  moveToPipeline(name);
}"""

new = """function moveToSettlements(name) {
  if (!confirm('Move ' + name + ' to Settlements? This means they have bought.')) return;
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].section = 'settlements';
  edits[name].settledDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  showToast(name + ' moved to Settlements - Bought This Month updated!');
  buildActiveBuyersSection(edits);
  buildSellersSection(edits);
  updateClientStats(edits);
}

function moveToPipeline(name) {
  if (!confirm('Move ' + name + ' to Active Buyers? This means they have signed.')) return;
  const edits = lsGet('mmClientEdits', {});
  if (!edits[name]) edits[name] = {};
  edits[name].section = 'active';
  edits[name].signedDate = new Date().toISOString().slice(0,7);
  lsSet('mmClientEdits', edits);
  showToast(name + ' moved to Active Buyers - Signed This Month updated!');
  buildActiveBuyersSection(edits);
  buildPipelineSection(edits);
  updateClientStats(edits);
}

function moveToActive(name) {
  moveToPipeline(name);
}"""

if old in h:
    h = h.replace(old, new)
    print('Fixed')
else:
    print('NOT FOUND')

# Also fix updateClientStats to read correctly
old2 = "function updateClientStats(e){const ym=new Date().toISOString().slice(0,7);let s=0,p=0,g=0;Object.values(e).forEach(x=>{if(x.settledDate&&x.settledDate.startsWith(ym))s++;if(x.pipelineAddedDate&&x.pipelineAddedDate.startsWith(ym))p++;if(x.signedDate&&x.signedDate.startsWith(ym))g++;});const se=document.getElementById(\"stat-settled\"),pe=document.getElementById(\"stat-pipeline\"),ge=document.getElementById(\"stat-signed\");if(se)se.textContent=s;if(pe)pe.textContent=p;if(ge)ge.textContent=g;}"
new2 = """function updateClientStats(e) {
  const ym = new Date().toISOString().slice(0,7);
  let settled=0, pipeline=0, signed=0;
  Object.values(e).forEach(x => {
    if (x.settledDate && x.settledDate.startsWith(ym)) settled++;
    if (x.pipelineAddedDate && x.pipelineAddedDate.startsWith(ym)) pipeline++;
    if (x.signedDate && x.signedDate.startsWith(ym)) signed++;
  });
  const se=document.getElementById('stat-settled');
  const pe=document.getElementById('stat-pipeline');
  const ge=document.getElementById('stat-signed');
  if(se) se.textContent=settled;
  if(pe) pe.textContent=pipeline;
  if(ge) ge.textContent=signed;
}"""

if old2 in h:
    h = h.replace(old2, new2)
    print('Stats function expanded')
else:
    print('Stats function not found - may already be expanded')

open('/Users/gf/Downloads/mazar_martin_app.html', 'w').write(h)
print('Saved.')
