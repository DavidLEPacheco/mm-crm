#!/usr/bin/env python3
"""
Inject Domain.com.au Auction Data into Mazar Martin App
========================================================
Scraped 190 auction listings from Domain on 07/04/2026.
Filters to LNS suburbs only, cross-references with existing For Sale
data for price guides, and injects as D.upcomingAuctions array.

Also updates daily_refresh.py to cross-check with Proping cancelled auctions.

Usage:
  python3 inject_auction_data.py
  python3 inject_auction_data.py --dry-run
"""

import json, re, os, sys
from datetime import datetime
from pathlib import Path

_DL = Path(__file__).resolve().parent.parent

APP_PATH = str(_DL / 'mazar_martin_app.html')

# Lower North Shore suburbs (filter out surrounding suburbs that Domain included)
LNS_SUBURBS = {
    'mosman', 'cremorne', 'cremorne point', 'neutral bay', 'kirribilli',
    'lavender bay', 'milsons point', 'north sydney', 'wollstonecraft',
    'waverton', 'cammeray', 'crows nest', 'st leonards', 'artarmon',
    'willoughby', 'chatswood', 'naremburn', 'northbridge', 'castlecrag',
    'castle cove', 'middle cove', 'hunters hill', 'northwood',
    'greenwich', 'lane cove', 'lane cove west', 'longueville',
    'linley point', 'riverview', 'mcmahons point', 'kurraba point',
}

