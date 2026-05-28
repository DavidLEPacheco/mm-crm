#!/usr/bin/env python3
"""Inject spreadsheet data (new listings + sold) into mazar_martin_app.html."""
import json, re, os
from pathlib import Path

# Data extracted from the user's spreadsheet image
NEW_LISTINGS = [
    {"suburb":"Cammeray","address":"497 Miller Street, Cammeray","auction":"AUC 26th Feb @ 5.00pm","guide":"$2,350,000","land":711,"aspect":"South","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Cammeray","address":"54 Cammeray Road, Cammeray","auction":"AUC 26th Feb @ 5.00pm","guide":"$3,100,000","land":221,"aspect":"NW","type":"4 beds, 2 baths, Study"},
    {"suburb":"Cammeray","address":"5 Churchill Crescent, Cammeray","auction":"For Sale (Price guide)","guide":"$5,800,000","land":797,"aspect":"South","type":"5 beds, 3 baths, tandem DLUG + 2CS"},
    {"suburb":"Castlecrag","address":"135 Eastern Valley Way, Castlecrag","auction":"AUC 28th Feb @ 5.15pm","guide":"$3,300,000","land":493,"aspect":"East","type":"4 beds, 2 baths, 2CP"},
    {"suburb":"Castlecrag","address":"70 Sugarloaf Crescent, Castlecrag","auction":"For Sale (Guide price)","guide":"$3,600,000","land":3681,"aspect":"East","type":"Residential Land"},
    {"suburb":"Castlecrag","address":"101 The Bulwark, Castlecrag","auction":"For Sale (Guide price)","guide":"$4,000,000","land":676,"aspect":"South","type":"5 beds, 4 baths, DLUG"},
    {"suburb":"Castlecrag","address":"7 Knight Place, Castlecrag","auction":"AUC 5th Mar @ 9.00am","guide":"$5,850,000","land":904,"aspect":"East","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Castle Cove","address":"82 Deepwater Road, Castle Cove","auction":"AUC 21st Feb @ 12.00pm","guide":"$2,950,000","land":469,"aspect":"NE","type":"4 beds, 3 baths, LUG + 1CS"},
    {"suburb":"Castle Cove","address":"184 Boundary Street, Castle Cove","auction":"AUC 21st Feb @ 9.00am","guide":"$3,300,000","land":790,"aspect":"South","type":"5 beds, 3 baths, DLUG + 2CS"},
    {"suburb":"Castle Cove","address":"130 Deepwater Road, Castle Cove","auction":"For Sale (Guide price)","guide":"$3,500,000","land":816,"aspect":"North","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Chatswood","address":"112 Greville Street, Chatswood","auction":"AUC 28th Feb @ 9.45am","guide":"$2,300,000","land":443,"aspect":"West","type":"3 beds, 2 baths, LUG + 1CP"},
    {"suburb":"Chatswood","address":"26 Valerie Avenue, Chatswood","auction":"AUC 28th Feb @ 9.45am","guide":"$2,600,000","land":588,"aspect":"SE","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Chatswood","address":"26 Saywell Street, Chatswood","auction":"For Sale (Guide price)","guide":"$2,800,000","land":309,"aspect":"South","type":"3 beds, 2 baths, 2CS"},
    {"suburb":"Chatswood","address":"48 Baldry Street, Chatswood","auction":"AUC 26th Feb @ 6.00pm","guide":"$3,500,000","land":277,"aspect":"North","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Chatswood","address":"116 Beaconsfield Road, Chatswood","auction":"AUC 21st Feb @ 3.00pm","guide":"$3,600,000","land":968,"aspect":"South","type":"4 beds, 3 baths, 1CP"},
    {"suburb":"Chatswood","address":"15 Royal Street, Chatswood","auction":"AUC 21st Feb @ 12.45pm","guide":"$3,700,000","land":550,"aspect":"East","type":"4 beds, 3 baths, 1CP"},
    {"suburb":"Chatswood","address":"9A Alleyne Street, Chatswood","auction":"AUC 28th Feb @ 1.30pm","guide":"$4,000,000","land":405,"aspect":"East","type":"5 beds, 3 baths, 2CP"},
    {"suburb":"Cremorne","address":"48 Ellalong Road, Cremorne","auction":"AUC 21st Feb @ 2.15pm","guide":"$6,000,000","land":511,"aspect":"NW","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Cremorne","address":"4 Bromley Avenue, Cremorne Point","auction":"For Sale (Guide price)","guide":"$6,500,000","land":462,"aspect":"West","type":"4 bed, 3 bath, DLUG"},
    {"suburb":"Crows Nest","address":"66 Albany Street, Crows Nest","auction":"AUC 28th Feb @ 11.30am","guide":"$2,180,000","land":183,"aspect":"North","type":"2 beds, 1 bath, 1CS"},
    {"suburb":"Crows Nest","address":"69 Falcon Street, Crows Nest","auction":"For Sale (Guide price)","guide":"$4,300,000","land":483,"aspect":"South","type":"5 beds, 3 baths, LUG"},
    {"suburb":"Hunters Hill","address":"1 Futuna Street, Hunters Hill","auction":"AUC 28th Feb @ 12.45pm","guide":"$5,500,000","land":708,"aspect":"East","type":"4 beds, 2 baths, 2 CS"},
    {"suburb":"Hunters Hill","address":"22 Princes Street, Hunters Hill","auction":"For Sale (Guide price)","guide":"$5,800,000","land":563,"aspect":"South","type":"5 beds, 5 baths, DLUG"},
    {"suburb":"Middle Cove","address":"22 Highland Ridge, Middle Cove","auction":"AUC 28th Feb @ 12.45pm","guide":"$4,800,000","land":1156,"aspect":"North","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"61 Rangers Avenue, Mosman","auction":"AUC 26th Feb @ 11.30am","guide":"$2,900,000","land":221,"aspect":"North","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"177a Spit Road, Mosman","auction":"For Sale (Guide price)","guide":"$3,200,000","land":245,"aspect":"East","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"46 Spencer Road, Mosman","auction":"AUC 21st Feb @ 11.30am","guide":"$3,700,000","land":233,"aspect":"South","type":"4 beds, 2 baths"},
    {"suburb":"Mosman","address":"44 Musgrave Street, Mosman","auction":"AUC 21st Feb @ 5.00pm","guide":"$3,700,000","land":240,"aspect":"West","type":"4 beds, 3 baths, LUG"},
    {"suburb":"Mosman","address":"140 Cowles Road, Mosman","auction":"AUC 21st Feb @ 9.00am","guide":"$4,000,000","land":417,"aspect":"West","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"25 Spencer Road, Mosman","auction":"AUC 28th Feb @ 9.00am","guide":"$4,500,000","land":300,"aspect":"North","type":"4 beds, 2 baths, 1CP"},
    {"suburb":"Mosman","address":"28a Raglan Street, Mosman","auction":"AUC 28th Feb @ 9.00am","guide":"$5,000,000","land":626,"aspect":"West","type":"3 beds, 2 baths, DLUG (semi)"},
    {"suburb":"Mosman","address":"44 Prince Street, Mosman","auction":"AUC 21st Feb @ 12.45pm","guide":"$5,000,000","land":516,"aspect":"South","type":"4 beds, 1CP"},
    {"suburb":"Mosman","address":"41 Cowles Road, Mosman","auction":"AUC 21st Feb @ 12.00pm","guide":"$5,000,000","land":492,"aspect":"East","type":"5 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"125 Ourimbah Road, Mosman","auction":"For Sale (Guide price)","guide":"$5,900,000","land":481,"aspect":"North","type":"5 beds, 5 baths, 2CP"},
    {"suburb":"Mosman","address":"36 Mandolong Road, Mosman","auction":"AUC 26th Feb @ 5.00pm","guide":"$7,500,000","land":512,"aspect":"North","type":"3 beds, 2 baths, 1 CS"},
    {"suburb":"Mosman","address":"53 Clanalpine Street, Mosman","auction":"AUC 28th Feb @ 11.00am","guide":"$8,500,000","land":511,"aspect":"SE","type":"5 beds, 5 baths, DLUG + 2CS"},
    {"suburb":"Mosman","address":"2 Morella Road, Mosman","auction":"For Sale (Guide price)","guide":"$9,500,000","land":594,"aspect":"NE","type":"5 beds, 4 baths, DLUG + 2CS"},
    {"suburb":"Mosman","address":"34 Rickard Avenue, Mosman","auction":"For Sale (Guide price)","guide":"$10,000,000","land":721,"aspect":"NW","type":"7 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"16 Lower Boyle Street, Mosman","auction":"AUC 26th Feb @ 5.00pm","guide":"$13,000,000","land":619,"aspect":"South","type":"5 beds, 3 baths, DLUG + 2CS"},
    {"suburb":"Mosman","address":"17 Morella Road, Mosman","auction":"For Sale (Guide price)","guide":"$23,000,000","land":961,"aspect":"NE","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"20 The Grove, Mosman","auction":"For Sale (Guide price)","guide":"$25,000,000","land":720,"aspect":"West","type":"6 beds, 5 baths, 4 x Garage"},
    {"suburb":"Naremburn","address":"26 Olympia Road, Naremburn","auction":"For Sale (Guide price)","guide":"$3,500,000","land":563,"aspect":"South","type":"3 beds, 2 baths, Study (duplex)"},
    {"suburb":"Neutral Bay","address":"294 Falcon Street, Neutral Bay","auction":"For Sale (Guide price)","guide":"$1,800,000","land":198,"aspect":"North","type":"3 beds, 2 baths"},
    {"suburb":"Neutral Bay","address":"296 Falcon Street, Neutral Bay","auction":"For Sale (Guide price)","guide":"$1,900,000","land":200,"aspect":"North","type":"3 beds, 2 baths"},
    {"suburb":"Neutral Bay","address":"31 Spruson Street, Neutral Bay","auction":"AUC 28th Feb @ 9.00am","guide":"$3,500,000","land":379,"aspect":"East","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Neutral Bay","address":"44 Raymond Road, Neutral Bay","auction":"AUC 28th Feb @ 5.00pm","guide":"$4,500,000","land":212,"aspect":"West","type":"3 beds, 2 baths, 1CS"},
    {"suburb":"North Sydney","address":"35 Whaling Road, North Sydney","auction":"AUC 26th Feb @ 5.00pm","guide":"$3,000,000","land":242,"aspect":"South","type":"3 beds, 2 baths, 1CS"},
    {"suburb":"North Sydney","address":"13 Bank Street, North Sydney","auction":"AUC 28th Feb @ 12.00pm","guide":"$3,450,000","land":348,"aspect":"East","type":"3 beds, 2 baths, 1CP"},
    {"suburb":"North Sydney","address":"59 Neutral Street, North Sydney","auction":"For Sale (Guide price)","guide":"$4,500,000","land":234,"aspect":"East","type":"5 beds, 3 baths, LUG + 1CS"},
    {"suburb":"Northbridge","address":"6 The Outpost, Northbridge","auction":"AUC 28th Feb @ 12.30pm","guide":"$3,800,000","land":632,"aspect":"West","type":"3 beds, 2 baths, DLUG + 1CS"},
    {"suburb":"Northbridge","address":"5 Pyalla Street, Northbridge","auction":"AUC 4th Mar @ 6.00pm","guide":"$4,100,000","land":454,"aspect":"East","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Northbridge","address":"51 Baroona Road, Northbridge","auction":"AUC 21st Feb @ 9.00am","guide":"$4,500,000","land":645,"aspect":"North","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Northbridge","address":"70 Minnamurra Road, Northbridge","auction":"AUC 28th Feb @ 3.00pm","guide":"$5,000,000","land":670,"aspect":"South","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Northbridge","address":"28 Baringa Road, Northbridge","auction":"AUC 28th Feb @ 12.30pm","guide":"$7,500,000","land":650,"aspect":"South","type":"5 beds, 3 baths, LUG"},
    {"suburb":"Willoughby","address":"646 Willoughby Road, Willoughby","auction":"AUC 7th Mar @ 9.30am","guide":"$2,000,000","land":325,"aspect":"West","type":"2 beds, 1 bath, 1CS"},
    {"suburb":"Willoughby","address":"21 Oakville Road, Willoughby","auction":"AUC 28th Feb @ 6.00pm","guide":"$2,800,000","land":361,"aspect":"North","type":"3 beds, 2 baths, DLUG"},
    {"suburb":"Willoughby","address":"1c Mabel Street, Willoughby","auction":"AUC 28th Feb @ 11.30am","guide":"$3,200,000","land":809,"aspect":"East","type":"5 beds, 3 baths, DLUG (semi)"},
    {"suburb":"Willoughby","address":"63 Edinburgh Road, Willoughby","auction":"AUC 28th Feb @ 1.30pm","guide":"$3,200,000","land":525,"aspect":"North","type":"4 beds, 3 baths, 3CS"},
    {"suburb":"Willoughby","address":"30 Hector Road, Willoughby","auction":"AUC 21st Feb @ 3.30pm","guide":"$3,500,000","land":557,"aspect":"North","type":"3 beds, 2 baths, LUG + 3CS"},
    {"suburb":"Willoughby","address":"23 Wallace Street, Willoughby","auction":"AUC 28th Feb @ 9.30am","guide":"$3,900,000","land":468,"aspect":"East","type":"4 beds, 1 bath, 1CS"},
    {"suburb":"Willoughby","address":"22 Rosewall Street, Willoughby","auction":"AUC 28th Feb @ 3.30pm","guide":"$3,900,000","land":626,"aspect":"SE","type":"4 beds, 2 baths, LUG + 3CS"},
    {"suburb":"Willoughby","address":"45 Tulloh Street, Willoughby","auction":"AUC 28th Feb @ 1.30pm","guide":"$4,000,000","land":373,"aspect":"East","type":"4 beds, 2 baths, LUG"},
    {"suburb":"Willoughby","address":"101 Sydney Street, Willoughby","auction":"AUC 28th Feb @ 11.15am","guide":"$4,000,000","land":676,"aspect":"SE","type":"4 beds, 3 baths, LUG"},
    {"suburb":"Willoughby","address":"6 Second Avenue, Willoughby","auction":"For Sale (Price Guide)","guide":"$4,100,000","land":1349,"aspect":"SW","type":"5 beds, 6 baths, DLUG"},
    {"suburb":"Willoughby","address":"16 Mabel Street, Willoughby","auction":"AUC 28th Feb @ 10.00am","guide":"$4,800,000","land":689,"aspect":"West","type":"5 beds, 2 baths, 1CP + 2CS"},
    {"suburb":"Willoughby","address":"24 Cobar Street, Willoughby","auction":"AUC 28th Feb @ 9.45am","guide":"$5,100,000","land":697,"aspect":"South","type":"5 beds, 2 bath, DLUG"},
    {"suburb":"Willoughby","address":"7 Remuera Street, Willoughby","auction":"AUC 28th Feb @ 9.00am","guide":"$6,000,000","land":607,"aspect":"East","type":"5 beds, 4 baths, tandem DLUG + 1CS"},
    {"suburb":"Willoughby","address":"3 Owen Street, Willoughby","auction":"AUC 7th Mar @ 9.00am","guide":"$6,500,000","land":558,"aspect":"North","type":"5 beds, 4 baths, DLUG"},
]

SOLD = [
    {"method":"Post Auction","address":"22 Shepherd Road, Artarmon","dateSold":"21-Jan-26","guidePrice":"$2,500,000","soldPrice":"$2,800,000","diff":"$300,000","pctChange":"12.00%"},
    {"method":"Private Treaty","address":"3 D'Aram Street, Hunters Hill","dateSold":"22-Jan-26","guidePrice":"$4,365,000","soldPrice":"$4,365,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"269 Claire Street, Naremburn","dateSold":"26-Jan-26","guidePrice":"$3,200,000","soldPrice":"$3,338,000","diff":"$138,000","pctChange":"4.31%"},
    {"method":"Post Auction","address":"38 Second Avenue, Willoughby","dateSold":"25-Jan-26","guidePrice":"$3,100,000","soldPrice":"$2,750,000","diff":"-$350,000","pctChange":"-11.29%"},
    {"method":"Pre-Auction","address":"40 High Street, Willoughby","dateSold":"28-Jan-26","guidePrice":"$2,700,000","soldPrice":"$3,000,000","diff":"$300,000","pctChange":"11.11%"},
]

def normalize_addr(addr):
    a = addr.lower()
    a = re.sub(r',?\s*(nsw|new south wales|australia)\s*', '', a)
    a = re.sub(r'\bstreet\b', 'st', a)
    a = re.sub(r'\broad\b', 'rd', a)
    a = re.sub(r'\bavenue\b', 'ave', a)
    a = re.sub(r'\bdrive\b', 'dr', a)
    a = re.sub(r'\bplace\b', 'pl', a)
    a = re.sub(r'\blane\b', 'ln', a)
    a = re.sub(r'\bcrescent\b', 'cres', a)
    a = re.sub(r'\bcircuit\b', 'cct', a)
    a = re.sub(r'\bparade\b', 'pde', a)
    a = re.sub(r'\bcourt\b', 'ct', a)
    a = re.sub(r'\bclose\b', 'cl', a)
    a = re.sub(r'\bterrace\b', 'tce', a)
    a = re.sub(r'\bboulevard\b', 'blvd', a)
    a = re.sub(r'\bway\b', 'wy', a)
    a = re.sub(r'[^a-z0-9]', '', a)
    return a

def main():
    APP_PATH = str(Path(__file__).resolve().parent.parent / 'mazar_martin_app.html')

    with open(APP_PATH) as f:
        html = f.read()

    # Generate JavaScript to inject into washPropingData or as a separate init
    # We'll create a JS block that runs after washPropingData to fill in spreadsheet data

    js_data = json.dumps(NEW_LISTINGS)
    js_sold = json.dumps(SOLD)

    # Build the JS injection code
    js_code = f"""
// ── Spreadsheet data injection (Mazar Martin report) ──
function _injectSpreadsheetData() {{
  const listings = {js_data};
  const soldData = {js_sold};

  // Build normalized lookup for For Sale
  const fsMap = {{}};
  (D.sampleListings||[]).forEach(l => {{
    const k = _normalizeAddr(l.address);
    if (k) fsMap[k] = l;
  }});

  // Build normalized lookup for Sold
  const soldMap = {{}};
  (D.soldListings||[]).forEach(l => {{
    const k = _normalizeAddr(l.address);
    if (k) soldMap[k] = l;
  }});

  let fsMatched = 0, soldMatched = 0;

  // Match new listings → For Sale
  for (const nl of listings) {{
    const k = _normalizeAddr(nl.address);
    const match = fsMap[k];
    if (match) {{
      if (nl.guide && !match.guidePrice) match.guidePrice = nl.guide;
      if (nl.land && (!match.landSize || match.landSize === 0)) match.landSize = nl.land;
      if (nl.aspect) match.aspect = nl.aspect;
      if (nl.auction && nl.auction.startsWith('AUC')) match.auctionDetail = nl.auction;
      if (nl.type) match.propertyDetail = nl.type;
      fsMatched++;
    }}
  }}

  // Match sold data → Sold listings
  for (const s of soldData) {{
    const k = _normalizeAddr(s.address);
    const match = soldMap[k];
    if (match) {{
      if (s.soldPrice && (!match.soldPrice || match.soldPrice === 'Price Withheld')) match.soldPrice = s.soldPrice;
      if (s.guidePrice && !match.guidePrice) match.guidePrice = s.guidePrice;
      if (s.method && !match.method) match.method = s.method;
      soldMatched++;
    }}
  }}

  console.log('Spreadsheet injection: ' + fsMatched + ' For Sale matched, ' + soldMatched + ' Sold matched');
}}
"""

    # Find where to insert - right after washPropingData function and before window.addEventListener
    marker = "window.addEventListener('load', () => {"
    idx = html.find(marker)
    if idx == -1:
        print("ERROR: Could not find window load marker")
        return

    # Insert the function before the load listener
    html = html[:idx] + js_code + '\n' + html[idx:]

    # Add call to _injectSpreadsheetData inside the load listener, after washPropingData
    old_load = "window.addEventListener('load', () => {\n  washPropingData();"
    new_load = "window.addEventListener('load', () => {\n  washPropingData();\n  _injectSpreadsheetData();"
    html = html.replace(old_load, new_load)

    # Write updated file
    with open(APP_PATH, 'w') as f:
        f.write(html)

    # Copy to deploy + preview
    for path in [str(Path(__file__).resolve().parent.parent.parent / 'index.html'), '/tmp/mm_preview/mazar_martin_app.html']:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(html)
            print(f"Updated {path}")
        except Exception as e:
            print(f"Warning: {path}: {e}")

    print(f"\nInjected {len(NEW_LISTINGS)} listing records and {len(SOLD)} sold records")
    print(f"App file size: {len(html):,} bytes")

if __name__ == '__main__':
    main()
