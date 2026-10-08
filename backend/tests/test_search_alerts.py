"""test_search_alerts.py — FR-13: saved-search alerts when a listing becomes active."""

from __future__ import annotations

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


def _app():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server as srv
    return srv


def _client(srv, token=None):
    from httpx import AsyncClient, ASGITransport
    return AsyncClient(transport=ASGITransport(app=srv.fastapi_app), base_url="http://test",
                       cookies={"access_token": token} if token else None)


async def _user(email, **extra):
    from app.db import db
    from app.security import create_access_token
    await db.users.delete_many({"email": email})
    doc = {
        "email": email, "full_name": email.split("@")[0].title(), "city": "Victoria", "role": "user",
        "password_hash": bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(), "verification_status": "unverified",
        "created_at": datetime.now(timezone.utc).isoformat(), **extra,
    }
    uid = str((await db.users.insert_one(doc)).inserted_id)
    return uid, create_access_token(uid, email)


async def _pending(seller_id, **extra):
    from app.db import db
    doc = {
        "title": "Vintage Road Bike", "description": "Steel frame, C++ sticker", "category": "Sports",
        "seller_id": seller_id, "status": "pending", "listing_type": "auction", "starting_bid": 100.0,
        "current_bid": 100.0, "bid_count": 0,
        "end_time": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(), **extra,
    }
    return str((await db.listings.insert_one(doc)).inserted_id)


async def _reset():
    from app.db import db
    for coll in ("saved_searches", "saved_search_alerts", "notifications", "listings"):
        await db[coll].delete_many({})


async def _save(srv, token, **body):
    body.setdefault("name", "My search")
    body.setdefault("query", "")
    async with _client(srv, token) as c:
        resp = await c.post("/api/saved-searches", json=body)
    assert resp.status_code == 200
    return resp.json()["id"]


async def _approve(srv, admin_token, listing_id):
    async with _client(srv, admin_token) as c:
        return await c.put(f"/api/admin/listings/{listing_id}", json={"status": "active"})


async def _setup():
    await _reset()
    seller, seller_tok = await _user("seller@alerts.example")
    saver, saver_tok = await _user("saver@alerts.example")
    _, admin_tok = await _user("admin@alerts.example", role="admin")
    return seller, seller_tok, saver, saver_tok, admin_tok


async def _notes(user_id):
    from app.db import db
    return [n async for n in db.notifications.find({"user_id": user_id, "type": "saved_search_match"})]


@pytest.mark.asyncio
async def test_matching_listing_notifies_saver_once_with_email():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, name="Bikes", query="road BIKE", category="Sports", min_price=50, max_price=150)
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()) as mail:
        assert (await _approve(srv, admin_tok, listing_id)).status_code == 200
    notes = await _notes(saver)
    assert len(notes) == 1
    assert notes[0]["listing_id"] == listing_id
    assert "Bikes" in notes[0]["message"] and "Vintage Road Bike" in notes[0]["message"]
    mail.assert_awaited_once()
    kw = mail.await_args.kwargs
    assert kw["to"] == "saver@alerts.example" and kw["subject"] == "New match: Vintage Road Bike"
    assert f"/auctions/{listing_id}" in kw["html"] and "turn these alerts off" in kw["html"]


@pytest.mark.asyncio
@pytest.mark.parametrize("criteria", [
    {"query": "kayak"}, {"query": "", "category": "Tools"}, {"query": "bike", "min_price": 200},
    {"query": "bike", "max_price": 50},
])
async def test_non_matching_search_gets_no_alert(criteria):
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, **criteria)
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()) as mail:
        await _approve(srv, admin_tok, listing_id)
    assert await _notes(saver) == []
    mail.assert_not_awaited()


@pytest.mark.asyncio
async def test_description_match_and_fixed_price_uses_buy_it_now_price():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, query="sticker", min_price=400, max_price=500)
    listing_id = await _pending(seller, listing_type="fixed_price", buy_it_now_price=450.0)
    with patch("app.search_alerts.send_email", new=AsyncMock()):
        await _approve(srv, admin_tok, listing_id)
    assert len(await _notes(saver)) == 1