# Raw scraped data: address|suburb|beds|baths|parking|price|auctionDate|type
RAW_DATA = """307/5 Belmont Avenue, Wollstonecraft|Wollstonecraft|1|1||Auction - Guide $750,000|2026-04-11T09:00:00|ApartmentUnitFlat
11/9 Wyagdon Street, Neutral Bay|Neutral Bay|1|1|1|Under Offer|2026-04-11T09:00:00|ApartmentUnitFlat
99 Atchison Street, Crows Nest|Crows Nest|3|1|1|Auction Guide: $2,600,000|2026-04-11T09:00:00|House
2/2 Bannerman Street, Cremorne|Cremorne|2|2|2|Auction Guide $1,800,000|2026-04-11T09:00:00|Townhouse
4/2-6 Margaret Street, North Sydney|North Sydney|2|2|1|Guide $2,950,000|2026-05-02T14:15:00|Townhouse
39/48 Upper Pitt Street, Kirribilli|Kirribilli|2|1|1|Auction|2026-04-11T09:15:00|ApartmentUnitFlat
3/15 Rocklands Road, Wollstonecraft|Wollstonecraft|2|2|1|Contact Agent|2026-04-11T09:15:00|Townhouse
14/15-19 Church Street, Chatswood|Chatswood|2|1|1|Auction - Contact Agent|2026-04-16T17:30:00|ApartmentUnitFlat
312/88 Vista Street, Mosman|Mosman|1|1||Contact Agent|2026-04-16T18:00:00|ApartmentUnitFlat
130 Cowles Road, Mosman|Mosman|5|2|1|Contact Agent|2026-04-11T09:45:00|House
23/1-5 Albany Street, St Leonards|St Leonards|2|2|1|Auction - Contact Agent|2026-04-18T15:30:00|ApartmentUnitFlat
4/325 Alfred Street, Neutral Bay|Neutral Bay|2|1||Contact Agent|2026-04-16T18:00:00|ApartmentUnitFlat
101/562 Willoughby Road, Willoughby|Willoughby|1|1|1|Auction | Price on Request|2026-04-22T17:15:00|ApartmentUnitFlat
6/1B Armstrong Street, Willoughby|Willoughby|2|1|1|Auction - Contact Agent|2026-04-18T11:30:00|ApartmentUnitFlat
28 Robert Street, Artarmon|Artarmon|3|1|2|Auction - Contact Agent|2026-04-23T17:00:00|Duplex
1901/138 Walker Street, North Sydney|North Sydney|2|2|1|Auction Guide: $1,295,000|2026-04-23T17:00:00|ApartmentUnitFlat
73 Minimbah Road, Northbridge|Northbridge|4|2|2|Contact Agent|2026-04-18T12:00:00|House
11 Sydney Street, Willoughby|Willoughby|4|2|2|Auction - Contact Agent|2026-04-11T10:30:00|House
1 Pearl Avenue, Chatswood|Chatswood|4|4|4|Contact Agent|2026-04-25T10:00:00|Duplex
235 Sailors Bay Road, Northbridge|Northbridge|4|2|2|Contact Agent|2026-04-18T10:30:00|House
1 Harnett Place, Chatswood|Chatswood|4|2|3|Auction - Contact Agent|2026-04-18T13:30:00|House
4/6 Waverton Avenue, Waverton|Waverton|3|2|2|Contact Agent|2026-04-18T11:00:00|Townhouse
8/236 Victoria Avenue, Chatswood|Chatswood|3|2|2|Price on request|2026-04-11T10:30:00|ApartmentUnitFlat
103/5 Belmont Avenue, Wollstonecraft|Wollstonecraft|3|2|2|Auction (if not sold prior) - Contact Agent|2026-05-02T09:00:00|ApartmentUnitFlat
513/55 Harbour Street, Mosman|Mosman|2|2|1|Contact Agent|2026-04-11T10:30:00|ApartmentUnitFlat
2/13 Premier Street, Neutral Bay|Neutral Bay|3|1|1|Auction Guide $1,300,000|2026-04-11T12:15:00|ApartmentUnitFlat
13/66 Ben Boyd Road, Neutral Bay|Neutral Bay|2|1|1|Auction - Contact Agent|2026-05-02T13:30:00|ApartmentUnitFlat
6/2B Milner Crescent, Wollstonecraft|Wollstonecraft|2|1||Price guide - $950,000|2026-05-02T09:00:00|ApartmentUnitFlat
2211/9 Eric Road, Artarmon|Artarmon|1|1|1|Auction - Contact Agent|2026-04-18T14:00:00|ApartmentUnitFlat
5/29 Carter Street, Cammeray|Cammeray|1|1|1|Auction Guide: $750,000|2026-04-30T17:00:00|ApartmentUnitFlat
2507/1 Sergeants Lane, St Leonards|St Leonards|3|2|2|Auction - Contact Agent|2026-05-09T09:15:00|ApartmentUnitFlat
10/19-21 Hampden Avenue, Cremorne|Cremorne|3|2|2|Guide $1,650,000|2026-05-02T15:00:00|ApartmentUnitFlat
1/62 Murdoch Street, Cremorne|Cremorne|2|1|1|Auction Guide $1,350,000|2026-04-11T10:30:00|ApartmentUnitFlat
94 Laurel Street, Willoughby|Willoughby|5|2|1|Auction - Contact Agent|2026-04-18T12:15:00|House
47 Park Avenue, Chatswood|Chatswood|5|3|2|Auction - Contact Agent|2026-04-18T10:30:00|House
1605/168 Walker Street, North Sydney|North Sydney|3|2|2|Auction - Contact Agent|2026-05-09T10:30:00|ApartmentUnitFlat
5/25 Waruda Street, Kirribilli|Kirribilli|2|1|1|Contact Agent|2026-04-18T11:00:00|ApartmentUnitFlat
8 Lone Pine Avenue, Chatswood|Chatswood|4|3|1|AUCTION, Guide $3,000,000|2026-04-15T18:00:00|House
5 Tunks Street, Waverton|Waverton|3|2||Auction - Contact Victoria Liu|2026-05-02T09:45:00|House
8/2A Brady Street, Mosman|Mosman|3|2|2|Auction - Price Guide $2,500,000|2026-04-16T17:00:00|ApartmentUnitFlat
805/30 Alfred Street South, Milsons Point|Milsons Point|2|2|1|Auction | Guide $2,200,000|2026-04-18T10:30:00|ApartmentUnitFlat
12/17-19 Grasmere Road, Cremorne|Cremorne|3|2|2|Auction Guide: $1,675,000|2026-04-23T17:00:00|ApartmentUnitFlat
3/16-18 Milner Road, Artarmon|Artarmon|3|2|1|Auction - Contact Agent|2026-05-02T09:15:00|Townhouse
1/220 Pacific Highway, Crows Nest|Crows Nest|1|1|1|Contact Agent|2026-04-18T10:00:00|ApartmentUnitFlat
1603/1 Post Office Lane, Chatswood|Chatswood|1|1|1|Auction - Contact Agent|2026-04-18T16:30:00|ApartmentUnitFlat
14 Erith Street, Mosman|Mosman|4|3|1|Contact Agent|2026-04-11T11:15:00|House
10 Calypso Avenue, Mosman|Mosman|2|1|1|Auction Guide - $2,750,000|2026-04-16T18:00:00|SemiDetached
23A Oakville Road, Willoughby|Willoughby|3|2|1|Auction Guide $2,750,000|2026-04-18T15:00:00|House
12 Rocklands Road, Wollstonecraft|Wollstonecraft|3|1|1|Auction|2026-04-18T09:45:00|House
3/8 Westleigh Street, Neutral Bay|Neutral Bay|3|2|1|Auction - Contact Agent|2026-05-09T12:30:00|Townhouse
7/10 Lindsay Street, Neutral Bay|Neutral Bay|3|1|1|Auction Wed 15th Apr 6:00pm|2026-04-15T18:00:00|ApartmentUnitFlat
3/42 Kardinia Road, Mosman|Mosman|3|2|2|Auction - Contact Agent|2026-05-02T11:00:00|ApartmentUnitFlat
18 Bertram Street, Chatswood|Chatswood|4|3|1|Contact Agent|2026-05-02T15:00:00|SemiDetached
19 Central Street, Naremburn|Naremburn|4|2||Auction|2026-04-18T11:00:00|House
2203/69 Albert Avenue, Chatswood|Chatswood|2|2|1|Auction - Contact Agent|2026-05-02T16:00:00|ApartmentUnitFlat
303/15 Richmond Avenue, Willoughby|Willoughby|1|1||Auction - Contact Agent|2026-05-02T09:30:00|ApartmentUnitFlat
31 Royal Street, Chatswood|Chatswood|5|3|1|Auction Guide $3,900,000|2026-04-15T17:30:00|House
15 Davies Street, Chatswood|Chatswood|4|3|2|Auction - Contact Agent|2026-05-02T16:30:00|House
28 - 32 Beaconsfield Road, Chatswood|Chatswood|6|2|3|AUCTION, Contact Agent|2026-04-15T18:00:00|House
14/29 Rawson Street, Neutral Bay|Neutral Bay|3|2|1|Auction - Contact Agent|2026-04-23T17:00:00|Townhouse
14/41-45 Broughton Road, Artarmon|Artarmon|3|2|1|Auction | Price Guide $1,400,000|2026-04-18T11:30:00|ApartmentUnitFlat
5/12-14 Merlin Street, Neutral Bay|Neutral Bay|2|1|1|Auction Guide - $1,050,000|2026-04-23T17:00:00|ApartmentUnitFlat
4/20 Moriarty Road, Chatswood|Chatswood|2|1|1|Auction- Guide $1,000,000 - $1,100,000|2026-04-18T11:30:00|ApartmentUnitFlat
803/26 Napier Street, North Sydney|North Sydney|1|1|1|Please contact agent|2026-05-07T09:00:00|ApartmentUnitFlat
16 Tindale Road, Artarmon|Artarmon|5|4|1|Auction Guide $4,850,000|2026-04-18T13:30:00|House
106 Sydney Street, Willoughby|Willoughby|5|3|2|Auction - Contact Agent|2026-05-23T12:00:00|House
22 Churchill Crescent, Cammeray|Cammeray|6|2|2|Auction Sat 18th Apr 2:00pm|2026-04-18T14:00:00|House
6/800 Military Road, Mosman|Mosman|3|2|2|Auction Guide $2,800,000|2026-04-16T18:00:00|Townhouse
6/199 West Street, Crows Nest|Crows Nest|3|2|2|Contact Agent|2026-04-11T12:00:00|Townhouse
101/15 Richmond Avenue, Willoughby|Willoughby|3|2|1|Auction - Contact Agent|2026-05-02T09:00:00|ApartmentUnitFlat
18/174 Spit Road, Mosman|Mosman|2|1|1|Contact Agent|2026-04-11T12:00:00|ApartmentUnitFlat
8/2 Parraween Street, Cremorne|Cremorne|1|1|1|Auction Guide: $800,000|2026-04-18T10:30:00|ApartmentUnitFlat
23 Kooba Avenue, Chatswood|Chatswood|4|2|4|Auction - Contact Agent|2026-05-09T16:30:00|House
2114/168 Walker Street, North Sydney|North Sydney|2|2|1|Auction | Contact Agent|2026-04-18T09:00:00|ApartmentUnitFlat
42 Cowdroy Avenue, Cammeray|Cammeray|4|3|3|Auction | Contact De Brennan|2026-04-18T12:00:00|House
77 Macpherson Street, Mosman|Mosman|5|3|3|Contact Agent|2026-04-18T12:30:00|House
1/72 Wycombe Road, Neutral Bay|Neutral Bay|3|3|1|Contact agent|2026-05-02T12:00:00|ApartmentUnitFlat
4 Lawrence Street, Chatswood|Chatswood|3|1|1|Auction|2026-04-18T15:00:00|House
1&2/11 Bariston Avenue, Cremorne|Cremorne|6|2|2|Auction - Contact Agent|2026-04-18T12:00:00|BlockOfUnits
37 Dalton Road, Mosman|Mosman|4|1|1|Contact Agent|2026-05-02T09:00:00|House
103/31-33 Albany Street, Crows Nest|Crows Nest|2|2|1|Auction Guide $1,600,000|2026-04-18T11:00:00|ApartmentUnitFlat
502/38C Albert Avenue, Chatswood|Chatswood|2|2|1|Auction - Contact Agent|2026-04-18T15:00:00|ApartmentUnitFlat
8/267-271 Sailors Bay Road, Northbridge|Northbridge|2|1|1|AUCTION - Contact Agent|2026-04-18T10:00:00|ApartmentUnitFlat
6/15-23 Sutherland Street, Cremorne|Cremorne|2|1|1|AUCTION, Contact Agent|2026-04-22T18:00:00|ApartmentUnitFlat
62/1 Jersey Road, Artarmon|Artarmon|2|1|1|Auction | Contact Agent|2026-04-18T12:30:00|ApartmentUnitFlat
4 Gorman Street, Willoughby|Willoughby|5|3|2|Auction Guide $4,300,000|2026-04-11T15:30:00|House
40/10 Carr Street, Waverton|Waverton|2|2|1|Guide $1,485,000|2026-05-09T10:30:00|ApartmentUnitFlat
116 Beaconsfield Road, Chatswood|Chatswood|4|2|4|Auction|2026-04-18T17:00:00|House
2B/18 King Street, Waverton|Waverton|3|2|2|Auction Guide $2,650,000|2026-04-22T18:00:00|ApartmentUnitFlat
5/28 Grosvenor Street, Neutral Bay|Neutral Bay|3|2|2|Auction guide $2,400,000|2026-04-18T09:00:00|Townhouse
4/2 Hardie Street (entry in Premier St), Neutral Bay|Neutral Bay|3|2|2|AUCTION 2 May @ 12:00pm|2026-05-02T12:30:00|Townhouse
9/8-12 Winnie Street, Cremorne|Cremorne|3|2|2|Auction- Contact Agent|2026-04-18T12:30:00|Townhouse
Apt 11/163 Avenue Road, Mosman|Mosman|2|1||Auction Guide - $1,400,000|2026-04-16T18:00:00|ApartmentUnitFlat
44/34 Archer Street, Chatswood|Chatswood|2|1|2|Auction - Contact Agent|2026-05-02T09:15:00|ApartmentUnitFlat
3/1A Oswald Street, Mosman|Mosman|2|1||Contact Agent|2026-04-18T11:15:00|ApartmentUnitFlat
2606/10 Atchison Street, St Leonards|St Leonards|1|1|1|Auction | Contact Agent|2026-04-18T14:00:00|ApartmentUnitFlat
906/79-81 Berry Street, North Sydney|North Sydney|1|1||Auction Guide $700,000|2026-04-18T15:45:00|ApartmentUnitFlat
178 Fullers Road, Chatswood|Chatswood|4|2|2|Auction Guide $2,500,000|2026-04-18T15:45:00|House
2/40 Waters Road, Cremorne|Cremorne|3|2|2|Contant Agent|2026-04-25T13:15:00|Townhouse
12/94-96 Wycombe Road, Neutral Bay|Neutral Bay|3|2|2|Auction Guide $1,950,000|2026-05-06T18:00:00|ApartmentUnitFlat
3/6 Rangers Road, Cremorne|Cremorne|2|1|1|Auction (if not sold prior) - Contact Agent|2026-04-18T13:00:00|Townhouse
1507/2B Help Street, Chatswood|Chatswood|2|2|1|Auction Guide $1,300,000|2026-04-18T09:30:00|ApartmentUnitFlat
37/25-29 Devonshire Street, Chatswood|Chatswood|1|1|1|Auction|2026-04-14T18:00:00|ApartmentUnitFlat
126 Northcote Street, Naremburn|Naremburn|3|2|1|Auction Guide: Price on reqest|2026-04-11T13:30:00|House
806/38C Albert Avenue, Chatswood|Chatswood|3|2|2|Auction - Contact Agent|2026-05-09T15:30:00|ApartmentUnitFlat
408/27 Neutral Street, North Sydney||1|1|Auction - Contact Nic Triemstra|2026-04-11T13:45:00|Studio
26 Cambridge Street, Willoughby|Willoughby|3|1|3|Auction - Contact Agent|2026-04-18T10:30:00|House
2013/2A Help Street, Chatswood|Chatswood|3|2|2|Auction Guide $1,800,000|2026-04-15T17:30:00|ApartmentUnitFlat
15/14-16 Freeman Road, Chatswood|Chatswood|1|1|1|Auction - Contact Agent|2026-04-18T09:15:00|ApartmentUnitFlat
106/40 Falcon Street, Crows Nest|Crows Nest|2|2|1|Auction Guide $1,200,000|2026-04-18T09:00:00|ApartmentUnitFlat
3 Methuen Avenue, Mosman|Mosman|5|4|2|Auction | Contact De Brennan|2026-04-28T17:00:00|House
1805/168 Walker Street, North Sydney|North Sydney|3|2|1|Auction|2026-04-28T17:00:00|ApartmentUnitFlat
Level 1, 3/669 Military Road, Mosman|Mosman|2|1|1|Auction|2026-05-02T14:00:00|ApartmentUnitFlat
138/2 Artarmon Road, Willoughby|Willoughby|2|1|1|Auction Guide: $1,000,000|2026-04-11T14:15:00|ApartmentUnitFlat
2/5 Broughton Road, Artarmon|Artarmon|1|1|1|Auction - Contact Agent|2026-04-29T18:00:00|ApartmentUnitFlat
13 Neridah Street, Chatswood|Chatswood|5|3|2|Contact Agent|2026-04-25T17:15:00|House
3/36 Park Road, Naremburn|Naremburn|2|1|1|Auction guide $1,100,000|2026-04-18T15:00:00|ApartmentUnitFlat
3/88 Raglan Street, Mosman|Mosman|2|1||Price Guide $1,000,000|2026-05-09T15:45:00|ApartmentUnitFlat
18/822 Pacific Highway, Chatswood|Chatswood|2|1|1|Auction Guide $900,000|2026-04-11T15:00:00|ApartmentUnitFlat
21/12-16 Berry Street, North Sydney|North Sydney|2|2|1|Price Guide - Contact Agent|2026-04-11T15:15:00|ApartmentUnitFlat
202/31 Bertram Street, Chatswood|Chatswood|2|2|1|Auction - Contact Agent|2026-04-11T16:30:00|ApartmentUnitFlat
17/272-274 Pacific Highway, Greenwich|Greenwich|3|1|1|Auction - Guide $1,050,000|2026-04-11T09:00:00|ApartmentUnitFlat
4 Belcote Road, Longueville|Longueville|5|3|2|Contact Agent|2026-05-02T09:30:00|House
307/8 Waterview Drive, Lane Cove|Lane Cove|2|2|1|Auction this Saturday|2026-04-11T10:00:00|ApartmentUnitFlat
20/7-9 Little Street, Lane Cove|Lane Cove|2|1|1|Auction Guide: $850,000|2026-04-18T13:30:00|ApartmentUnitFlat
4 Warung Street, McMahons Point|McMahons Point|4|3|3|Auction | Contact De Brennan|2026-05-09T15:00:00|House
36 Castle Cove Drive, Castle Cove|Castle Cove|3|2|2|Auction Guide $2,500,000|2026-04-22T18:00:00|House
4 Banksia Close, Lane Cove West|Lane Cove West|3|2|1|Auction Guide $2,300,000|2026-04-18T09:00:00|House
6/12 Elizabeth Parade, Lane Cove|Lane Cove|2|1|1|Auction Guide $900,000|2026-04-18T09:00:00|ApartmentUnitFlat
304/14-18 Finlayson Street, Lane Cove|Lane Cove|1|1|1|Auction Guide $800,000|2026-04-11T16:00:00|ApartmentUnitFlat
411/9-13 Birdwood Avenue, Lane Cove|Lane Cove|1|1|1|Auction - Contact Agent|2026-04-11T10:00:00|ApartmentUnitFlat
6503/1-8 Nield Avenue, Greenwich|Greenwich|2|2|2|Auction Guide: $1,250,000|2026-04-16T17:00:00|ApartmentUnitFlat
2/129 Kurraba Road, Kurraba Point|Kurraba Point|2|1||AUCTION|2026-04-15T17:15:00|ApartmentUnitFlat
4/258 Pacific Highway, Greenwich|Greenwich|2|1|1|Contact Agent|2026-04-18T14:30:00|ApartmentUnitFlat
3/132 Kurraba Road, Kurraba Point|Kurraba Point|3|1|2|Auction Guide $2,500,000|2026-04-29T17:15:00|ApartmentUnitFlat
1 Chowne Place, Middle Cove|Middle Cove|4|2|2|Contact Agent|2026-04-18T12:00:00|House
13/18-20 Longueville Road, Lane Cove|Lane Cove|2|1|1|Auction Guide $850,000|2026-04-18T15:00:00|ApartmentUnitFlat
28 Dunois Street, Longueville|Longueville|2|2|2|Auction Guide: $4,000,000|2026-04-18T16:30:00|House
206/9-13 Mindarie Street, Lane Cove|Lane Cove|2|2|1|Auction Guide $850,000|2026-04-18T16:00:00|ApartmentUnitFlat"""


