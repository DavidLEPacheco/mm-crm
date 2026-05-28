from pathlib import Path
_APP = Path(__file__).resolve().parent.parent / 'mazar_martin_app.html'
h = open(_APP).read()

old = "if (!confirm('Withdraw this listing? It will be moved to Off Market.')) return;"

new = """const action = prompt('What to do with this listing?\\n\\n1 = Move to Off Market\\n2 = Permanently Delete (blacklisted forever)\\n\\nEnter 1 or 2:');
  if (!action) return;
  if (action === '2') {
    if (!confirm('Permanently delete? This property will never come back.')) return;
    const bl = JSON.parse(localStorage.getItem('mmBlacklist') || '[]');
    bl.push(normKey);
    localStorage.setItem('mmBlacklist', JSON.stringify(bl));
    const del2 = JSON.parse(localStorage.getItem('mmDeletedFS') || '[]');
    del2.push(normKey);
    localStorage.setItem('mmDeletedFS', JSON.stringify(del2));
    filterForSale();
    showToast('Permanently deleted and blacklisted.');
    return;
  }
  if (action !== '1') return;"""

if old in h:
    h = h.replace(old, new)
    open(_APP, 'w').write(h)
    print('Done')
else:
    print('NOT FOUND')
