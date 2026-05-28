import json, re
from pathlib import Path

_DL = Path(__file__).resolve().parent.parent

new_entries = [
    {"address":"48 Neerim Road","suburb":"Castle Cove","soldDate":"2026-03-05","guidePrice":"$4,000,000","soldPrice":"$4,200,000"},
    {"address":"1 Willowie Road","suburb":"Castle Cove","soldDate":"2026-03-06","guidePrice":"$4,000,000","soldPrice":"$4,000,000"},
    {"address":"9A Alleyne Street","suburb":"Chatswood","soldDate":"2026-02-28","guidePrice":"$4,000,000","soldPrice":"$4,205,000"},
    {"address":"10 Beresford Avenue","suburb":"Chatswood","soldDate":"2026-03-01","guidePrice":"$3,800,000","soldPrice":"$4,288,000"},
    {"address":"8A Wood Street","suburb":"Chatswood","soldDate":"2026-03-03","guidePrice":"$2,200,000","soldPrice":"$2,250,000"},
    {"address":"362 Penshurst Street","suburb":"Chatswood","soldDate":"2026-03-03","guidePrice":"$3,500,000","soldPrice":"$3,770,000"},
    {"address":"74 Macpherson Street","suburb":"Cremorne","soldDate":"2026-03-05","guidePrice":"$4,650,000","soldPrice":"$4,650,000"},
    {"address":"33 Spofforth Street","suburb":"Mosman","soldDate":"2026-03-02","guidePrice":"$4,700,000","soldPrice":"$5,075,000"},
    {"address":"51 Prince Street","suburb":"Mosman","soldDate":"2026-03-02","guidePrice":"$7,000,000","soldPrice":"$6,600,000"},
    {"address":"19 Wyong Road","suburb":"Mosman","soldDate":"2026-03-04","guidePrice":"$7,800,000","soldPrice":"$8,085,000"},
    {"address":"55 Wolseley Road","suburb":"Mosman","soldDate":"2026-03-05","guidePrice":"$8,000,000","soldPrice":"$7,430,000"},
    {"address":"14 Kirkoswald Avenue","suburb":"Mosman","soldDate":"2026-03-05","guidePrice":"$8,500,000","soldPrice":"$8,510,000"},
    {"address":"32 Lang Street","suburb":"Mosman","soldDate":"2026-03-06","guidePrice":"$4,000,000","soldPrice":"$3,900,000"},
    {"address":"33 Clanalpine Street","suburb":"Mosman","soldDate":"2026-03-06","guidePrice":"$6,500,000","soldPrice":"$6,675,000"},
    {"address":"10 Phillips Street","suburb":"Neutral Bay","soldDate":"2026-02-27","guidePrice":"$3,800,000","soldPrice":"$3,875,000"},
    {"address":"13 Bank Street","suburb":"North Sydney","soldDate":"2026-03-06","guidePrice":"$3,450,000","soldPrice":"$3,370,000"},
    {"address":"59 Neutral Street","suburb":"North Sydney","soldDate":"2026-03-02","guidePrice":"$4,500,000","soldPrice":"$4,700,000"},
    {"address":"5 Pyalla Street","suburb":"Northbridge","soldDate":"2026-03-02","guidePrice":"$4,100,000","soldPrice":"$4,050,000"},
    {"address":"27 Narooma Road","suburb":"Northbridge","soldDate":"2026-03-27","guidePrice":"$6,200,000","soldPrice":"$5,330,000"},
    {"address":"47 Neeworra Road","suburb":"Northbridge","soldDate":"2026-03-05","guidePrice":"$7,500,000","soldPrice":"$5,500,000"},
    {"address":"15 Whatmore Street","suburb":"Waverton","soldDate":"2026-02-27","guidePrice":"$3,510,000","soldPrice":"$3,510,000"},
    {"address":"24 Cobar Street","suburb":"Willoughby","soldDate":"2026-02-28","guidePrice":"$5,100,000","soldPrice":"$5,200,000"},
    {"address":"14A Rocklands Road","suburb":"Wollstonecraft","soldDate":"2026-03-04","guidePrice":"$2,650,000","soldPrice":"$2,975,000"},
    {"address":"30 Milray Avenue","suburb":"Wollstonecraft","soldDate":"2026-03-04","guidePrice":"$5,000,000","soldPrice":"$5,000,000"},
]

h = open(_DL / 'mazar_martin_app.html').read()
m = re.search('"soldListings"\\s*:\\s*(\\[.*?\\])\\s*[,}]', h, re.DOTALL)
sold = json.loads(m.group(1))

# Remove any previous manual entries for these
manual_ids = ['manual_' + r['address'].lower().replace(' ','').replace('/','') for r in new_entries]
sold = [s for s in sold if s.get('id') not in manual_ids]

# Add clean entries
for row in new_entries:
    sold.append({
        'id': 'manual_' + row['address'].lower().replace(' ','').replace('/',''),
        'address': row['address'] + ', ' + row['suburb'] + ' NSW',
        'suburb': row['suburb'],
        'soldPrice': row['soldPrice'],
        'guidePrice': row['guidePrice'],
        'soldDate': row['soldDate'],
        'method': 'Auction',
        'source': 'manual'
    })

sold.sort(key=lambda x: x.get('soldDate',''), reverse=True)
open(_DL / 'mazar_martin_app.html', 'w').write(h[:m.start(1)] + json.dumps(sold) + h[m.end(1):])
print(f'Done. Total: {len(sold)}')