@pytest.mark.asyncio
async def test_sellers_own_saved_search_is_skipped():
    srv = _app()
    seller, seller_tok, _, _, admin_tok = await _setup()
    await _save(srv, seller_tok, query="bike")
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()) as mail:
        await _approve(srv, admin_tok, listing_id)
    assert await _notes(seller) == []
    mail.assert_not_awaited()


@pytest.mark.asyncio
async def test_alerts_disabled_search_is_skipped():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    sid = await _save(srv, saver_tok, query="bike")
    async with _client(srv, saver_tok) as c:
        resp = await c.put(f"/api/saved-searches/{sid}", json={"alerts_enabled": False})
        assert resp.status_code == 200 and resp.json()["alerts_enabled"] is False
        assert (await c.get("/api/saved-searches")).json()["saved_searches"][0]["alerts_enabled"] is False
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()):
        await _approve(srv, admin_tok, listing_id)
    assert await _notes(saver) == []


@pytest.mark.asyncio
async def test_no_duplicates_on_reapproval_or_rerun():
    srv = _app()
    from app.db import db
    from app.search_alerts import alert_saved_searches
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, query="bike")
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()) as mail:
        await _approve(srv, admin_tok, listing_id)
        await db.listings.update_one({"_id": __import__("bson").ObjectId(listing_id)}, {"$set": {"status": "pending"}})
        await _approve(srv, admin_tok, listing_id)  # pending -> active again
        listing = await db.listings.find_one({"_id": __import__("bson").ObjectId(listing_id)})
        assert await alert_saved_searches(listing) == 0
    assert len(await _notes(saver)) == 1
    assert mail.await_count == 1


@pytest.mark.asyncio
async def test_two_matching_searches_one_notification():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, name="First", query="bike")
    await _save(srv, saver_tok, name="Second", query="vintage")
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()) as mail:
        await _approve(srv, admin_tok, listing_id)
    notes = await _notes(saver)
    assert len(notes) == 1 and "First" in notes[0]["message"]
    assert mail.await_count == 1


@pytest.mark.asyncio
async def test_regex_characters_in_query_match_literally():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    other, other_tok = await _user("other@alerts.example")
    await _save(srv, saver_tok, name="plus", query="C++")
    await _save(srv, other_tok, name="paren", query="(")
    listing_id = await _pending(seller)  # description has "C++" but no "("
    with patch("app.search_alerts.send_email", new=AsyncMock()):
        assert (await _approve(srv, admin_tok, listing_id)).status_code == 200
    assert len(await _notes(saver)) == 1
    assert await _notes(other) == []


@pytest.mark.asyncio
async def test_only_transition_to_active_triggers_and_failures_do_not_break_admin():
    srv = _app()
    seller, _, saver, saver_tok, admin_tok = await _setup()
    await _save(srv, saver_tok, query="bike")
    rejected = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock()):
        async with _client(srv, admin_tok) as c:
            await c.put(f"/api/admin/listings/{rejected}", json={"status": "rejected"})
    assert await _notes(saver) == []
    listing_id = await _pending(seller)
    with patch("app.search_alerts.send_email", new=AsyncMock(side_effect=RuntimeError("boom"))):
        assert (await _approve(srv, admin_tok, listing_id)).status_code == 200


@pytest.mark.asyncio
async def test_toggle_is_owner_only_and_validates_ids():
    srv = _app()
    _, _, _, saver_tok, _ = await _setup()
    _, other_tok = await _user("intruder@alerts.example")
    sid = await _save(srv, saver_tok, query="bike")
    async with _client(srv, other_tok) as c:
        assert (await c.put(f"/api/saved-searches/{sid}", json={"alerts_enabled": False})).status_code == 404
    async with _client(srv, saver_tok) as c:
        assert (await c.get("/api/saved-searches")).json()["saved_searches"][0]["alerts_enabled"] is True
        assert (await c.put("/api/saved-searches/not-an-id", json={"alerts_enabled": False})).status_code == 400
        assert (await c.put(f"/api/saved-searches/{'0' * 24}", json={"alerts_enabled": True})).status_code == 404