def normalize_addr(addr):
    a = (addr or '').lower()
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


def extract_guide(price_str):
    """Extract dollar amount from Domain price string."""
    if not price_str:
        return ''
    # Remove auction prefix text
    cleaned = re.sub(r'(?i)^(auction|guide|price guide|auction guide)[:\s\-|]*', '', price_str)
    cleaned = re.sub(r'(?i)(contact agent|price on request|under offer|please contact|contant agent).*', '', cleaned)
    # Find dollar amounts
    amounts = re.findall(r'\$[\d,]+(?:\.\d+)?', cleaned)
    if amounts:
        return amounts[0]
    return ''


def parse_data():
    """Parse raw scraped data into structured records."""
    records = []
    for line in RAW_DATA.strip().split('\n'):
        parts = line.split('|')
        if len(parts) < 7:
            continue
        address = parts[0].strip()
        suburb = parts[1].strip()
        beds = parts[2].strip()
        baths = parts[3].strip()
        parking = parts[4].strip()
        price_raw = parts[5].strip()
        auction_date = parts[6].strip()
        prop_type = parts[7].strip() if len(parts) > 7 else ''

        # Filter to LNS suburbs only
        if suburb.lower() not in LNS_SUBURBS:
            continue

        guide = extract_guide(price_raw)

        records.append({
            'address': address,
            'suburb': suburb,
            'beds': beds,
            'baths': baths,
            'parking': parking,
            'guide': guide,
            'price': price_raw,
            'auctionDate': auction_date,
            'type': prop_type,
            'cancelled': False,
        })

    return records


