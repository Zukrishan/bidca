"""
seed_demo.py — fill a local BidCa API with realistic demo data, through the API itself.

Creates a seller and two buyers, 12 listings (auctions, buy-now, auction + buy-now) across BC,
approves them as admin, places some bids, and leaves one listing pending (to check it stays
hidden). With MONGO_URL/DB_NAME set it also pulls a few auctions' end_time into the next hours
so "Ending soon" has content (duration_days can't go below 1 through the API).

Dev only: logs in as the seeded admin (ADMIN_EMAIL / ADMIN_PASSWORD, default admin123), which
the server refuses to create when ENV=production.

    API_URL=http://localhost:8100 MONGO_URL=mongodb://localhost:27017 DB_NAME=bidca \
        python scripts/seed_demo.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API = os.environ.get("API_URL", "http://localhost:8100").rstrip("/") + "/api"
ADMIN = (os.environ.get("ADMIN_EMAIL", "admin@bidca.ca"), os.environ.get("ADMIN_PASSWORD", "admin123"))
PASSWORD = "DemoPass123!"


def img(slug):
    return f"https://picsum.photos/seed/bidca-{slug}/800/800"


LISTINGS = [
    # title, category, subcategory, city, type, starting, bin, condition, slug
    ("DeWalt 20V cordless drill kit with 2 batteries", "Tools & Equipment", "Power Tools", "Kamloops", "auction", 60, None, "like_new", "drill"),
    ("Specialized Allez road bike, 54cm", "Sports & Outdoors", "Cycling", "Nanaimo", "auction", 350, None, "good", "bike"),
    ("Herman Miller Aeron chair, size B", "Home & Garden", "Furniture", "Victoria", "auction_bin", 300, 650, "good", "chair"),
    ("Vintage Panasonic boombox RX-5050", "Electronics", "Audio", "Vancouver", "auction", 80, None, "fair", "boombox"),
    ("Yamaha FG830 acoustic guitar with hard case", "Musical Instruments", "Guitars", "Coquitlam", "auction", 150, None, "like_new", "guitar"),
    ("Le Creuset 5.5 qt Dutch oven", "Home & Garden", "Kitchen", "Burnaby", "fixed_price", 250, 310, "new", "dutchoven"),
    ("Sony A7 III camera body, low shutter count", "Electronics", "Cameras", "Richmond", "fixed_price", 1200, 1450, "like_new", "camera"),
    ("Breville Barista Express espresso machine", "Home & Garden", "Appliances", "Surrey", "auction", 250, None, "good", "espresso"),
    ("Solid oak coffee table, handmade", "Home & Garden", "Furniture", "Whistler", "auction", 150, None, "new", "table"),
    ("Anon M4 ski goggles with spare lens", "Sports & Outdoors", "Winter Sports", "Kelowna", "auction_bin", 90, 160, "like_new", "goggles"),
    ("Lot of 10 classic rock vinyl LPs", "Books & Media", "Music", "Prince George", "fixed_price", 100, 120, "good", "vinyl"),
    ("LEGO Technic Porsche 911 GT3 RS, complete", "Toys & Games", "LEGO", "Penticton", "auction", 220, None, "good", "lego"),
]


def session_for(email, password, register=None):
    s = requests.Session()
    if register:
        r = s.post(f"{API}/auth/register", json={"email": email, "password": password, **register})
        if r.status_code not in (200, 201, 400):
            sys.exit(f"register {email}: {r.status_code} {r.text}")
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        sys.exit(f"login {email}: {r.status_code} {r.text}")
    return s


def main():
    admin = session_for(*ADMIN)
    seller = session_for("mark@demo.bidca.ca", PASSWORD,
                         {"full_name": "Mark Thompson", "city": "Kamloops", "postal_code": "V2C 1A1"})
    buyers = [
        session_for("jess@demo.bidca.ca", PASSWORD, {"full_name": "Jess Nguyen", "city": "Vancouver", "postal_code": "V6B 1A1"}),
        session_for("raj@demo.bidca.ca", PASSWORD, {"full_name": "Raj Patel", "city": "Surrey", "postal_code": "V3T 1A1"}),
    ]

    # Registration now requires email confirmation before bidding/selling; skip it for demo users.
    if os.environ.get("MONGO_URL"):
        from pymongo import MongoClient
        MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "bidca")].users.update_many(
            {"email": {"$regex": "@demo\\.bidca\\.ca$"}}, {"$set": {"email_verified": True}})

    created = []
    for title, cat, sub, city, ltype, start, bin_price, cond, slug in LISTINGS:
        body = {
            "title": title, "category": cat, "subcategory": sub, "city": city,
            "description": f"{title}. Local pickup in {city}, BC. Message me with any questions.",
            "starting_bid": start, "buy_it_now_price": bin_price, "listing_type": ltype,
            "condition": cond, "duration_days": 3 if ltype != "fixed_price" else 7,
            "images": [img(slug), img(slug + "-2")],
        }
        r = seller.post(f"{API}/listings", json=body)
        if r.status_code != 201:
            sys.exit(f"create {title}: {r.status_code} {r.text}")
        created.append(r.json())

    for listing in created:
        r = admin.put(f"{API}/admin/listings/{listing['_id']}", json={"status": "active"})
        if r.status_code != 200:
            sys.exit(f"approve {listing['title']}: {r.status_code} {r.text}")

    # A few competing proxy bids so cards show bid counts and the detail page has history.
    auctions = [l for l in created if l["listing_type"] != "fixed_price"]
    for i, listing in enumerate(auctions[:6]):
        for j, buyer in enumerate(buyers):
            amount = listing["starting_bid"] + 10 * (i + 1) + 15 * j
            buyer.post(f"{API}/listings/{listing['_id']}/bid", json={"max_bid": amount})

    # One listing left pending: must never appear on public pages (contract D8).
    pending = seller.post(f"{API}/listings", json={
        "title": "PENDING demo item — should not be public", "category": "Other", "city": "Vernon",
        "description": "Awaiting admin approval.", "starting_bid": 10, "images": [img("pending")],
    }).json()

    ending = []
    if os.environ.get("MONGO_URL"):
        from bson import ObjectId
        from pymongo import MongoClient
        db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "bidca")]
        now = datetime.now(timezone.utc)
        for listing, minutes in zip(auctions[:3], (25, 50, 150)):
            db.listings.update_one({"_id": ObjectId(listing["_id"])},
                                   {"$set": {"end_time": (now + timedelta(minutes=minutes)).isoformat()}})
            ending.append(listing["_id"])

    print(f"seller_id={created[0]['seller_id']}")
    print(f"listing_ids={','.join(l['_id'] for l in created)}")
    print(f"pending_id={pending['_id']}")
    print(f"ending_soon_ids={','.join(ending)}")


if __name__ == "__main__":
    main()
