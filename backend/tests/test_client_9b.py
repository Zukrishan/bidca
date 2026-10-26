"""
test_client_9b.py — Phase 9b, the client-source quick fixes (docs/source/BIDCA.txt):
R30 no money (no shipping, no `pending_payment`), R31 12 h lockout, R35 won/lost messages,
R36 outbid email, R37 Best Offer on fixed-price listings only.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hardening import _app, _client, _listing, _user  # noqa: E402  (same fixtures, same shared DB)


def _sent_to(mock, email):
    return [c.kwargs for c in mock.await_args_list if c.kwargs.get("to") == email]


# --- R31 lockout --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("env_hours,expected_hours", [(None, 12), ("1", 1)])
async def test_five_failed_logins_lock_for_the_configured_time(monkeypatch, env_hours, expected_hours):
    srv = _app()
    from app.db import db
    if env_hours is None:
        monkeypatch.delenv("LOGIN_LOCKOUT_HOURS", raising=False)
    else:
        monkeypatch.setenv("LOGIN_LOCKOUT_HOURS", env_hours)
    email = f"lock{expected_hours}@9b.example"
    await _user(email)
    await db.login_attempts.delete_many({})
    async with _client(srv) as c:
        for _ in range(5):
            await c.post("/api/auth/login", json={"email": email, "password": "wrong"})
        locked = await c.post("/api/auth/login", json={"email": email, "password": "wrong"})
    assert locked.status_code == 429
    attempts = await db.login_attempts.find_one({"locked_until": {"$exists": True}})
    left = datetime.fromisoformat(attempts["locked_until"]) - datetime.now(timezone.utc)
    assert timedelta(hours=expected_hours) - timedelta(minutes=1) < left <= timedelta(hours=expected_hours)


# --- R30 / R37 listing create --------------------------------------------------------------

def _new_listing(**extra):
    return {"title": "9B lamp", "category": "Home & Garden", "description": "A lamp", "city": "Victoria",
            "starting_bid": 20, **extra}


@pytest.mark.asyncio
async def test_create_listing_has_no_shipping_and_offers_only_on_fixed_price():
    srv = _app()
    _, token = await _user("seller@9b.example")
    async with _client(srv, token) as c:
        # An old client still sending shipping fields is accepted; they are not stored
        auction = await c.post("/api/listings", json=_new_listing(
            shipping_cost=15, shipping_from="Surrey", accepts_best_offer=True))
        fixed = await c.post("/api/listings", json=_new_listing(
            listing_type="fixed_price", buy_it_now_price=40, accepts_best_offer=True))
    assert auction.status_code == 201, auction.text
    body = auction.json()
    assert "shipping_cost" not in body and "shipping_from" not in body
    assert body["accepts_best_offer"] is False  # no negotiating an auction (FR-28)
    assert fixed.json()["accepts_best_offer"] is True


@pytest.mark.asyncio
async def test_best_offer_refused_on_auctions_even_if_flagged():
    srv = _app()
    seller, _ = await _user("offer-s@9b.example")
    _, token = await _user("offer-b@9b.example")
    legacy = await _listing(seller, listing_type="auction_bin", accepts_best_offer=True)
    fixed = await _listing(seller, listing_type="fixed_price", accepts_best_offer=True)
    async with _client(srv, token) as c:
        refused = await c.post(f"/api/listings/{legacy}/best-offer", json={"offer_amount": 20})
        ok = await c.post(f"/api/listings/{fixed}/best-offer", json={"offer_amount": 20})
    assert refused.status_code == 400
    assert ok.status_code == 200


# --- R36 outbid email ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_outbid_bidder_is_emailed_immediately():
    srv = _app()
    seller, _ = await _user("ob-s@9b.example")
    _, a_tok = await _user("ob-a@9b.example")
    _, b_tok = await _user("ob-b@9b.example")
    lid = await _listing(seller, title="Outbid <b>lamp</b>", listing_type="auction", buy_it_now_price=None)
    with patch("app.email.send_email", new_callable=AsyncMock) as send:
        async with _client(srv, a_tok) as c:
            assert (await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 20})).status_code == 200
        async with _client(srv, b_tok) as c:
            assert (await c.post(f"/api/listings/{lid}/bid", json={"max_bid": 60})).json()["is_winning"] is True
    mails = _sent_to(send, "ob-a@9b.example")
    assert len(mails) == 1
    assert mails[0]["subject"].startswith("You've been outbid")
    assert "<b>lamp</b>" not in mails[0]["html"]  # user input is escaped
    assert f"/auctions/{lid}" in mails[0]["html"]
    assert not _sent_to(send, "ob-b@9b.example")


# --- R30 / R35 closing ---------------------------------------------------------------------

async def _bid(listing_id, bidder_id, amount):
    from app.db import db
    await db.bids.insert_one({"listing_id": listing_id, "bidder_id": bidder_id, "amount": amount,
                              "created_at": datetime.now(timezone.utc).isoformat()})


@pytest.mark.asyncio
async def test_close_tells_winner_seller_and_every_losing_bidder():
    _app()
    from app.closer import run_once
    from app.db import db
    seller, _ = await _user("close-s@9b.example")
    winner, _ = await _user("close-w@9b.example")
    loser, _ = await _user("close-l@9b.example")
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    lid = await _listing(seller, title="Close lamp", listing_type="auction", buy_it_now_price=None,
                         end_time=past, highest_bidder_id=winner, current_bid=80.0, bid_count=3)
    await _bid(lid, loser, 50.0)
    await _bid(lid, winner, 80.0)
    await _bid(lid, loser, 70.0)  # two bids from the loser: still one notice
    with patch("app.email.send_email", new_callable=AsyncMock) as send:
        await run_once(db)
    won = await db.notifications.find_one({"user_id": winner, "type": "auction_won", "listing_id": lid})
    assert won and won["message"].startswith("You won!")
    assert await db.notifications.count_documents({"user_id": loser, "type": "auction_lost", "listing_id": lid}) == 1
    assert await db.notifications.count_documents({"user_id": winner, "type": "auction_lost", "listing_id": lid}) == 0
    tx = await db.transactions.find_one({"listing_id": lid})
    assert tx["status"] == "open"  # no money involved (NFR-07)
    subjects = {c.kwargs["subject"] for c in send.await_args_list}
    assert "You won the bid for Close lamp" in subjects
    assert "Your item Close lamp has a winning bidder" in subjects


@pytest.mark.asyncio
async def test_unsold_auction_tells_bidders_they_did_not_win():
    _app()
    from app.closer import run_once
    from app.db import db
    seller, _ = await _user("unsold-s@9b.example")
    bidder, _ = await _user("unsold-b@9b.example")
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    lid = await _listing(seller, title="Reserve lamp", listing_type="auction", buy_it_now_price=None,
                         end_time=past, highest_bidder_id=bidder, current_bid=30.0, reserve_price=100.0,
                         bid_count=1)
    await _bid(lid, bidder, 30.0)
    with patch("app.email.send_email", new_callable=AsyncMock):
        await run_once(db)
    assert (await db.listings.find_one({"_id": ObjectId(lid)}))["status"] == "unsold"
    assert await db.notifications.count_documents({"user_id": bidder, "type": "auction_lost", "listing_id": lid}) == 1


@pytest.mark.asyncio
async def test_buy_now_emails_both_sides_and_tells_bidders():
    srv = _app()
    from app.db import db
    seller, _ = await _user("bn-s@9b.example")
    buyer, b_tok = await _user("bn-b@9b.example")
    bidder, _ = await _user("bn-x@9b.example")
    lid = await _listing(seller, title="BIN lamp", listing_type="auction_bin", bid_count=1)
    await _bid(lid, bidder, 12.0)
    with patch("app.sales.broadcast_auction_end", new_callable=AsyncMock), \
         patch("app.email.send_email", new_callable=AsyncMock) as send:
        async with _client(srv, b_tok) as c:
            assert (await c.post(f"/api/listings/{lid}/buy-now")).status_code == 200
    assert (await db.transactions.find_one({"listing_id": lid}))["status"] == "open"
    assert _sent_to(send, "bn-s@9b.example") and _sent_to(send, "bn-b@9b.example")
    assert await db.notifications.count_documents({"user_id": bidder, "type": "auction_lost", "listing_id": lid}) == 1