def cross_reference_guides(records, html):
    """Cross-reference with existing For Sale data to fill missing guides."""
    # Build lookup from sampleListings
    fs_map = {}
    fs_start = html.find('"sampleListings"')
    if fs_start != -1:
        arr_start = html.find('[', fs_start)
        if arr_start != -1:
            depth = 0
            i = arr_start
            while i < len(html):
                if html[i] == '[': depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        chunk = html[arr_start:i+1]
                        for m in re.finditer(r'\{[^}]*?"address"\s*:\s*"([^"]+)"[^}]*?\}', chunk):
                            obj_text = m.group(0)
                            addr = m.group(1)
                            k = normalize_addr(addr)
                            # Extract guidePrice or price
                            gp = re.search(r'"guidePrice"\s*:\s*"([^"]*)"', obj_text)
                            pr = re.search(r'"price"\s*:\s*"([^"]*)"', obj_text)
                            guide = ''
                            if gp and gp.group(1):
                                guide = gp.group(1)
                            elif pr and pr.group(1):
                                amt = re.findall(r'\$[\d,]+', pr.group(1))
                                if amt:
                                    guide = amt[0]
                            if k and guide:
                                fs_map[k] = guide
                        break
                i += 1

    filled = 0
    for rec in records:
        if not rec['guide']:
            k = normalize_addr(rec['address'])
            if k in fs_map:
                rec['guide'] = fs_map[k]
                filled += 1

    print(f"  Cross-referenced: filled {filled} missing guides from For Sale data")
    return records


