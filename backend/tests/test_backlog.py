"""
test_backlog.py — small backlog fixes:
B6 malformed path ids are 404 (not 500), B7 bidding validation, B8 admin listing update idempotence,
B14 price filters honour Buy-now prices, B15 saved searches store city + listing type.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hardening import _app, _client, _listing, _user  # noqa: E402  (same fixtures, same shared DB)


# --- B6 ---------------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body,as_admin", [
    ("POST", "/api/listings/not-an-id/watch", None, False),
    ("POST", "/api/listings/not-an-id/report", {"reason": "spam", "description": "x"}, False),
    ("PUT", "/api/notifications/not-an-id/read", None, False),
    ("PUT", "/api/admin/listings/not-an-id", {"status": "active"}, True),
    ("DELETE", "/api/admin/listings/not-an-id", None, True),
    ("PUT", "/api/admin/users/not-an-id", {"is_suspended": True}, True),
    ("PUT", "/api/admin/verifications/not-an-id?status=approved", None, True),
])
async def test_malformed_ids_are_404(method, path, body, as_admin):
    srv = _app()
    _, token = await _user("b6-admin@backlog.example", role="admin") if as_admin else await _user("b6@backlog.example")
    async with _client(srv, token) as c:
        resp = await c.request(method, path, json=body)
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_watch_unknown_listing_is_404_and_creates_nothing():
    srv = _app()
    from app.db import db
    uid, token = await _user("b6w@backlog.example")
    async with _client(srv, token) as c:
        resp = await c.post("/api/listings/64b64b64b64b64b64b64b64b/watch")
    assert resp.status_code == 404
    assert await db.watchlist.count_documents({"user_id": uid}) == 0


@pytest.mark.asyncio
async def test_watch_toggles_for_a_real_listing():
    srv = _app()
    seller, _ = await _user("b6s@backlog.example")
    _, token = await _user("b6w2@backlog.example")
    lid = await _listing(seller)
    async with _client(srv, token) as c:
        assert (await c.post(f"/api/listings/{lid}/watch")).json()["watching"] is True
        assert (await c.post(f"/api/listings/{lid}/watch")).json()["watching"] is False


# --- B7 ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_best_offer_rejected_when_not_active_or_not_accepted():
    srv = _app()
    seller, _ = await _user("b7s@backlog.example")
    _, token = await _user("b7b@backlog.example")
    inactive = await _listing(seller, status="sold")
    no_offers = await _listing(seller, accepts_best_offer=False)
    ok = await _listing(seller)
    async with _client(srv, token) as c:
        r1 = await c.post(f"/api/listings/{inactive}/best-offer", json={"offer_amount": 20})
        r2 = await c.post(f"/api/listings/{no_offers}/best-offer", json={"offer_amount": 20})
        r3 = await c.post(f"/api/listings/{ok}/best-offer", json={"offer_amount": 20})
    assert r1.status_code == 400 and r1.json()["detail"] == "This listing is not active"
    assert r2.status_code == 400
    assert r3.status_code == 200


@pytest.mark.asyncio
async def test_sniper_bid_below_minimum_is_rejected():
    srv = _app()
    seller, _ = await _user("b7ss@backlog.example")
    _, token = await _user("b7sn@backlog.example")
    lid = await _listing(seller, current_bid=100.0, starting_bid=100.0, bid_count=3)
    async with _client(srv, token) as c:
        low = await c.post(f"/api/listings/{lid}/sniper-bid", json={"max_bid": 100.0})
        ok = await c.post(f"/api/listings/{lid}/sniper-bid", json={"max_bid": 500.0})
    assert low.status_code == 400 and "Minimum bid is $" in low.json()["detail"]
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_losing_bid_keeps_leader_and_records_losers_max():
    """Already correct before B7 — this pins the behaviour (plus the stored amount) down."""
    srv = _app()
    from app.db import db
    seller, _ = await _user("b7ps@backlog.example")
    a_id, a_tok = await _user("b7a@backlog.example", full_name="Alice Leader")
    _, b_tok = await _user("b7b2@backlog.example", full_name="Bob Loser")
    lid = await _listing(seller, listing_type="auction", buy_it_now_price=None, accepts_best_offer=False)
    async with _client(srv, a_tok) as c:
        assert (await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 100.0})).status_code == 200
    async with _client(srv, b_tok) as c:
        resp = await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 50.0})
    assert resp.json()["is_winning"] is False
    from bson import ObjectId
    listing = await db.listings.find_one({"_id": ObjectId(lid)})
    assert listing["highest_bidder_name"] == "Alice Leader"
    assert str(listing["highest_bidder_id"]) == a_id
    assert listing["highest_bidder_max_bid"] == 100.0
    bob_bid = await db.bids.find_one({"listing_id": lid, "bidder_name": "Bob Loser"})
    assert bob_bid["amount"] == 50.0 and bob_bid["max_bid"] == 50.0


# --- B8 ---------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_update_with_unchanged_status_is_200_and_silent():
    srv = _app()
    from app.db import db
    seller, _ = await _user("b8s@backlog.example")
    _, admin = await _user("b8a@backlog.example", role="admin")
    lid = await _listing(seller, status="pending")
    async with _client(srv, admin) as c:
        first = await c.put(f"/api/admin/listings/{lid}", json={"status": "active"})
        second = await c.put(f"/api/admin/listings/{lid}", json={"status": "active"})
        missing = await c.put("/api/admin/listings/64b64b64b64b64b64b64b64b", json={"status": "active"})
    assert first.status_code == 200 and second.status_code == 200
    assert missing.status_code == 404
    assert await db.notifications.count_documents({"user_id": seller, "type": "listing_status"}) == 1


# --- B14 --------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_price_filters_use_buy_now_price_for_fixed_price_listings():
    srv = _app()
    seller, _ = await _user("b14@backlog.example")
    fixed = await _listing(seller, title="B14 fixed lamp", listing_type="fixed_price", starting_bid=0.0,
                           current_bid=0.0, buy_it_now_price=75.0)
    auction = await _listing(seller, title="B14 auction lamp", listing_type="auction", buy_it_now_price=None,
                             current_bid=300.0)
    async with _client(srv) as c:
        def ids(resp):
            return {x["_id"] for x in resp.json()["listings"]}
        inside = await c.get("/api/listings", params={"min_price": 50, "max_price": 100, "q": "B14"})
        above = await c.get("/api/listings", params={"min_price": 200, "q": "B14"})
        below = await c.get("/api/listings", params={"max_price": 100, "q": "B14"})
    assert ids(inside) == {fixed}
    assert ids(above) == {auction}
    assert ids(below) == {fixed}


# --- B15 --------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_saved_search_stores_city_and_listing_type_and_alerts_honour_them():
    srv = _app()
    from app.search_alerts import search_matches
    _, token = await _user("b15@backlog.example")
    async with _client(srv, token) as c:
        created = await c.post("/api/saved-searches", json={
            "name": "Victoria buy-now", "query": "", "city": "Victoria", "listing_type": "fixed_price"})
        bad = await c.post("/api/saved-searches", json={"name": "x", "query": "", "listing_type": "nope"})
        listed = (await c.get("/api/saved-searches")).json()["saved_searches"]
    assert created.status_code == 200 and bad.status_code == 422
    saved = next(s for s in listed if s["_id"] == created.json()["id"])
    assert saved["city"] == "Victoria" and saved["listing_type"] == "fixed_price"
    ok = {"city": "Victoria", "listing_type": "fixed_price", "title": "t"}
    assert search_matches(saved, ok, 10)
    assert not search_matches(saved, {**ok, "city": "Kelowna"}, 10)
    assert not search_matches(saved, {**ok, "listing_type": "auction"}, 10)
