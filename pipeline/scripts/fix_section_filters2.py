h = open('/Users/gf/Downloads/mazar_martin_app.html').read()

# Fix Pipeline filter
old2 = "filter(c => (c.section||'').includes('Pipeline'));"
new2 = """filter(c => {
    const ov = (edits[c.name]||{}).section;
    if (ov) return ov === 'Pipeline' || ov === 'pipeline';
    return (c.section||'').includes('Pipeline');
  });"""
if old2 in h:
    h = h.replace(old2, new2, 1)
    print('Pipeline filter fixed')
else:
    print('Pipeline NOT FOUND')

# Fix Sellers/Settlements filter
old3 = "filter(c => (c.section||'').includes('Seller'));"
new3 = """filter(c => {
    const ov = (edits[c.name]||{}).section;
    if (ov) return ov === 'settlements';
    return (c.section||'').includes('Seller');
  });
  const movedToSettlements = Object.entries(edits)
    .filter(([name, e]) => e.section === 'settlements' && !sellers.find(s => s.name === name))
    .map(([name, e]) => ({name, section:'settlements', ...e}));
  sellers.push(...movedToSettlements);"""
if old3 in h:
    h = h.replace(old3, new3, 1)
    print('Settlements filter fixed')
else:
    print('Settlements NOT FOUND')

open('/Users/gf/Downloads/mazar_martin_app.html', 'w').write(h)
print('Saved.')