def check_proping_cancelled(records, html):
    """Check Proping history for cancelled/moved/postponed/sold auctions."""
    # Look for sold/withdrawn/auction_moved in propingHistory
    marker_start = '/* __PROPING_HIST_START__ */'
    marker_end = '/* __PROPING_HIST_END__ */'
    s = html.find(marker_start)
    e = html.find(marker_end)
    if s == -1 or e == -1:
        # Fall back to searching the full propingHistory array
        s = html.find('const propingHistory')
        if s == -1:
            return records
        e = len(html)

    chunk = html[s:e]
    cancelled_addrs = set()

    # Find sold addresses
    for m in re.finditer(r'"address"\s*:\s*"([^"]+)"', chunk):
        pos = m.start()
        section_check = chunk[max(0, pos-200):pos]
        if '"sold"' in section_check:
            cancelled_addrs.add(normalize_addr(m.group(1)))

    # Find auction_moved addresses (cancelled/postponed/moved = all cancelled for us)
    for m in re.finditer(r'"auction_moved"\s*:\s*\[([^\]]*)\]', chunk):
        moved_block = m.group(1)
        for addr_m in re.finditer(r'"address"\s*:\s*"([^"]+)"', moved_block):
            cancelled_addrs.add(normalize_addr(addr_m.group(1)))

    cancelled = 0
    for rec in records:
        k = normalize_addr(rec['address'])
        if k in cancelled_addrs:
            rec['cancelled'] = True
            cancelled += 1

    if cancelled:
        print(f"  Found {cancelled} auctions cancelled/moved/sold (per Proping data)")
    else:
        print(f"  No cancelled auctions found in Proping data ({len(cancelled_addrs)} sold/moved addresses checked)")
    return records


