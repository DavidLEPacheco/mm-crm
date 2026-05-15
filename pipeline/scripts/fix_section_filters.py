h = open('/Users/gf/Downloads/mazar_martin_app.html').read()

# Fix buildActiveBuyersSection to respect edits section
old = "const buyers = (D.xlsxClients||[]).filter(c => (c.section||'').includes('Buyer'));"
new = """const buyers = (D.xlsxClients||[]).filter(c => {
    const override = (edits[c.name]||{}).section;
    if (override) return override === 'active' || override === 'Active Buyer';
    return (c.section||'').includes('Buyer');
  });"""

if old in h:
    h = h.replace(old, new, 1)
    print('Active buyers filter fixed')
else:
    print('Active buyers filter NOT FOUND')

# Fix buildPipelineSection to respect edits section
old2 = "const pipeline = (D.xlsxClients||[]).filter(c => (c.section||'').toLowerCase().includes('pipeline'));"
new2 = """const pipeline = (D.xlsxClients||[]).filter(c => {
    const override = (edits[c.name]||{}).section;
    if (override) return override === 'Pipeline' || override === 'pipeline';
    return (c.section||'').toLowerCase().includes('pipeline');
  });"""

if old2 in h:
    h = h.replace(old2, new2, 1)
    print('Pipeline filter fixed')
else:
    print('Pipeline filter NOT FOUND - checking...')
    idx = h.find('function buildPipelineSection')
    idx2 = h.find('filter(c =>', idx)
    print(repr(h[idx2:idx2+100]))

# Fix buildSellersSection to include moved-to-settlements clients
old3 = "const sellers = (D.xlsxClients||[]).filter(c => (c.section||'').toLowerCase().includes('settlement'));"
new3 = """const sellers = (D.xlsxClients||[]).filter(c => {
    const override = (edits[c.name]||{}).section;
    if (override) return override === 'settlements';
    return (c.section||'').toLowerCase().includes('settlement');
  });
  // Also add any clients moved to settlements via edits
  const movedToSettlements = Object.entries(edits)
    .filter(([name, e]) => e.section === 'settlements' && !sellers.find(s => s.name === name))
    .map(([name, e]) => ({name, section:'settlements', ...e}));
  sellers.push(...movedToSettlements);"""

if old3 in h:
    h = h.replace(old3, new3, 1)
    print('Settlements filter fixed')
else:
    print('Settlements filter NOT FOUND - checking...')
    idx = h.find('function buildSellersSection')
    idx2 = h.find('filter(c =>', idx)
    print(repr(h[idx2:idx2+100]))

open('/Users/gf/Downloads/mazar_martin_app.html', 'w').write(h)
print('Saved.')
