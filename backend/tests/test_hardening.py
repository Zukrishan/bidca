"""
test_hardening.py — pre-launch fixes:
B1 Socket.IO notification rooms are bound to the authenticated user,
B3 banned/suspended accounts lose access immediately (and login doesn't leak account state),
B10 auth cookies are Secure in production,
B2 closer notifications are pushed in real time,
B4/B5 Buy It Now and accepted best offers finish a sale the same way, exactly once.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import bcrypt
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "bidca_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")

import mongomock_motor  # type: ignore

_mock_client = mongomock_motor.AsyncMongoMockClient()
PASSWORD = "Hardening123!"


def _app():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server as srv
    return srv


async def _user(email, **extra):
    from app.db import db
    from app.security import create_access_token
    await db.users.delete_many({"email": email})
    doc = {
        "email": email, "full_name": email.split("@")[0].title(), "city": "Victoria", "role": "user",
        "password_hash": bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode(),
        "verification_status": "unverified", "email_verified": True, "total_sales": 0, "total_sales_amount": 0,
        "total_purchases": 0, "created_at": datetime.now(timezone.utc).isoformat(), **extra,
    }
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    return uid, create_access_token(uid, email)


async def _listing(seller_id, **extra):
    from app.db import db
    doc = {
        "title": "HARD item", "description": "x", "category": "Tools", "seller_id": seller_id,
        "status": "active", "listing_type": "auction_bin", "starting_bid": 10.0, "current_bid": 10.0,
        "buy_it_now_price": 50.0, "bid_count": 0, "accepts_best_offer": True,
        "end_time": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(), **extra,
    }
    return str((await db.listings.insert_one(doc)).inserted_id)


def _client(srv, token=None):
    from httpx import AsyncClient, ASGITransport
    return AsyncClient(transport=ASGITransport(app=srv.fastapi_app), base_url="http://test",
                       cookies={"access_token": token} if token else None)


# --- B3: banned / suspended -------------------------------------------------------------

@pytest.mark.asyncio
async def test_banned_and_suspended_tokens_stop_working_immediately():
    srv = _app()
    for flag in ("is_banned", "is_suspended"):
        _, token = await _user(f"{flag}@hard.example", **{flag: True})
        async with _client(srv, token) as c:
            resp = await c.get("/api/auth/me")
        assert resp.status_code == 403, flag


@pytest.mark.asyncio
async def test_refresh_refused_for_banned_user():
    srv = _app()
    from app.security import create_refresh_token
    uid, _ = await _user("refresh-banned@hard.example", is_banned=True)
    async with _client(srv) as c:
        c.cookies.set("refresh_token", create_refresh_token(uid))
        assert (await c.post("/api/auth/refresh")).status_code == 403


@pytest.mark.asyncio
async def test_login_does_not_reveal_ban_without_the_password():
    srv = _app()
    await _user("leak@hard.example", is_banned=True)
    async with _client(srv) as c:
        wrong = await c.post("/api/auth/login", json={"email": "leak@hard.example", "password": "nope"})
        right = await c.post("/api/auth/login", json={"email": "leak@hard.example", "password": PASSWORD})
    assert wrong.status_code == 401  # same as any wrong password
    assert right.status_code == 403


# --- B10: secure cookies ----------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("env,override,secure", [
    ("production", None, True), ("development", None, False), ("production", "false", False), ("", "true", True),
    ("production", "", True),  # compose passes an empty COOKIE_SECURE when .env leaves it blank
])
async def test_auth_cookie_secure_flag(monkeypatch, env, override, secure):
    srv = _app()
    monkeypatch.setenv("ENV", env)
    if override is None:
        monkeypatch.delenv("COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("COOKIE_SECURE", override)
    await _user("cookie@hard.example")
    async with _client(srv) as c:
        resp = await c.post("/api/auth/login", json={"email": "cookie@hard.example", "password": PASSWORD})
    assert resp.status_code == 200
    cookies = resp.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all(("secure" in h.lower()) is secure for h in cookies), cookies
    assert all("httponly" in h.lower() and "samesite=lax" in h.lower() for h in cookies)


# --- B1: socket notification rooms ------------------------------------------------------

class _FakeSio:
    def __init__(self):
        self.sessions, self.rooms = {}, []

    async def save_session(self, sid, data):
        self.sessions[sid] = data

    async def get_session(self, sid):
        return self.sessions.get(sid, {})

    async def enter_room(self, sid, room):
        self.rooms.append((sid, room))


@pytest.mark.asyncio
async def test_notification_room_is_bound_to_the_authenticated_user():
    _app()
    from app import realtime
    me, token = await _user("socket@hard.example")
    victim, _ = await _user("victim@hard.example")
    fake = _FakeSio()
    with patch.object(realtime, "sio", fake):
        await realtime.connect("authed", {"HTTP_COOKIE": f"access_token={token}"})
        await realtime.connect("anon", {})
        # Asking for someone else's room still only joins your own
        assert (await realtime.join_user_notifications("authed", {"user_id": victim}))["ok"] is True
        assert (await realtime.join_user_notifications("anon", {"user_id": victim}))["ok"] is False
    assert fake.rooms == [("authed", f"user_{me}")]


@pytest.mark.asyncio
async def test_banned_user_socket_is_anonymous():
    _app()
    from app import realtime
    _, token = await _user("socket-banned@hard.example", is_banned=True)
    fake = _FakeSio()
    with patch.object(realtime, "sio", fake):
        await realtime.connect("s", {"HTTP_COOKIE": f"access_token={token}"})
        assert (await realtime.join_user_notifications("s", {}))["ok"] is False
    assert fake.rooms == []


# --- B4/B5: sales -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_buy_now_completes_the_sale_exactly_once():
    srv = _app()
    from app.db import db
    seller, _ = await _user("bin-seller@hard.example")
    buyer, buyer_token = await _user("bin-buyer@hard.example")
    _, other_token = await _user("bin-other@hard.example")
    lid = await _listing(seller)
    with patch("app.sales.broadcast_auction_end", new_callable=AsyncMock) as emit:
        async with _client(srv, buyer_token) as c:
            assert (await c.post(f"/api/listings/{lid}/buy-now")).status_code == 200
        async with _client(srv, other_token) as c:
            assert (await c.post(f"/api/listings/{lid}/buy-now")).status_code == 400  # not active any more
    assert await db.transactions.count_documents({"listing_id": lid}) == 1
    from bson import ObjectId
    seller_doc = await db.users.find_one({"_id": ObjectId(seller)})
    assert seller_doc["total_sales"] == 1 and seller_doc["total_sales_amount"] == 50.0  # was never updated
    payload = emit.await_args.args[1]
    assert payload["status"] == "sold" and payload["winner_id"] == buyer and payload["price"] == 50.0


@pytest.mark.asyncio
async def test_concurrent_sale_only_one_wins():
    _app()
    from app.db import db
    from app.sales import complete_sale
    from fastapi import HTTPException
    seller, _ = await _user("race-seller@hard.example")
    a, _ = await _user("race-a@hard.example")
    b, _ = await _user("race-b@hard.example")
    lid = await _listing(seller)
    listing = await db.listings.find_one({"title": "HARD item", "seller_id": seller})
    with patch("app.sales.broadcast_auction_end", new_callable=AsyncMock):
        await complete_sale(listing, a, 50.0, "buy_it_now")
        with pytest.raises(HTTPException) as exc:
            await complete_sale(listing, b, 50.0, "buy_it_now")  # stale copy still says "active"
    assert exc.value.status_code == 409
    assert await db.transactions.count_documents({"listing_id": lid}) == 1


@pytest.mark.asyncio
async def test_accepting_an_offer_records_the_sale():
    srv = _app()
    from app.db import db
    seller, seller_token = await _user("offer-seller@hard.example")
    buyer, buyer_token = await _user("offer-buyer@hard.example")
    _, rival_token = await _user("offer-rival@hard.example")
    lid = await _listing(seller, listing_type="fixed_price")
    async with _client(srv, buyer_token) as c:
        assert (await c.post(f"/api/listings/{lid}/best-offer", json={"offer_amount": 40})).status_code == 200
    async with _client(srv, rival_token) as c:
        assert (await c.post(f"/api/listings/{lid}/best-offer", json={"offer_amount": 35})).status_code == 200
    offer = await db.offers.find_one({"listing_id": lid, "amount": 40})
    rival = await db.offers.find_one({"listing_id": lid, "amount": 35})
    with patch("app.sales.broadcast_auction_end", new_callable=AsyncMock):
        async with _client(srv, seller_token) as c:
            ok = await c.put(f"/api/offers/{offer['_id']}/respond", params={"action": "accept"})
            again = await c.put(f"/api/offers/{offer['_id']}/respond", params={"action": "accept"})
            late = await c.put(f"/api/offers/{rival['_id']}/respond", params={"action": "accept"})
    assert ok.status_code == 200, ok.text
    assert again.status_code == 400
    assert late.status_code == 400  # auto-declined when the other offer won
    tx = await db.transactions.find_one({"listing_id": lid})
    assert tx and tx["type"] == "best_offer" and tx["buyer_id"] == buyer and tx["amount"] == 40
    assert (await db.listings.find_one({"title": "HARD item", "seller_id": seller}))["status"] == "sold"


# --- B2: closer notifications are pushed -------------------------------------------------

@pytest.mark.asyncio
async def test_closer_notifications_are_pushed_json_safe():
    _app()
    from app import closer
    from app.db import db
    pushed = []

    async def fake_push(user_id, notification):
        pushed.append((user_id, json.dumps(notification)))

    with patch("app.realtime.send_user_notification", fake_push):
        await closer._create_notification(db, "u-closer", "auction_won", "You won", "l1")
    assert pushed and pushed[0][0] == "u-closer"