def inject_auctions(html, records):
    """Inject D.upcomingAuctions array into the HTML."""
    # Build the JS array
    js_entries = []
    for r in records:
        entry = {
            'address': r['address'],
            'suburb': r['suburb'],
            'beds': r['beds'],
            'baths': r['baths'],
            'parking': r['parking'],
            'guide': r['guide'],
            'price': r['price'],
            'auctionDate': r['auctionDate'],
            'type': r['type'],
            'cancelled': r['cancelled'],
        }
        js_entries.append(entry)

    js_array = json.dumps(js_entries, indent=2)

    # Check if D.upcomingAuctions already exists
    marker = '// __UPCOMING_AUCTIONS__'
    marker_end = '// __UPCOMING_AUCTIONS_END__'

    if marker in html:
        # Replace existing
        s = html.find(marker)
        e = html.find(marker_end)
        if e != -1:
            e += len(marker_end)
            html = html[:s] + f'{marker}\nD.upcomingAuctions = {js_array};\n{marker_end}' + html[e:]
    else:
        # Insert after D = {...} definition
        insert_point = html.find('_injectSpreadsheetData();')
        if insert_point == -1:
            insert_point = html.find("window.addEventListener('load'")
        if insert_point != -1:
            injection = f'\n{marker}\nD.upcomingAuctions = {js_array};\n{marker_end}\n'
            html = html[:insert_point] + injection + html[insert_point:]

    return html


