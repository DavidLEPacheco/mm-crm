#!/usr/bin/env python3
"""Inject comprehensive spreadsheet data (5 sheets) into mazar_martin_app.html.
Replaces the previous spreadsheet_data.py injection with much more data."""
import json, re, os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 1 - New Listings (52) + Sold (10)
# ═══════════════════════════════════════════════════════════════════════════
SHEET1_LISTINGS = [
    {"suburb":"Artarmon","address":"93 Artarmon Road, Artarmon","auction":"AUC 28th Feb @ 11:15am","guide":"$3,300,000","land":696,"aspect":"North","type":"4 beds, 2 baths, LUG + 2CS"},
    {"suburb":"Castlecrag","address":"14 Sugarloaf Crescent, Castlecrag","auction":"AUC 7th Mar @ 11.15am","guide":"$3,500,000","land":613,"aspect":"South","type":"4 beds, 3 baths, 1CP + 1CS"},
    {"suburb":"Castlecrag","address":"12 The Bulwark, Castlecrag","auction":"AUC 5th Mar @ 5.00pm","guide":"$3,500,000","land":904,"aspect":"West","type":"5 beds, 4 baths, DLUG + 4CS"},
    {"suburb":"Castlecrag","address":"12 Sunnyside Crescent, Castlecrag","auction":"AUC 4th Mar @ 6.00pm","guide":"$4,800,000","land":594,"aspect":"SW","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Castle Cove","address":"48 Neerim Road, Castle Cove","auction":"AUC 7th Mar @ 9.30am","guide":"$4,000,000","land":759,"aspect":"South","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Chatswood","address":"12a Range Street, Chatswood","auction":"AUC 28th Feb @ 3.00pm","guide":"$1,900,000","land":392,"aspect":"West","type":"3 beds, 2 baths, 1CP + 1CS"},
    {"suburb":"Chatswood","address":"33 Royal Street, Chatswood","auction":"AUC 28th Feb @ 1.30pm","guide":"$2,850,000","land":372,"aspect":"East","type":"3 beds, 1 baths"},
    {"suburb":"Chatswood","address":"43 Beaconsfield Road, Chatswood","auction":"AUC 28th Feb @ 9.00am","guide":"$3,200,000","land":875,"aspect":"NE","type":"4 beds, 2 baths, 2CS"},
    {"suburb":"Chatswood","address":"12 Beresford Avenue, Chatswood","auction":"AUC 28th Feb @ 12.00pm","guide":"$3,600,000","land":556,"aspect":"SE","type":"4 beds, 2 baths, 2 CS"},
    {"suburb":"Chatswood","address":"10 Beresford Avenue, Chatswood","auction":"AUC 7th Mar @ NA","guide":"$3,800,000","land":575,"aspect":"South","type":"5 beds, 2 baths, LUG + 1CS"},
    {"suburb":"Chatswood","address":"48 Robinson Street, Chatswood","auction":"AUC 11th Mar @ 11.00am","guide":"$3,900,000","land":384,"aspect":"West","type":"4 beds, 2 baths, 2CS"},
    {"suburb":"Chatswood","address":"10 Ivy Street, Chatswood","auction":"AUC 7th Mar @ 3.30pm","guide":"$4,000,000","land":665,"aspect":"North","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Chatswood","address":"31 Royal Street, Chatswood","auction":"AUC 28th Feb @ 10.30am","guide":"$4,200,000","land":367,"aspect":"NE","type":"5 beds, 3 baths, 2CP"},
    {"suburb":"Chatswood","address":"22c Greville Street, Chatswood","auction":"AUC 7th Mar @ 1.30pm","guide":"$4,500,000","land":540,"aspect":"West","type":"5 beds, 3 baths, 1CP"},
    {"suburb":"Chatswood","address":"20 Tulip Street, Chatswood","auction":"For Sale (Guide price)","guide":"$9,200,000","land":1290,"aspect":"SE","type":"7 beds, 3 baths, LUG + 2CP + 1CS"},
    {"suburb":"Cremorne","address":"129 Milson Road, Cremorne Point","auction":"AUC 5th Mar @ 5.00pm","guide":"$8,000,000","land":645,"aspect":"West","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Crows Nest","address":"76 Falcon Street, Crows Nest","auction":"AUC 7th Mar @ 3.00pm","guide":"$2,200,000","land":252,"aspect":"North","type":"2 beds, 1 bath, 4CS"},
    {"suburb":"Middle Cove","address":"13 The Quarterdeck, Middle Cove","auction":"For Sale (Price guide)","guide":"$14,500,000","land":1797,"aspect":"East","type":"5 beds, 4 baths, DLUG"},
    {"suburb":"Mosman","address":"89 Spit Road, Mosman","auction":"AUC 3rd Mar @ 6.00pm","guide":"$2,500,000","land":250,"aspect":"East","type":"3 beds, 2 baths, Study (semi)"},
    {"suburb":"Mosman","address":"12 Orlando Avenue, Mosman","auction":"For Sale (Guide price)","guide":"$2,800,000","land":221,"aspect":"West","type":"2 beds, 1 bath, 1 CP (semi)"},
    {"suburb":"Mosman","address":"8A Prince Street, Mosman","auction":"AUC 28th Feb @ 3.00pm","guide":"$3,600,000","land":258,"aspect":"South","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"31 Ryrie Street, Mosman","auction":"AUC 7th Mar @ 9.00am","guide":"$3,800,000","land":624,"aspect":"East","type":"5 beds, 3 baths, LUG + 1CS"},
    {"suburb":"Mosman","address":"55C Belmont Road, Mosman","auction":"For Sale (Guide price)","guide":"$3,950,000","land":207,"aspect":"North","type":"3 beds, 2 baths, 2CP"},
    {"suburb":"Mosman","address":"63 Rangers Avenue, Mosman","auction":"AUC 7th Mar @ 9.00am","guide":"$4,500,000","land":455,"aspect":"North","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"21A Noble Street, Mosman","auction":"AUC 26th Feb @ 5.00pm","guide":"$5,000,000","land":887,"aspect":"North","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"171 Spit Road, Mosman","auction":"For Sale (Guide price)","guide":"$5,000,000","land":645,"aspect":"East","type":"5 beds, 4 baths, 4 x LUG"},
    {"suburb":"Mosman","address":"18 Melrose Street, Mosman","auction":"AUC 7th Mar @ 9.00am","guide":"$5,500,000","land":532,"aspect":"South","type":"6 beds, 3 baths, LUG + 1CS"},
    {"suburb":"Mosman","address":"8A Bickell Road, Mosman","auction":"AUC 6th Mar @ 4.00pm","guide":"$5,500,000","land":746,"aspect":"South","type":"5 beds, 3 baths, 1CP + 3CS"},
    {"suburb":"Mosman","address":"51 Prince Street, Mosman","auction":"AUC 7th Mar @ 9.00am","guide":"$6,500,000","land":520,"aspect":"North","type":"5 beds, 2 baths, 2CP"},
    {"suburb":"Mosman","address":"5 Sirius Cove Road, Mosman","auction":"For Sale (Guide price)","guide":"$6,500,000","land":653,"aspect":"East","type":"5 beds, 2 baths, LUG + LUG"},
    {"suburb":"Mosman","address":"13 Cardinal Street, Mosman","auction":"For Sale (Guide price)","guide":"$6,500,000","land":556,"aspect":"East","type":"5 beds, 3 baths, 1 CP"},
    {"suburb":"Mosman","address":"Lot 3/10-12 Bay Street, Mosman","auction":"AUC 12th Mar @ 5.00pm","guide":"$6,500,000","land":930,"aspect":"West","type":"Residential Land"},
    {"suburb":"Mosman","address":"19 Wyong Road, Mosman","auction":"AUC 5th Mar @ 5.00pm","guide":"$7,800,000","land":999,"aspect":"NE","type":"4 beds, 3 baths, LUG"},
    {"suburb":"Mosman","address":"55 Wolseley Road, Mosman","auction":"For Sale (Guide price)","guide":"$8,000,000","land":771,"aspect":"North","type":"4 beds, 3 baths, 2CP"},
    {"suburb":"Mosman","address":"40 Middle Head Road, Mosman","auction":"AUC 5th Mar @ 5.00pm","guide":"$10,700,000","land":1107,"aspect":"South","type":"5 beds, 4 baths, 2CS"},
    {"suburb":"Mosman","address":"4 Curlew Camp Road, Mosman","auction":"For Sale (Guide price)","guide":"$11,800,000","land":991,"aspect":"NW","type":"5 beds, 3 baths, TLUG"},
    {"suburb":"Mosman","address":"2a Hampden Street, Mosman","auction":"AUC 12th Mar @ 5.00pm","guide":"$12,000,000","land":674,"aspect":"SE","type":"5 beds, 4 baths, DLUG + 2CS"},
    {"suburb":"Mosman","address":"3 Methuen Avenue, Mosman","auction":"AUC 12th Mar @ 5.00pm","guide":"$20,000,000","land":555,"aspect":"East","type":"5 beds, 4 baths, DLUG + 2CS"},
    {"suburb":"Mosman","address":"26 Kirkoswald Avenue, Mosman","auction":"For Sale (Guide price)","guide":"$12,500,000","land":461,"aspect":"North","type":"4 beds, 3 baths, 2CP"},
    {"suburb":"Mosman","address":"5 Botanic Road, Mosman","auction":"EOI 3rd Mar @ 1.00pm","guide":"$12,500,000","land":437,"aspect":"East","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"28 David Street, Mosman","auction":"AUC 12th Mar @ 5.00pm","guide":"$18,000,000","land":1150,"aspect":"South","type":"5 beds, 5 baths, 2 CP + 1 CS"},
    {"suburb":"Mosman","address":"Lot 2/10 Bay Street, Mosman","auction":"For Sale (Guide price)","guide":"$18,500,000","land":2610,"aspect":"West","type":"Residential Land"},
    {"suburb":"Naremburn","address":"19 Plunkett Street, Naremburn","auction":"AUC 28th Feb @ 11.15am","guide":"$2,850,000","land":215,"aspect":"East","type":"3 beds, 2 baths, 1CS"},
    {"suburb":"Neutral Bay","address":"10 Phillips Street, Neutral Bay","auction":"AUC 28th Feb @ 11.00am","guide":"$3,800,000","land":373,"aspect":"North","type":"4 beds, 2 baths"},
    {"suburb":"Northbridge","address":"4 Wollombi Road, Northbridge","auction":"AUC 28th Feb @ 10.00am","guide":"$6,700,000","land":708,"aspect":"West","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Northbridge","address":"12 Tenilba Road, Northbridge","auction":"AUC 28th Feb @ 1.30pm","guide":"$6,800,000","land":760,"aspect":"South","type":"5 beds, 4 baths, DLUG"},
    {"suburb":"Willoughby","address":"33 Penhurst Street, Willoughby","auction":"AUC 28th Feb @ 4.15pm","guide":"$2,000,000","land":232,"aspect":"East","type":"2 beds, 1 bath, DLUG"},
    {"suburb":"Willoughby","address":"265A High Street, Willoughby","auction":"AUC 28th Feb @ 3.45pm","guide":"$2,800,000","land":433,"aspect":"East","type":"3 beds, 2 baths, 2CP"},
    {"suburb":"Willoughby","address":"32 Hector Road, Willoughby","auction":"AUC 28th Feb @ 3.45pm","guide":"$2,800,000","land":278,"aspect":"North","type":"3 beds, 1 bath, 1CP"},
    {"suburb":"Willoughby","address":"56 Tulloh Street, Willoughby","auction":"AUC 28th Feb @ 9.00am","guide":"$3,600,000","land":342,"aspect":"NW","type":"4 beds, 2 baths, 1CP + 1CS (semi)"},
    {"suburb":"Willoughby","address":"51 McClelland Street, Willoughby","auction":"AUC 7th Mar @ 12.00pm","guide":"$4,300,000","land":545,"aspect":"North","type":"4 beds, 2 baths, LUG + 2CP"},
    {"suburb":"Willoughby","address":"143 High Street, Willoughby","auction":"AUC 5th Mar @ 6.00pm","guide":"$5,600,000","land":778,"aspect":"East","type":"5 beds, 2 baths, 2CS"},
]

SHEET1_SOLD = [
    {"method":"At Auction","address":"17 Moola Parade, Chatswood","dateSold":"04-Feb-26","guidePrice":"$2,800,000","soldPrice":"$3,300,000","diff":"$500,000","pctChange":"17.86%"},
    {"method":"At Auction","address":"71 Beaconsfield Road, Chatswood","dateSold":"05-Feb-26","guidePrice":"$2,300,000","soldPrice":"$3,180,000","diff":"$880,000","pctChange":"38.26%"},
    {"method":"At Auction","address":"15 Hawthorne Avenue, Chatswood","dateSold":"31-Jan-26","guidePrice":"$2,600,000","soldPrice":"$2,650,000","diff":"$50,000","pctChange":"1.92%"},
    {"method":"Pre-Auction","address":"12 Figtree Road, Hunters Hill","dateSold":"30-Jan-26","guidePrice":"$2,700,000","soldPrice":"$2,975,000","diff":"$275,000","pctChange":"10.19%"},
    {"method":"Pre-Auction","address":"1 Milling Street, Hunters Hill","dateSold":"02-Feb-26","guidePrice":"$3,500,000","soldPrice":"$3,800,000","diff":"$300,000","pctChange":"8.57%"},
    {"method":"Pre-Auction","address":"19 Bay View Street, Lavender Bay","dateSold":"04-Feb-26","guidePrice":"$5,250,000","soldPrice":"$6,200,000","diff":"$950,000","pctChange":"18.10%"},
    {"method":"Post Auction","address":"51 Hale Road, Mosman","dateSold":"04-Feb-26","guidePrice":"$3,600,000","soldPrice":"$3,215,000","diff":"-$385,000","pctChange":"-10.69%"},
    {"method":"Pre-Auction","address":"254 Willoughby Road, Naremburn","dateSold":"03-Feb-26","guidePrice":"$3,300,000","soldPrice":"$3,700,000","diff":"$400,000","pctChange":"12.12%"},
    {"method":"Private Treaty","address":"26 Station Street, Naremburn","dateSold":"05-Feb-26","guidePrice":"$3,800,000","soldPrice":"$4,080,000","diff":"$280,000","pctChange":"7.37%"},
    {"method":"Pre-Auction","address":"204 Sydney Street, Willoughby","dateSold":"03-Feb-26","guidePrice":"$2,700,000","soldPrice":"$2,725,000","diff":"$25,000","pctChange":"0.93%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 2 - New Listings (39) + Sold (24)
# ═══════════════════════════════════════════════════════════════════════════
SHEET2_LISTINGS = [
    {"suburb":"Artarmon","address":"24 Robert Street, Artarmon","auction":"28-Mar-26 13:00","guide":"$2,300,000","land":325,"aspect":"SW","type":"3 beds, 1 bath, 1 CP (semi)"},
    {"suburb":"Artarmon","address":"4 Cameron Avenue, Artarmon","auction":"29-Mar-26 12:00","guide":"$3,600,000","land":632,"aspect":"South","type":"4 beds, 1 bath, 1CS"},
    {"suburb":"Artarmon","address":"16 Tindale Road, Artarmon","auction":"28-Mar-26 14:00","guide":"$4,850,000","land":967,"aspect":"West","type":"5 beds, 4 baths, 1CS"},
    {"suburb":"Cammeray","address":"3 Arkland Street, Cammeray","auction":"01-Apr-26 17:00","guide":"$4,400,000","land":423,"aspect":"East","type":"4 beds, 2 baths"},
    {"suburb":"Castlecrag","address":"11a The Bulwark, Castlecrag","auction":"For Sale (Guide price)","guide":"$4,000,000","land":727,"aspect":"North","type":"4 beds, 3 baths, LUG + 1CP"},
    {"suburb":"Castle Cove","address":"353 Eastern Valley Way, Castle Cove","auction":"28-Mar-26 17:15","guide":"$3,200,000","land":383,"aspect":"North","type":"4 beds, 4 baths, LUG"},
    {"suburb":"Castle Cove","address":"8 Padulla Place, Castle Cove","auction":"01-Apr-26 18:00","guide":"$4,000,000","land":759,"aspect":"SW","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Castle Cove","address":"21 Allambie Road, Castle Cove","auction":"21-Mar-26 15:00","guide":"$5,000,000","land":860,"aspect":"South","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Chatswood","address":"178 Fullers Road, Chatswood","auction":"28-Mar-26 15:45","guide":"$2,500,000","land":695.6,"aspect":"South","type":"4 beds, 2 baths, 2CP"},
    {"suburb":"Chatswood","address":"1 Harnett Place, Chatswood","auction":"28-Mar-26 10:00","guide":"$2,900,000","land":658,"aspect":"South","type":"4 beds, 2 baths, DLUG + 1CP"},
    {"suburb":"Chatswood","address":"22 West Parade, Chatswood","auction":"28-Mar-26 17:15","guide":"$4,650,000","land":565,"aspect":"SW","type":"6 beds, 4 baths, DLUG"},
    {"suburb":"Crows Nest","address":"162 West Street, Crows Nest","auction":"28-Mar-26 15:00","guide":"$2,500,000","land":133,"aspect":"West","type":"4 beds, 1 bath, LUG"},
    {"suburb":"Crows Nest","address":"218 West Street, Crows Nest","auction":"28-Mar-26 15:00","guide":"$2,500,000","land":139,"aspect":"West","type":"4 beds, 1 bath, LUG"},
    {"suburb":"Crows Nest","address":"66 Hayberry Street, Crows Nest","auction":"28-Mar-26 10:00","guide":"$2,900,000","land":243,"aspect":"North","type":"3 beds, 2 baths, LUG + 1CS"},
    {"suburb":"Hunters Hill","address":"6 Moorefield Avenue, Hunters Hill","auction":"28-Mar-26 14:15","guide":"$3,250,000","land":461,"aspect":"West","type":"4 beds, 2 baths, LUG"},
    {"suburb":"Hunters Hill","address":"10 Herberton Avenue, Hunters Hill","auction":"01-Apr-26 18:00","guide":"$4,750,000","land":651,"aspect":"West","type":"5 beds, 3 baths, LUG"},
    {"suburb":"Hunters Hill","address":"9 Vernon Street, Hunters Hill","auction":"28-Mar-26 10:30","guide":"$8,500,000","land":538,"aspect":"South","type":"5 beds, 4 baths, 4 x LUG"},
    {"suburb":"McMahons Point","address":"30 Victoria Street, McMahons Point","auction":"26-Mar-26 17:00","guide":"$3,470,000","land":145,"aspect":"North","type":"3 beds, 2 baths"},
    {"suburb":"Mosman","address":"3 Ourimbah Road, Mosman","auction":"28-Mar-26 09:00","guide":"$3,000,000","land":278,"aspect":"North","type":"3 beds, 1 bath, 1 CS (semi)"},
    {"suburb":"Mosman","address":"3 Marsala Street, Mosman","auction":"28-Mar-26 11:00","guide":"$5,000,000","land":705,"aspect":"West","type":"4 beds, 3 baths, LUG"},
    {"suburb":"Mosman","address":"34 Somerset Street, Mosman","auction":"28-Mar-26 11:00","guide":"$5,800,000","land":557,"aspect":"NW","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"5 Cabban Street, Mosman","auction":"For Sale (Guide price)","guide":"$5,900,000","land":455,"aspect":"South","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"6 Wolseley Road, Mosman","auction":"01-Apr-26 17:00","guide":"$6,000,000","land":436,"aspect":"South","type":"4 beds, 2 baths, DLUG"},
    {"suburb":"Mosman","address":"36 Rickard Avenue, Mosman","auction":"01-Apr-26 17:00","guide":"$6,500,000","land":1035,"aspect":"NW","type":"5 beds, 4 baths, 1CP"},
    {"suburb":"Mosman","address":"11 Cobbitree Street, Mosman","auction":"01-Apr-26 17:00","guide":"$7,750,000","land":670,"aspect":"North","type":"5 beds, 4 baths, DLUG"},
    {"suburb":"Mosman","address":"26 David Street, Mosman","auction":"01-Apr-26 17:00","guide":"$9,000,000","land":766,"aspect":"South","type":"5 beds, 3 baths, 2CP"},
    {"suburb":"Mosman","address":"15 - 17 Carrington Avenue, Mosman","auction":"For Sale (Guide price)","guide":"$43,000,000","land":2462,"aspect":"South","type":"5 beds, 5 baths, DLUG"},
    {"suburb":"Naremburn","address":"51 Waters Road, Naremburn","auction":"For Sale (Guide price)","guide":"$2,500,000","land":252,"aspect":"West","type":"3 beds, 2 baths, 1CP"},
    {"suburb":"Neutral Bay","address":"7 Yeo Street, Neutral Bay","auction":"01-Apr-26 17:00","guide":"$2,800,000","land":434,"aspect":"North","type":"3 beds, 1 bath, 1CS (semi)"},
    {"suburb":"Neutral Bay","address":"62 Ben Boyd Road, Neutral Bay","auction":"28-Mar-26 12:30","guide":"$2,900,000","land":331,"aspect":"South","type":"4 beds, 2 baths"},
    {"suburb":"Neutral Bay","address":"18 Yeo Street, Neutral Bay","auction":"24-Mar-26 17:00","guide":"$3,600,000","land":334,"aspect":"North","type":"3 beds, 2 baths, 1CS (semi)"},
    {"suburb":"North Sydney","address":"24 Lord Street, North Sydney","auction":"28-Mar-26 09:00","guide":"$4,000,000","land":341,"aspect":"North","type":"4 beds, 3 baths"},
    {"suburb":"Northbridge","address":"235 Sailors Bay Road, Northbridge","auction":"28-Mar-26 11:15","guide":"$3,800,000","land":462,"aspect":"North","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"Northbridge","address":"72 Kameruka Road, Northbridge","auction":"28-Mar-26 11:15","guide":"$4,200,000","land":752,"aspect":"SW","type":"3 beds, 1 bath, 2CP"},
    {"suburb":"Northbridge","address":"2 Miowera Road, Northbridge","auction":"28-Mar-26 15:40","guide":"$7,000,000","land":573,"aspect":"South","type":"5 beds, 2 baths, 4 x LUG"},
    {"suburb":"Willoughby","address":"2 Ann Street, Willoughby","auction":"28-Mar-26 09:00","guide":"$2,350,000","land":411,"aspect":"West","type":"2 beds, 1 bath, 2CS"},
    {"suburb":"Willoughby","address":"31 Mabel Street, Willoughby","auction":"28-Mar-26 15:45","guide":"$3,800,000","land":556,"aspect":"East","type":"4 beds, 2 baths, 2CS"},
    {"suburb":"Willoughby","address":"100 Warrane Road, Willoughby","auction":"28-Mar-26 09:45","guide":"$4,300,000","land":734,"aspect":"West","type":"3 beds, 1 bath, LUG"},
    {"suburb":"Willoughby","address":"94 Laurel Street, Willoughby","auction":"28-Mar-26 09:00","guide":"$4,800,000","land":487,"aspect":"South","type":"5 beds, 2 baths, 1CS"},
]

SHEET2_SOLD = [
    {"method":"Pre-Auction","address":"48 Neerim Road, Castle Cove","dateSold":"05-Mar-26","guidePrice":"$4,000,000","soldPrice":"$4,200,000","diff":"$200,000","pctChange":"5.00%"},
    {"method":"Post Auction","address":"1 Willowie Road, Castle Cove","dateSold":"06-Mar-26","guidePrice":"$4,000,000","soldPrice":"$4,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"At Auction","address":"9A Alleyne Street, Chatswood","dateSold":"28-Feb-26","guidePrice":"$4,000,000","soldPrice":"$4,205,000","diff":"$205,000","pctChange":"5.13%"},
    {"method":"At Auction","address":"10 Beresford Avenue, Chatswood","dateSold":"01-Mar-26","guidePrice":"$3,800,000","soldPrice":"$4,288,000","diff":"$488,000","pctChange":"12.84%"},
    {"method":"Post Auction","address":"8A Wood Street, Chatswood","dateSold":"03-Mar-26","guidePrice":"$2,200,000","soldPrice":"$2,250,000","diff":"$50,000","pctChange":"2.27%"},
    {"method":"Pre-Auction","address":"362 Penshurst Street, Chatswood","dateSold":"03-Mar-26","guidePrice":"$3,500,000","soldPrice":"$3,770,000","diff":"$270,000","pctChange":"7.71%"},
    {"method":"Post Auction","address":"74 Macpherson Street, Cremorne","dateSold":"05-Mar-26","guidePrice":"$4,650,000","soldPrice":"$4,650,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Post Auction","address":"33 Spofforth Street, Mosman","dateSold":"02-Mar-26","guidePrice":"$4,700,000","soldPrice":"$5,075,000","diff":"$375,000","pctChange":"7.98%"},
    {"method":"Pre-Auction","address":"51 Prince Street, Mosman","dateSold":"02-Mar-26","guidePrice":"$7,000,000","soldPrice":"$6,600,000","diff":"-$400,000","pctChange":"-5.71%"},
    {"method":"Pre-Auction","address":"19 Wyong Road, Mosman","dateSold":"04-Mar-26","guidePrice":"$7,800,000","soldPrice":"$8,085,000","diff":"$285,000","pctChange":"3.65%"},
    {"method":"Private Treaty","address":"55 Wolseley Road, Mosman","dateSold":"05-Mar-26","guidePrice":"$8,000,000","soldPrice":"$7,430,000","diff":"-$570,000","pctChange":"-7.13%"},
    {"method":"Pre-Auction","address":"14 Kirkoswald Avenue, Mosman","dateSold":"05-Mar-26","guidePrice":"$8,500,000","soldPrice":"$8,510,000","diff":"$10,000","pctChange":"0.12%"},
    {"method":"Pre-Auction","address":"32 Lang Street, Mosman","dateSold":"06-Mar-26","guidePrice":"$4,000,000","soldPrice":"$3,900,000","diff":"-$100,000","pctChange":"-2.50%"},
    {"method":"Pre-Auction","address":"33 Clanalpine Street, Mosman","dateSold":"06-Mar-26","guidePrice":"$6,500,000","soldPrice":"$6,675,000","diff":"$175,000","pctChange":"2.69%"},
    {"method":"Pre-Auction","address":"10 Phillips Street, Neutral Bay","dateSold":"27-Feb-26","guidePrice":"$3,800,000","soldPrice":"$3,875,000","diff":"$75,000","pctChange":"1.97%"},
    {"method":"Pre-Auction","address":"13 Bank Street, North Sydney","dateSold":"06-Mar-26","guidePrice":"$3,450,000","soldPrice":"$3,370,000","diff":"-$80,000","pctChange":"-2.32%"},
    {"method":"Private Treaty","address":"59 Neutral Street, North Sydney","dateSold":"02-Mar-26","guidePrice":"$4,500,000","soldPrice":"$4,700,000","diff":"$200,000","pctChange":"4.44%"},
    {"method":"Pre-Auction","address":"5 Pyalla Street, Northbridge","dateSold":"02-Mar-26","guidePrice":"$4,100,000","soldPrice":"$4,050,000","diff":"-$50,000","pctChange":"-1.22%"},
    {"method":"Pre-Auction","address":"27 Narooma Road, Northbridge","dateSold":"27-Mar-26","guidePrice":"$6,200,000","soldPrice":"$5,330,000","diff":"-$870,000","pctChange":"-14.03%"},
    {"method":"Post Auction","address":"47 Neeworra Road, Northbridge","dateSold":"05-Mar-26","guidePrice":"$7,500,000","soldPrice":"$5,500,000","diff":"-$2,000,000","pctChange":"-26.67%"},
    {"method":"Private Treaty","address":"15 Whatmore Street, Waverton","dateSold":"27-Feb-26","guidePrice":"$3,510,000","soldPrice":"$3,510,000","diff":"$0","pctChange":"0.00%"},
    {"method":"At Auction","address":"24 Cobar Street, Willoughby","dateSold":"28-Feb-26","guidePrice":"$5,100,000","soldPrice":"$5,200,000","diff":"$100,000","pctChange":"1.96%"},
    {"method":"Pre-Auction","address":"14A Rocklands Road, Wollstonecraft","dateSold":"04-Mar-26","guidePrice":"$2,650,000","soldPrice":"$2,975,000","diff":"$325,000","pctChange":"12.26%"},
    {"method":"Pre-Auction","address":"30 Milray Avenue, Wollstonecraft","dateSold":"04-Mar-26","guidePrice":"$5,000,000","soldPrice":"$5,000,000","diff":"$0","pctChange":"0.00%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 3 - New Listings (23) + Sold (24)
# ═══════════════════════════════════════════════════════════════════════════
SHEET3_LISTINGS = [
    {"suburb":"Castle Cove","address":"12 Emerstan Drive, Castle Cove","auction":"For Sale (Guide price)","guide":"$5,800,000","land":1201,"aspect":"South","type":"5 beds, 4 baths, DLUG","dom":136},
    {"suburb":"Chatswood","address":"211 Fullers Road, Chatswood","auction":"11-Apr-26 15:45","guide":"$3,500,000","land":803,"aspect":"North","type":"4 beds, 1 bath, 1 CP","dom":1},
    {"suburb":"Cremorne","address":"71 Benelong Road, Cremorne","auction":"11-Apr-26 10:00","guide":"$2,900,000","land":228,"aspect":"West","type":"3 beds, 2 baths","dom":5},
    {"suburb":"Crows Nest","address":"99 Atchison Street, Crows Nest","auction":"11-Apr-26 09:00","guide":"$2,700,000","land":177,"aspect":"South","type":"3 beds, 1 bath, 1CS","dom":2},
    {"suburb":"Hunters Hill","address":"28 Barons Crescent, Hunters Hill","auction":"11-Apr-26 14:15","guide":"$4,500,000","land":2770,"aspect":"North","type":"5 beds, 3 baths, DLUG","dom":2},
    {"suburb":"Hunters Hill","address":"11 Lyndhurst Crescent, Hunters Hill","auction":"02-Apr-26 18:00","guide":"$6,500,000","land":601,"aspect":"North","type":"4 beds, 3 baths, DLUG","dom":2},
    {"suburb":"Middle Cove","address":"173 Eastern Valley Way, Middle Cove","auction":"AUC 1st Apr @ 5.15pm","guide":"$2,500,000","land":696,"aspect":"East","type":"4 beds, 3 baths, 3CS","dom":1},
    {"suburb":"Middle Cove","address":"12 North Arm Road, Middle Cove","auction":"11-Apr-26 09:00","guide":"$4,000,000","land":975,"aspect":"East","type":"5 beds, 2 baths, DLUG","dom":1},
    {"suburb":"Mosman","address":"38 Bond Street, Mosman","auction":"01-Apr-26 09:00","guide":"$3,000,000","land":233,"aspect":"West","type":"2 beds, 1 bath, 1 CP (semi)","dom":2},
    {"suburb":"Mosman","address":"130 Cowles Road, Mosman","auction":"11-Apr-26 09:45","guide":"$4,800,000","land":417,"aspect":"West","type":"5 beds, 2 baths, 1CS","dom":2},
    {"suburb":"Mosman","address":"14 Erith Street, Mosman","auction":"11-Apr-26 11:15","guide":"$4,800,000","land":613,"aspect":"South","type":"4 beds, 3 baths, 1 CS","dom":2},
    {"suburb":"Mosman","address":"60 Prince Street, Mosman","auction":"11-Apr-26 10:30","guide":"$4,800,000","land":512,"aspect":"South","type":"5 beds, 3 baths, 1 CP","dom":2},
    {"suburb":"Mosman","address":"31 Wyong Road, Mosman","auction":"01-Apr-26 09:00","guide":"$7,000,000","land":569,"aspect":"North","type":"5 beds, 3 baths, LUG","dom":2},
    {"suburb":"Mosman","address":"11 Alexander Avenue, Mosman","auction":"01-Apr-26 17:00","guide":"$7,000,000","land":443,"aspect":"North","type":"5 beds, 3 baths, 2CP","dom":2},
    {"suburb":"Mosman","address":"6 Cabramatta Road, Mosman","auction":"11-Apr-26 11:45","guide":"$7,900,000","land":394,"aspect":"South","type":"5 beds, 3 baths","dom":5},
    {"suburb":"Naremburn","address":"126 Northcote Street, Naremburn","auction":"11-Apr-26 13:30","guide":"$2,900,000","land":342,"aspect":"West","type":"3 beds, 2 baths, 1 CP","dom":2},
    {"suburb":"North Sydney","address":"12 Margaret Street, North Sydney","auction":"09-Apr-26 21:00","guide":"$3,300,000","land":279,"aspect":"West","type":"3 beds, 2 baths","dom":2},
    {"suburb":"Northbridge","address":"49 Coolawin Road, Northbridge","auction":"For Sale (Guide price)","guide":"$43,000,000","land":3434,"aspect":"East","type":"6 beds, 7 baths, 3 x LUG","dom":2},
    {"suburb":"Willoughby","address":"23A Oakville Road, Willoughby","auction":"AUC 18th Apr @ 3.00pm","guide":"$2,750,000","land":266,"aspect":"North","type":"3 beds, 2 baths, 1CP","dom":2},
    {"suburb":"Willoughby","address":"4 Nardoo Street, Willoughby","auction":"For Sale (Price Guide)","guide":"$3,700,000","land":695,"aspect":"South","type":"3 beds, 1 bath, LUG","dom":2},
    {"suburb":"Willoughby","address":"11 Sydney Street, Willoughby","auction":"11-Apr-26 10:30","guide":"$4,300,000","land":601,"aspect":"East","type":"4 beds, 2 baths, 2CS","dom":5},
    {"suburb":"Willoughby","address":"14 Cobar Street, Willoughby","auction":"11-Apr-26 02:15","guide":"$4,750,000","land":699,"aspect":"South","type":"5 beds, 3 baths, 1CP","dom":5},
    {"suburb":"Mosman","address":"22 Cowles Road, Mosman","auction":"01-Apr-26 09:00","guide":"$6,000,000","land":624,"aspect":"West","type":"4 beds, 2 baths, 1CS","dom":2},
]

SHEET3_SOLD = [
    {"method":"Pre-Auction","address":"93 Artarmon Road, Artarmon","dateSold":"11-Mar-26","guidePrice":"$3,300,000","soldPrice":"$2,950,000","diff":"-$350,000","pctChange":"-10.61%","dom":35},
    {"method":"Pre-Auction","address":"22 Warringa Road, Cammeray","dateSold":"09-Mar-26","guidePrice":"$4,400,000","soldPrice":"$4,600,000","diff":"$200,000","pctChange":"4.55%","dom":18},
    {"method":"Post Auction","address":"70 Sugarloaf Crescent, Castlecrag","dateSold":"06-Mar-26","guidePrice":"$3,200,000","soldPrice":"$3,150,000","diff":"-$50,000","pctChange":"-1.56%","dom":586},
    {"method":"Pre-Auction","address":"112 Greville Street, Chatswood","dateSold":"06-Mar-26","guidePrice":"$2,300,000","soldPrice":"$2,530,000","diff":"$230,000","pctChange":"10.00%","dom":44},
    {"method":"Pre-Auction","address":"33 Robinson Street, Chatswood","dateSold":"11-Mar-26","guidePrice":"$2,900,000","soldPrice":"$3,185,000","diff":"$285,000","pctChange":"9.83%","dom":16},
    {"method":"Private Treaty","address":"28 Saywell Street, Chatswood","dateSold":"12-Mar-26","guidePrice":"$2,800,000","soldPrice":"$3,050,000","diff":"$250,000","pctChange":"8.93%","dom":16},
    {"method":"At Auction","address":"3 Iredale Avenue, Cremorne Point","dateSold":"12-Mar-26","guidePrice":"$5,000,000","soldPrice":"$5,075,000","diff":"$75,000","pctChange":"1.50%","dom":29},
    {"method":"Pre-Auction","address":"8 Montague Road, Cremorne","dateSold":"12-Mar-26","guidePrice":"$6,200,000","soldPrice":"$6,475,000","diff":"$275,000","pctChange":"4.44%","dom":14},
    {"method":"Pre-Auction","address":"25 Brightmore Street, Cremorne","dateSold":"11-Mar-26","guidePrice":"$4,800,000","soldPrice":"$5,225,000","diff":"$425,000","pctChange":"8.85%","dom":30},
    {"method":"Pre-Auction","address":"51 Ernest Street, Crows Nest","dateSold":"10-Mar-26","guidePrice":"$3,500,000","soldPrice":"$3,500,000","diff":"$0","pctChange":"0.00%","dom":23},
    {"method":"Pre-Auction","address":"56 Bonnefin Road, Hunters Hill","dateSold":"13-Mar-26","guidePrice":"$3,600,000","soldPrice":"$3,550,000","diff":"-$50,000","pctChange":"-1.39%","dom":16},
    {"method":"Pre-Auction","address":"13 John Street, Hunters Hill","dateSold":"13-Mar-26","guidePrice":"$4,200,000","soldPrice":"$3,750,000","diff":"-$450,000","pctChange":"-10.71%","dom":22},
    {"method":"Pre-Auction","address":"45 Earl Street, Hunters Hill","dateSold":"13-Mar-26","guidePrice":"$4,500,000","soldPrice":"$4,500,000","diff":"$0","pctChange":"0.00%","dom":32},
    {"method":"Post Auction","address":"18 Melrose Street, Mosman","dateSold":"09-Mar-26","guidePrice":"$5,500,000","soldPrice":"$5,200,000","diff":"-$300,000","pctChange":"-5.45%","dom":32},
    {"method":"Post Auction","address":"8 Rhodes Avenue, Naremburn","dateSold":"13-Mar-26","guidePrice":"$5,100,000","soldPrice":"$4,870,000","diff":"-$230,000","pctChange":"-4.51%","dom":42},
    {"method":"Pre-Auction","address":"85 Bank Street, North Sydney","dateSold":"09-Mar-26","guidePrice":"$3,500,000","soldPrice":"$4,015,000","diff":"$515,000","pctChange":"14.71%","dom":14},
    {"method":"Pre-Auction","address":"24 Lord Street, North Sydney","dateSold":"12-Mar-26","guidePrice":"$4,000,000","soldPrice":"$4,850,000","diff":"$850,000","pctChange":"21.25%","dom":7},
    {"method":"Post Auction","address":"6 The Outpost, Northbridge","dateSold":"12-Mar-26","guidePrice":"$3,800,000","soldPrice":"$3,850,000","diff":"$50,000","pctChange":"1.32%","dom":45},
    {"method":"Pre-Auction","address":"3 Malacoota Road, Northbridge","dateSold":"12-Mar-26","guidePrice":"$4,700,000","soldPrice":"$4,500,000","diff":"-$200,000","pctChange":"-4.26%","dom":30},
    {"method":"Pre-Auction","address":"31 Mabel Street, Willoughby","dateSold":"12-Mar-26","guidePrice":"$3,800,000","soldPrice":"$4,200,000","diff":"$400,000","pctChange":"10.53%","dom":9},
    {"method":"Post Auction","address":"3 Owen Street, Willoughby","dateSold":"07-Mar-26","guidePrice":"$6,500,000","soldPrice":"$7,160,000","diff":"$660,000","pctChange":"10.15%","dom":44},
    {"method":"Pre-Auction","address":"30 Hector Road, Willoughby","dateSold":"13-Mar-26","guidePrice":"$3,500,000","soldPrice":"$3,200,000","diff":"-$300,000","pctChange":"-8.57%","dom":44},
    {"method":"Private Treaty","address":"44 Cobar Street, Willoughby","dateSold":"13-Mar-26","guidePrice":"$4,200,000","soldPrice":"$4,200,000","diff":"$0","pctChange":"0.00%","dom":0},
    {"method":"Post Auction","address":"37 Carlyle Lane, Wollstonecraft","dateSold":"12-Mar-26","guidePrice":"$4,000,000","soldPrice":"$4,200,000","diff":"$200,000","pctChange":"5.00%","dom":157},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 4 - New Listings (9) + Sold (15)
# ═══════════════════════════════════════════════════════════════════════════
SHEET4_LISTINGS = [
    {"suburb":"Chatswood","address":"28-32 Beaconsfield Road, Chatswood","auction":"15-Apr-26 18:00","guide":"$3,000,000","land":1625,"aspect":"South","type":"6 beds, 2 baths, LUG"},
    {"suburb":"Crows Nest","address":"27 Burlington Street, Crows Nest","auction":"18-Apr-26 09:00","guide":"$3,200,000","land":292,"aspect":"South","type":"3 beds, 1 bath, 1CS"},
    {"suburb":"Hunters Hill","address":"1 Reserve Street, Hunters Hill","auction":"18-Apr-26 11:15","guide":"$4,250,000","land":499,"aspect":"NE","type":"5 beds, 3 baths, LUG"},
    {"suburb":"Hunters Hill","address":"5a Pains Road, Hunters Hill","auction":"21-Apr-26 18:00","guide":"$3,500,000","land":582,"aspect":"West","type":"4 beds, 3 baths, DLUG"},
    {"suburb":"McMahons Point","address":"107 & 109 Union Street, McMahons Point","auction":"24-Apr-26 17:00 (EOI)","guide":"$10,500,000","land":459,"aspect":"South","type":"6 beds, 2 baths, 5 x LUG"},
    {"suburb":"Middle Cove","address":"1 Chowne Place, Middle Cove","auction":"18-Apr-26 12:00","guide":"$2,700,000","land":1050,"aspect":"West","type":"4 beds, 2 baths, 2CP"},
    {"suburb":"Mosman","address":"10 Calypso Avenue, Mosman","auction":"16-Apr-26 18:00","guide":"$2,750,000","land":221,"aspect":"West","type":"2 beds, 1 bath, 1 CP (semi)"},
    {"suburb":"Mosman","address":"77 Macpherson Street, Mosman","auction":"18-Apr-26 12:30","guide":"$5,600,000","land":575,"aspect":"East","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Mosman","address":"2 Little Street, Mosman","auction":"For Sale (Guide price)","guide":"$12,500,000","land":539,"aspect":"West","type":"4 beds, 3 baths, DLUG"},
]

SHEET4_SOLD = [
    {"method":"Pre-Auction","address":"4 Cameron Avenue, Artarmon","dateSold":"18-Mar-26","guidePrice":"$3,600,000","soldPrice":"$3,700,000","diff":"$100,000","pctChange":"2.78%"},
    {"method":"Pre-Auction","address":"3 Arkland Street, Cammeray","dateSold":"17-Mar-26","guidePrice":"$4,400,000","soldPrice":"$4,725,000","diff":"$325,000","pctChange":"7.39%"},
    {"method":"Pre-Auction","address":"107 Bellevue Street, Cammeray","dateSold":"18-Mar-26","guidePrice":"$4,200,000","soldPrice":"$4,400,000","diff":"$200,000","pctChange":"4.76%"},
    {"method":"Pre-Auction","address":"1 Fairyland Avenue, Chatswood","dateSold":"13-Mar-26","guidePrice":"$2,475,000","soldPrice":"$2,475,000","diff":"$0","pctChange":"0.00%"},
    {"method":"At Auction","address":"24 Lodge Road, Cremorne","dateSold":"14-Mar-26","guidePrice":"$8,500,000","soldPrice":"$8,450,000","diff":"-$50,000","pctChange":"-0.59%"},
    {"method":"Pre-Auction","address":"43A Ellalong Road, Cremorne","dateSold":"16-Mar-26","guidePrice":"$3,990,000","soldPrice":"$3,450,000","diff":"-$540,000","pctChange":"-13.53%"},
    {"method":"Pre-Auction","address":"28 Bennett Street, Cremorne","dateSold":"18-Mar-26","guidePrice":"$5,800,000","soldPrice":"$6,100,000","diff":"$300,000","pctChange":"5.17%"},
    {"method":"Pre-Auction","address":"218 West Street, Crows Nest","dateSold":"19-Mar-26","guidePrice":"$2,500,000","soldPrice":"$2,475,000","diff":"-$25,000","pctChange":"-1.00%"},
    {"method":"Pre-Auction","address":"173 Eastern Valley Way, Middle Cove","dateSold":"18-Mar-26","guidePrice":"$2,500,000","soldPrice":"$2,718,000","diff":"$218,000","pctChange":"8.72%"},
    {"method":"Post Auction","address":"125 Ourimbah Road, Mosman","dateSold":"19-Mar-26","guidePrice":"$4,500,000","soldPrice":"$4,500,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"8A Prince Street, Mosman","dateSold":"18-Mar-26","guidePrice":"$3,600,000","soldPrice":"$3,570,000","diff":"-$30,000","pctChange":"-0.83%"},
    {"method":"At Auction","address":"2a Ryrie Street, Mosman","dateSold":"14-Mar-26","guidePrice":"$3,750,000","soldPrice":"$3,700,000","diff":"-$50,000","pctChange":"-1.33%"},
    {"method":"Pre-Auction","address":"143 High Street, Willoughby","dateSold":"11-Mar-26","guidePrice":"$5,600,000","soldPrice":"$6,000,000","diff":"$400,000","pctChange":"7.14%"},
    {"method":"Pre-Auction","address":"7 Megalong Avenue, Willoughby","dateSold":"16-Mar-26","guidePrice":"$4,300,000","soldPrice":"$3,850,000","diff":"-$450,000","pctChange":"-10.47%"},
    {"method":"Pre-Auction","address":"2 Ann Street, Willoughby","dateSold":"17-Mar-26","guidePrice":"$2,375,000","soldPrice":"$2,375,000","diff":"$0","pctChange":"0.00%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 5 - New Listings (9) + Sold (22)
# ═══════════════════════════════════════════════════════════════════════════
SHEET5_LISTINGS = [
    {"suburb":"Cammeray","address":"22 Churchill Crescent, Cammeray","auction":"18-Apr-26 14:00","guide":"$3,700,000","land":401,"aspect":"NE","type":"6 beds, 2 baths, 1CS + LUG"},
    {"suburb":"Chatswood","address":"18 Bertram Street, Chatswood","auction":"02-May-26 15:00","guide":"$3,000,000","land":316,"aspect":"West","type":"4 beds, 3 baths, 1 CS"},
    {"suburb":"Chatswood","address":"15 Davies Street, Chatswood","auction":"02-May-26 16:30","guide":"$3,600,000","land":449,"aspect":"West","type":"4 beds, 2 baths, 2CP"},
    {"suburb":"Cremorne","address":"120 Macpherson Street, Cremorne","auction":"For Sale (Guide price)","guide":"$6,000,000","land":272,"aspect":"East","type":"5 beds, 3 baths, DLUG"},
    {"suburb":"Hunters Hill","address":"69 Alexandra Street, Hunters Hill","auction":"For Sale (Guide price)","guide":"$9,000,000","land":790,"aspect":"South","type":"5 beds, 4 baths, triple LUG"},
    {"suburb":"Kirribilli","address":"56 Carabella Street, Kirribilli","auction":"For Sale (Guide Price)","guide":"$8,000,000","land":379,"aspect":"NE","type":"5 beds, 2 baths, 2CP"},
    {"suburb":"Mosman","address":"32 Stanton Road, Mosman","auction":"18-Apr-26 13:00 (EOI)","guide":"$12,500,000","land":841,"aspect":"East","type":"4 beds, 4 baths, DLUG"},
    {"suburb":"Naremburn","address":"19 Central Street, Naremburn","auction":"11-Apr-26 11:00","guide":"$2,900,000","land":297,"aspect":"East","type":"4 beds, 2 baths"},
    {"suburb":"Willoughby","address":"26 Cambridge Street, Willoughby","auction":"18-Apr-26 10:30","guide":"$3,650,000","land":540,"aspect":"South","type":"3 beds, 1 bath, LUG"},
]

SHEET5_SOLD = [
    {"method":"Pre-Auction","address":"11 Burra Road, Artarmon","dateSold":"25-Mar-26","guidePrice":"$3,500,000","soldPrice":"$3,500,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"18 Rosalind Street, Cammeray","dateSold":"25-Mar-26","guidePrice":"$2,500,000","soldPrice":"$2,441,000","diff":"-$59,000","pctChange":"-2.36%"},
    {"method":"Post Auction","address":"317 Mowbray Road, Chatswood","dateSold":"19-Mar-26","guidePrice":"$5,700,000","soldPrice":"$4,800,000","diff":"-$900,000","pctChange":"-15.79%"},
    {"method":"Post Auction","address":"26 Valerie Avenue, Chatswood","dateSold":"20-Mar-26","guidePrice":"$2,600,000","soldPrice":"$2,808,000","diff":"$208,000","pctChange":"8.00%"},
    {"method":"Post Auction","address":"10 Ivy Street, Chatswood","dateSold":"23-Mar-26","guidePrice":"$4,000,000","soldPrice":"$4,168,000","diff":"$168,000","pctChange":"4.20%"},
    {"method":"At Auction","address":"56 Cremorne Road, Cremorne Point","dateSold":"25-Mar-26","guidePrice":"$6,500,000","soldPrice":"$6,500,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"162 West Street, Crows Nest","dateSold":"26-Mar-26","guidePrice":"$2,500,000","soldPrice":"$2,625,000","diff":"$125,000","pctChange":"5.00%"},
    {"method":"Post Auction","address":"14 Gale Street, Hunters Hill","dateSold":"24-Mar-26","guidePrice":"$5,750,000","soldPrice":"$6,125,000","diff":"$375,000","pctChange":"6.52%"},
    {"method":"At Auction","address":"34 Ryde Road, Hunters Hill","dateSold":"25-Mar-26","guidePrice":"$3,200,000","soldPrice":"$3,280,000","diff":"$80,000","pctChange":"2.50%"},
    {"method":"Pre-Auction","address":"26 David Street, Mosman","dateSold":"25-Mar-26","guidePrice":"$9,000,000","soldPrice":"$9,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"17B Market Street, Naremburn","dateSold":"23-Mar-26","guidePrice":"$4,000,000","soldPrice":"$3,710,000","diff":"-$290,000","pctChange":"-7.25%"},
    {"method":"Private Treaty","address":"32b Market Street, Naremburn","dateSold":"25-Mar-26","guidePrice":"$3,300,000","soldPrice":"$3,300,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"18 Yeo Street, Neutral Bay","dateSold":"23-Mar-26","guidePrice":"$3,600,000","soldPrice":"$3,740,000","diff":"$140,000","pctChange":"3.89%"},
    {"method":"Private Treaty","address":"36 Aubin Street, Neutral Bay","dateSold":"23-Mar-26","guidePrice":"$7,000,000","soldPrice":"$7,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"86 Cliff Avenue, Northbridge","dateSold":"20-Mar-26","guidePrice":"$4,850,000","soldPrice":"$4,850,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Post Auction","address":"10 Courallie Road, Northbridge","dateSold":"24-Mar-26","guidePrice":"$11,850,000","soldPrice":"$8,200,000","diff":"-$3,650,000","pctChange":"-30.80%"},
    {"method":"Post Auction","address":"51 Baroona Road, Northbridge","dateSold":"26-Mar-26","guidePrice":"$4,500,000","soldPrice":"$4,325,000","diff":"-$175,000","pctChange":"-3.89%"},
    {"method":"Pre-Auction","address":"72 Kameruka Road, Northbridge","dateSold":"26-Mar-26","guidePrice":"$4,200,000","soldPrice":"$4,508,888","diff":"$308,888","pctChange":"7.35%"},
    {"method":"Post Auction","address":"1c Mabel Street, Willoughby","dateSold":"26-Mar-26","guidePrice":"$3,200,000","soldPrice":"$3,250,000","diff":"$50,000","pctChange":"1.56%"},
    {"method":"Post Auction","address":"83 Tyneside Avenue, Willoughby","dateSold":"26-Mar-26","guidePrice":"$3,300,000","soldPrice":"$3,300,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Post Auction","address":"135 Mowbray Road, Willoughby","dateSold":"26-Mar-26","guidePrice":"$5,000,000","soldPrice":"$5,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"38 Shirley Road, Wollstonecraft","dateSold":"25-Mar-26","guidePrice":"$4,500,000","soldPrice":"$4,550,000","diff":"$50,000","pctChange":"1.11%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# Also include original sheet data (from previous script)
# ═══════════════════════════════════════════════════════════════════════════
SHEET0_LISTINGS = [
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

SHEET0_SOLD = [
    {"method":"Post Auction","address":"22 Shepherd Road, Artarmon","dateSold":"21-Jan-26","guidePrice":"$2,500,000","soldPrice":"$2,800,000","diff":"$300,000","pctChange":"12.00%"},
    {"method":"Private Treaty","address":"3 D'Aram Street, Hunters Hill","dateSold":"22-Jan-26","guidePrice":"$4,365,000","soldPrice":"$4,365,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"269 Claire Street, Naremburn","dateSold":"26-Jan-26","guidePrice":"$3,200,000","soldPrice":"$3,338,000","diff":"$138,000","pctChange":"4.31%"},
    {"method":"Post Auction","address":"38 Second Avenue, Willoughby","dateSold":"25-Jan-26","guidePrice":"$3,100,000","soldPrice":"$2,750,000","diff":"-$350,000","pctChange":"-11.29%"},
    {"method":"Pre-Auction","address":"40 High Street, Willoughby","dateSold":"28-Jan-26","guidePrice":"$2,700,000","soldPrice":"$3,000,000","diff":"$300,000","pctChange":"11.11%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 6 - New Listings (10) + Sold (31) - Updated/combined sheet
# ═══════════════════════════════════════════════════════════════════════════
SHEET6_LISTINGS = [
    {"suburb":"Cammeray","address":"2 Cowdroy Avenue, Cammeray","auction":"For Sale (Price guide)","guide":"$14,000,000","land":936,"aspect":"South","type":"8 beds, 7 baths, 4CS"},
]

SHEET6_SOLD = [
    {"method":"Pre-Auction","address":"83 Woolwich Road, Hunters Hill","dateSold":"27-Mar-26","guidePrice":"$3,000,000","soldPrice":"$3,120,000","diff":"$120,000","pctChange":"4.00%"},
    {"method":"Pre-Auction","address":"1 Manning Road, Hunters Hill","dateSold":"27-Mar-26","guidePrice":"$3,000,000","soldPrice":"$3,150,000","diff":"$150,000","pctChange":"5.00%"},
    {"method":"Pre-Auction","address":"16 Farnell Street, Hunters Hill","dateSold":"27-Mar-26","guidePrice":"$7,300,000","soldPrice":"$7,800,000","diff":"$500,000","pctChange":"6.85%"},
    {"method":"Pre-Auction","address":"26 David Street, Mosman","dateSold":"25-Mar-26","guidePrice":"$9,000,000","soldPrice":"$8,750,000","diff":"-$250,000","pctChange":"-2.78%"},
    {"method":"Pre-Auction","address":"6 Wolseley Road, Mosman","dateSold":"26-Mar-26","guidePrice":"$6,000,000","soldPrice":"$6,600,000","diff":"$600,000","pctChange":"10.00%"},
    {"method":"At Auction","address":"10 Cyprian Street, Mosman","dateSold":"27-Mar-26","guidePrice":"$10,000,000","soldPrice":"$10,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"At Auction","address":"14 Illawarra Street, Mosman","dateSold":"27-Mar-26","guidePrice":"$5,000,000","soldPrice":"$4,635,000","diff":"-$365,000","pctChange":"-7.30%"},
    {"method":"Post EOI","address":"34 Rickard Avenue, Mosman","dateSold":"27-Mar-26","guidePrice":"$10,000,000","soldPrice":"$9,000,000","diff":"-$1,000,000","pctChange":"-10.00%"},
    {"method":"Post Auction","address":"70 West Street, North Sydney","dateSold":"27-Mar-26","guidePrice":"$2,900,000","soldPrice":"$2,750,000","diff":"-$150,000","pctChange":"-5.17%"},
    {"method":"Pre-Auction","address":"100 Warrane Road, Willoughby","dateSold":"27-Mar-26","guidePrice":"$4,300,000","soldPrice":"$3,950,000","diff":"-$350,000","pctChange":"-8.14%"},
]

# ═══════════════════════════════════════════════════════════════════════════
# SHEET 7 - New Listings (5) + Sold (17) - Latest sheet with full sold data
# ═══════════════════════════════════════════════════════════════════════════
SHEET7_LISTINGS = [
    {"suburb":"Artarmon","address":"28 Robert Street, Artarmon","auction":"23-Apr-26 17:00","guide":"$2,200,000","land":322,"aspect":"West","type":"3 beds, 1 bath, DLUG"},
    {"suburb":"Hunters Hill","address":"84 Ryde Road, Hunters Hill","auction":"09-May-26 09:30","guide":"$3,000,000","land":484,"aspect":"SE","type":"5 beds, 3 baths, 1CP + 2CS"},
    {"suburb":"Mosman","address":"37 Dalton Road, Mosman","auction":"02-May-26 09:00","guide":"$3,700,000","land":316,"aspect":"South","type":"4 beds, 1 bath, LUG"},
    {"suburb":"Mosman","address":"3 Methuen Avenue, Mosman","auction":"29-Apr-26 17:00","guide":"$12,500,000","land":555,"aspect":"East","type":"5 beds, 4 baths, DLUG + 2CS"},
    {"suburb":"Northbridge","address":"29 Weemala Road, Northbridge","auction":"For Sale (Guide price)","guide":"$10,000,000","land":841,"aspect":"East","type":"5 beds, 3 baths, 2CP"},
]

SHEET7_SOLD = [
    {"method":"At Auction","address":"24 Robert Street, Artarmon","dateSold":"28-Mar-26","guidePrice":"$2,300,000","soldPrice":"$2,650,000","diff":"$350,000","pctChange":"15.22%"},
    {"method":"Post Auction","address":"304 Edinburgh Road, Castlecrag","dateSold":"28-Mar-26","guidePrice":"$28,000,000","soldPrice":"$19,000,000","diff":"-$9,000,000","pctChange":"-32.14%"},
    {"method":"Post Auction","address":"20 Morella Place, Castle Cove","dateSold":"27-Mar-26","guidePrice":"$4,200,000","soldPrice":"$4,425,000","diff":"$225,000","pctChange":"5.36%"},
    {"method":"Post Auction","address":"7 Daymar Place, Castle Cove","dateSold":"01-Apr-26","guidePrice":"$3,800,000","soldPrice":"$4,038,000","diff":"$238,000","pctChange":"6.26%"},
    {"method":"At Auction","address":"50 Park Avenue, Chatswood","dateSold":"28-Mar-26","guidePrice":"$3,900,000","soldPrice":"$4,300,000","diff":"$400,000","pctChange":"10.26%"},
    {"method":"Post Auction","address":"17-19 Bogota Avenue, Cremorne Point","dateSold":"27-Mar-26","guidePrice":"$9,500,000","soldPrice":"$9,938,000","diff":"$438,000","pctChange":"4.61%"},
    {"method":"At Auction","address":"66 Hayberry Street, Crows Nest","dateSold":"28-Mar-26","guidePrice":"$2,900,000","soldPrice":"$3,100,000","diff":"$200,000","pctChange":"6.90%"},
    {"method":"Post Auction","address":"20 The Grove, Mosman","dateSold":"30-Mar-26","guidePrice":"$25,000,000","soldPrice":"$22,500,000","diff":"-$2,500,000","pctChange":"-10.00%"},
    {"method":"Post Auction","address":"27 Bardwell Road, Mosman","dateSold":"30-Mar-26","guidePrice":"$3,500,000","soldPrice":"$3,675,000","diff":"$175,000","pctChange":"5.00%"},
    {"method":"Post Auction","address":"22B Musgrave Street, Mosman","dateSold":"31-Mar-26","guidePrice":"$10,000,000","soldPrice":"$10,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Post Auction","address":"44 Musgrave Street, Mosman","dateSold":"31-Mar-26","guidePrice":"$4,300,000","soldPrice":"$3,388,000","diff":"-$912,000","pctChange":"-21.21%"},
    {"method":"Post Auction","address":"2/1C Avenue Road, Mosman","dateSold":"31-Mar-26","guidePrice":"$4,200,000","soldPrice":"$4,500,000","diff":"$300,000","pctChange":"7.14%"},
    {"method":"Private Treaty","address":"17 Morella Road, Mosman","dateSold":"31-Mar-26","guidePrice":"$23,000,000","soldPrice":"$23,000,000","diff":"$0","pctChange":"0.00%"},
    {"method":"Pre-Auction","address":"7 Yeo Street, Neutral Bay","dateSold":"31-Mar-26","guidePrice":"$2,800,000","soldPrice":"$2,920,000","diff":"$120,000","pctChange":"4.29%"},
    {"method":"At Auction","address":"2 Miowera Road, Northbridge","dateSold":"28-Mar-26","guidePrice":"$7,000,000","soldPrice":"$7,910,000","diff":"$910,000","pctChange":"13.00%"},
    {"method":"Post Auction","address":"60A Marlborough Road, Willoughby","dateSold":"30-Mar-26","guidePrice":"$3,800,000","soldPrice":"$3,600,000","diff":"-$200,000","pctChange":"-5.26%"},
    {"method":"Post Auction","address":"45 Tulloh Street, Willoughby","dateSold":"01-Apr-26","guidePrice":"$4,000,000","soldPrice":"$4,000,000","diff":"$0","pctChange":"0.00%"},
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

    # Combine all listings and sold data
    all_listings = SHEET0_LISTINGS + SHEET1_LISTINGS + SHEET2_LISTINGS + SHEET3_LISTINGS + SHEET4_LISTINGS + SHEET5_LISTINGS + SHEET6_LISTINGS + SHEET7_LISTINGS
    all_sold = SHEET0_SOLD + SHEET1_SOLD + SHEET2_SOLD + SHEET3_SOLD + SHEET4_SOLD + SHEET5_SOLD + SHEET6_SOLD + SHEET7_SOLD

    # Deduplicate by normalized address (keep latest/most complete entry)
    seen_listings = {}
    for nl in all_listings:
        k = normalize_addr(nl['address'])
        if k not in seen_listings:
            seen_listings[k] = nl
        else:
            # Keep the one with more data
            existing = seen_listings[k]
            if nl.get('land', 0) and not existing.get('land', 0):
                seen_listings[k] = nl

    seen_sold = {}
    for s in all_sold:
        k = normalize_addr(s['address'])
        if k not in seen_sold:
            seen_sold[k] = s
        else:
            # Prefer the entry with more complete data (soldPrice > guidePrice only)
            existing = seen_sold[k]
            if s.get('soldPrice') and not existing.get('soldPrice'):
                seen_sold[k] = s
            elif s.get('soldPrice') and s.get('guidePrice') and not existing.get('guidePrice'):
                seen_sold[k] = s

    unique_listings = list(seen_listings.values())
    unique_sold = list(seen_sold.values())

    print(f"Total listings: {len(all_listings)} -> {len(unique_listings)} unique")
    print(f"Total sold: {len(all_sold)} -> {len(unique_sold)} unique")

    js_data = json.dumps(unique_listings)
    js_sold = json.dumps(unique_sold)

    # Build the new JS injection code
    js_code = f"""
// ── Spreadsheet data injection v2 (comprehensive - 6 sheets) ──
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

  let fsMatched = 0, soldFromListings = 0, soldMatched = 0;

  // Match new listings → For Sale AND Sold
  for (const nl of listings) {{
    const k = _normalizeAddr(nl.address);
    const fsMatch = fsMap[k];
    if (fsMatch) {{
      if (nl.guide && !fsMatch.guidePrice) fsMatch.guidePrice = nl.guide;
      if (nl.land && (!fsMatch.landSize || fsMatch.landSize === 0)) fsMatch.landSize = nl.land;
      if (nl.aspect) fsMatch.aspect = nl.aspect;
      if (nl.auction && (nl.auction.startsWith('AUC') || nl.auction.startsWith('EOI'))) fsMatch.auctionDetail = nl.auction;
      if (nl.type) fsMatch.propertyDetail = nl.type;
      if (nl.dom) fsMatch.daysOnMarket = nl.dom;
      fsMatched++;
    }}
    // Also check if this listing has since sold
    const soldMatch = soldMap[k];
    if (soldMatch) {{
      if (nl.guide && !soldMatch.guidePrice) soldMatch.guidePrice = nl.guide;
      if (nl.land && (!soldMatch.landSize || soldMatch.landSize === 0)) soldMatch.landSize = nl.land;
      if (nl.aspect) soldMatch.aspect = nl.aspect;
      if (nl.type) soldMatch.propertyDetail = nl.type;
      if (nl.auction && (nl.auction.startsWith('AUC') || nl.auction.startsWith('EOI'))) soldMatch.auctionDetail = nl.auction;
      soldFromListings++;
    }}
  }}

  // Match sold data → Sold listings (actual sold prices + guide prices)
  for (const s of soldData) {{
    const k = _normalizeAddr(s.address);
    const match = soldMap[k];
    if (match) {{
      if (s.soldPrice && (!match.soldPrice || match.soldPrice === 'Price Withheld')) match.soldPrice = s.soldPrice;
      if (s.guidePrice && !match.guidePrice) match.guidePrice = s.guidePrice;
      if (s.method && !match.method) match.method = s.method;
      if (s.diff) match.priceDiff = s.diff;
      if (s.pctChange) match.pctChange = s.pctChange;
      if (s.dom) match.daysOnMarket = s.dom;
      soldMatched++;
    }}
    // Also check if the sold property is still in For Sale (shouldn't be, but fill guide)
    const fsMatch = fsMap[k];
    if (fsMatch) {{
      if (s.guidePrice && !fsMatch.guidePrice) fsMatch.guidePrice = s.guidePrice;
    }}
  }}

  console.log('Spreadsheet v2: ' + fsMatched + ' For Sale, ' + soldFromListings + ' Sold enriched, ' + soldMatched + ' Sold prices');
}}
"""

    # Remove old _injectSpreadsheetData function and replace with new one
    # Find the old function
    old_start = html.find('// ── Spreadsheet data injection')
    if old_start == -1:
        old_start = html.find('function _injectSpreadsheetData()')

    if old_start != -1:
        # Find the end of the old function (the closing } before window.addEventListener)
        old_end = html.find("\nwindow.addEventListener('load'", old_start)
        if old_end == -1:
            old_end = html.find('\nwindow.addEventListener("load"', old_start)

        if old_end != -1:
            html = html[:old_start] + js_code.strip() + '\n\n' + html[old_end+1:]
            print("Replaced existing _injectSpreadsheetData function")
        else:
            print("ERROR: Could not find end of old function")
            return
    else:
        # Insert before window.addEventListener
        marker = "window.addEventListener('load', () => {"
        idx = html.find(marker)
        if idx == -1:
            print("ERROR: Could not find window load marker")
            return
        html = html[:idx] + js_code + '\n' + html[idx:]
        print("Inserted new _injectSpreadsheetData function")

    # Make sure _injectSpreadsheetData is called in the load listener
    if '_injectSpreadsheetData();' not in html:
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

    print(f"\nApp file size: {len(html):,} bytes")


if __name__ == '__main__':
    main()
