"""
test_9f_private.py — Phase 9f, private (invite-only) listings (R51 / FR-31, Q007): only the seller,
invitees and admins can see or bid; never listed anywhere public; invite links expire with the
listing; no ratings.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hardening import _app, _client, _listing, _user  # noqa: E402  (same fixtures, same shared DB)


async def _private(seller, invitees=(), **extra):
    fields = {"listing_type": "private", "buy_it_now_price": None, "accepts_best_offer": False,
              "invitees": list(invitees), "invite_token": "tok-" + seller, "category": "Tools",
              "invite_expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), **extra}
    return await _listing(seller, **fields)


@pytest.mark.asyncio
async def test_create_private_listing_invites_by_email_and_needs_accounts():
    srv = _app()
    _, token = await _user("seller@9f.example")
    friend, _ = await _user("friend@9f.example")
    form = {"title": "9F private lamp", "category": "Home & Garden", "description": "Invite only",
            "condition": "good", "city": "Victoria", "starting_bid": 5, "listing_type": "private",
            "buy_it_now_price": 99}
    async with _client(srv, token) as c:
        unknown = await c.post("/api/listings", json={**form, "invitees": ["nobody@9f.example"]})
        ok = await c.post("/api/listings", json={**form, "invitees": ["FRIEND@9f.example"]})
    assert unknown.status_code == 422 and "nobody@9f.example" in unknown.json()["detail"]
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["status"] == "pending"  # still needs admin approval
    assert body["invitees"] == [friend] and len(body["invite_token"]) >= 20
    assert body["invite_expires_at"] == body["end_time"]
    assert body["buy_it_now_price"] is None  # auction mechanics only


@pytest.mark.asyncio
async def test_private_listing_is_hidden_from_every_public_list():
    srv = _app()
    seller, _ = await _user("hidden-s@9f.example")
    public = await _listing(seller, title="9F public twin", category="Tools")
    private = await _private(seller, title="9F secret twin", bid_count=50,
                             end_time=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    async with _client(srv) as c:
        browse = (await c.get("/api/listings", params={"q": "9F"})).json()["listings"]
        typed = (await c.get("/api/listings", params={"listing_type": "private"})).json()["listings"]
        by_seller = (await c.get("/api/listings", params={"seller_id": seller})).json()["listings"]
        featured = (await c.get("/api/listings/featured")).json()["listings"]
        ending = (await c.get("/api/listings/ending-soon")).json()["listings"]
        related = (await c.get(f"/api/listings/{public}")).json()["related_items"]
        profile = (await c.get(f"/api/users/{seller}/profile")).json()
    for found in (browse, typed, by_seller, featured, ending, related):
        assert private not in [l["_id"] for l in found]
    assert public in [l["_id"] for l in browse]
    assert profile["active_listings"] == 1


@pytest.mark.asyncio
async def test_only_seller_invitees_and_admins_can_view_or_bid():
    srv = _app()
    seller, s_tok = await _user("view-s@9f.example")
    guest, g_tok = await _user("view-g@9f.example")
    _, x_tok = await _user("view-x@9f.example")
    _, a_tok = await _user("view-a@9f.example", role="admin")
    lid = await _private(seller, [guest])
    async with _client(srv) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 404
    async with _client(srv, x_tok) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 404
        assert (await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 20})).status_code == 404
        assert (await c.post(f"/api/listings/{lid}/sniper-bid", json={"max_bid": 20})).status_code == 404
        assert (await c.post(f"/api/listings/{lid}/watch")).status_code == 404
    async with _client(srv, g_tok) as c:
        seen = await c.get(f"/api/listings/{lid}")
        assert seen.status_code == 200
        assert "invite_token" not in seen.json() and "invitees" not in seen.json()
        bid = await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 20})
        assert bid.status_code == 200, bid.text
    async with _client(srv, s_tok) as c:
        assert (await c.get(f"/api/listings/{lid}")).json()["invite_token"] == "tok-" + seller
    async with _client(srv, a_tok) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 200


@pytest.mark.asyncio
async def test_invite_link_lets_a_member_in_and_expires_with_the_listing():
    srv = _app()
    seller, s_tok = await _user("link-s@9f.example")
    newcomer, n_tok = await _user("link-n@9f.example")
    lid = await _private(seller, invite_token="link-token-9f")
    ended = await _private(seller, invite_token="link-token-9f-old",
                           invite_expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
    async with _client(srv) as anon:
        assert (await anon.post("/api/invites/link-token-9f/accept")).status_code == 401  # needs an account
    async with _client(srv, n_tok) as c:
        assert (await c.post("/api/invites/nope/accept")).status_code == 404
        assert (await c.post("/api/invites/link-token-9f-old/accept")).status_code == 410
        r = await c.post("/api/invites/link-token-9f/accept")
        assert r.status_code == 200 and r.json()["listing_id"] == lid
        assert (await c.get(f"/api/listings/{lid}")).status_code == 200
    assert ended
    async with _client(srv, s_tok) as c:
        invites = (await c.get(f"/api/listings/{lid}/invites")).json()
        assert [i["user_id"] for i in invites["invitees"]] == [newcomer]
        fresh = (await c.post(f"/api/listings/{lid}/invite-link")).json()
    assert fresh["invite_token"] != "link-token-9f"
    async with _client(srv, n_tok) as c:
        assert (await c.post("/api/invites/link-token-9f/accept")).status_code == 404  # old link is dead


@pytest.mark.asyncio
async def test_seller_manages_invitees_by_email_or_id():
    srv = _app()
    seller, s_tok = await _user("manage-s@9f.example")
    friend, f_tok = await _user("manage-f@9f.example")
    _, x_tok = await _user("manage-x@9f.example")
    lid = await _private(seller)
    public = await _listing(seller)
    async with _client(srv, x_tok) as c:
        assert (await c.get(f"/api/listings/{lid}/invites")).status_code == 404
    async with _client(srv, s_tok) as c:
        assert (await c.post(f"/api/listings/{lid}/invites", json={"identifier": "ghost@9f.example"})).status_code == 404
        assert (await c.post(f"/api/listings/{lid}/invites", json={"identifier": seller})).status_code == 400
        assert (await c.post(f"/api/listings/{public}/invites", json={"identifier": friend})).status_code == 400
        added = await c.post(f"/api/listings/{lid}/invites", json={"identifier": "manage-f@9f.example"})
        assert added.status_code == 201
        assert added.json()["invitees"][0]["full_name"] == "Manage-F"
    async with _client(srv, f_tok) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 200
    async with _client(srv, s_tok) as c:
        removed = await c.delete(f"/api/listings/{lid}/invites/{friend}")
        assert removed.json()["invitees"] == []
    async with _client(srv, f_tok) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 404


@pytest.mark.asyncio
async def test_private_deals_cannot_be_rated():
    srv = _app()
    from app.db import db
    seller, _ = await _user("rate-s@9f.example")
    buyer, b_tok = await _user("rate-b@9f.example")
    lid = await _private(seller, [buyer], status="sold")
    tx = await db.transactions.insert_one({"listing_id": lid, "buyer_id": buyer, "seller_id": seller,
                                           "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()})
    async with _client(srv, b_tok) as c:
        r = await c.post(f"/api/transactions/{tx.inserted_id}/feedback", json={"rating": "positive", "comment": "great"})
    assert r.status_code == 403 and "Private" in r.json()["detail"]
    assert await db.feedback.count_documents({"listing_id": lid}) == 0


@pytest.mark.asyncio
async def test_private_listing_never_triggers_saved_search_alerts():
    _app()
    from app.db import db
    from app.search_alerts import alert_saved_searches
    seller, _ = await _user("alert-s@9f.example")
    watcher, _ = await _user("alert-w@9f.example")
    await db.saved_searches.insert_one({"user_id": watcher, "name": "anything", "query": "", "alerts_enabled": True})
    lid = await _private(seller, title="9F alert")
    listing = await db.listings.find_one({"title": "9F alert"})
    assert await alert_saved_searches(listing) == 0
    assert not await db.notifications.find_one({"user_id": watcher, "listing_id": lid})