def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("🏠 Domain Auction Data Injection")
    print(f"   {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print("=" * 60)

    if dry_run:
        print("   🔍 DRY RUN — no changes will be written\n")

    # Parse scraped data
    records = parse_data()
    print(f"\n  📊 {len(records)} LNS auction listings parsed from Domain")

    # Count by Saturday
    from collections import Counter
    sat_counts = Counter()
    for r in records:
        dt = r['auctionDate']
        if dt:
            day = dt.split('T')[0]
            from datetime import date as dt_date
            try:
                d = dt_date.fromisoformat(day)
                if d.weekday() == 5:  # Saturday
                    sat_counts[day] += 1
            except:
                pass

    print("\n  📅 Saturday auction counts:")
    for day in sorted(sat_counts.keys()):
        print(f"     {day}: {sat_counts[day]} auctions")

    # Load app
    with open(APP_PATH) as f:
        html = f.read()

    # Cross-reference price guides from For Sale data
    records = cross_reference_guides(records, html)

    # Check Proping for cancelled auctions
    records = check_proping_cancelled(records, html)

    # Inject
    if not dry_run:
        html = inject_auctions(html, records)
        with open(APP_PATH, 'w') as f:
            f.write(html)
        print(f"\n  ✅ Injected {len(records)} auctions into {APP_PATH}")

        # Also deploy
        for path in [str(_DL.parent / 'index.html'), '/tmp/mm_preview/mazar_martin_app.html']:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(html)
                print(f"  Updated {path}")
            except Exception as e:
                print(f"  ⚠️  {path}: {e}")
    else:
        print(f"\n  (Dry run — {len(records)} auctions would be injected)")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
