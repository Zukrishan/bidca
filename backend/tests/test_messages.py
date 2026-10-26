"""
test_messages.py — FR-20 buyer–seller messaging after a sale.
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
PASSWORD = "Messages123!"


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
        "verification_status": "unverified", "total_sales": 0, "total_sales_amount": 0,
        "total_purchases": 0, "created_at": datetime.now(timezone.utc).isoformat(), **extra,
    }
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    return uid, create_access_token(uid, email)


async def _listing(seller_id, **extra):
    from app.db import db
    doc = {
        "title": "MSG item", "description": "x", "category": "Tools", "seller_id": seller_id,
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


async def _setup(tag):
    """seller, buyer, stranger and a transaction between seller and buyer."""
    from app.db import db
    s_id, s_tok = await _user(f"seller-{tag}@msg.example", full_name="Sally Seller")
    b_id, b_tok = await _user(f"buyer-{tag}@msg.example", full_name="Bob Buyer")
    x_id, x_tok = await _user(f"x-{tag}@msg.example")
    lid = await _listing(s_id, status="sold", images=["http://img/1.jpg"])
    tid = str((await db.transactions.insert_one({
        "listing_id": lid, "seller_id": s_id, "buyer_id": b_id, "amount": 40.0, "type": "buy_it_now",
        "status": "open", "created_at": datetime.now(timezone.utc).isoformat()})).inserted_id)
    return dict(s=(s_id, s_tok), b=(b_id, b_tok), x=(x_id, x_tok), lid=lid, tid=tid)


@pytest.mark.asyncio
async def test_exchange_read_and_unread_count():
    srv = _app()
    c = await _setup("ex")
    async with _client(srv, c["b"][1]) as buyer, _client(srv, c["s"][1]) as seller:
        r = await buyer.post(f"/api/transactions/{c['tid']}/messages", json={"body": "  Hi, when can I pick up? "})
        assert r.status_code == 201
        assert r.json()["body"] == "Hi, when can I pick up?" and r.json()["sender_id"] == c["b"][0]
        assert (await seller.get("/api/messages/unread-count")).json() == {"unread": 1}
        assert (await buyer.get("/api/messages/unread-count")).json() == {"unread": 0}

        convs = (await seller.get("/api/conversations")).json()["conversations"]
        mine = [x for x in convs if x["transaction_id"] == c["tid"]][0]
        assert mine["role"] == "seller" and mine["unread_count"] == 1
        assert mine["other_party"] == {"id": c["b"][0], "full_name": "Bob Buyer"}
        assert mine["last_message"]["body"] == "Hi, when can I pick up?"
        assert mine["listing_title"] == "MSG item" and mine["listing_image"] == "http://img/1.jpg"
        assert mine["amount"] == 40.0

        t = (await seller.get(f"/api/transactions/{c['tid']}/messages")).json()
        assert [m["body"] for m in t["messages"]] == ["Hi, when can I pick up?"]
        assert t["other_party"]["full_name"] == "Bob Buyer" and t["listing"]["id"] == c["lid"]
        assert (await seller.get("/api/messages/unread-count")).json() == {"unread": 0}

        assert (await seller.post(f"/api/transactions/{c['tid']}/messages", json={"body": "Saturday 10am"})).status_code == 201
        convs = (await buyer.get("/api/conversations")).json()["conversations"]
        mine = [x for x in convs if x["transaction_id"] == c["tid"]][0]
        assert mine["role"] == "buyer" and mine["unread_count"] == 1
        assert mine["other_party"]["full_name"] == "Sally Seller"
        assert mine["last_message"]["sender_id"] == c["s"][0]
        t = (await buyer.get(f"/api/transactions/{c['tid']}/messages")).json()
        assert [m["body"] for m in t["messages"]] == ["Hi, when can I pick up?", "Saturday 10am"]


@pytest.mark.asyncio
async def test_outsiders_and_bad_ids_get_404():
    srv = _app()
    c = await _setup("out")
    async with _client(srv, c["x"][1]) as x, _client(srv) as anon:
        assert (await x.get(f"/api/transactions/{c['tid']}/messages")).status_code == 404
        assert (await x.post(f"/api/transactions/{c['tid']}/messages", json={"body": "hi"})).status_code == 404
        assert (await x.get("/api/conversations")).json()["conversations"] == []
        assert (await anon.get("/api/conversations")).status_code == 401
    async with _client(srv, c["b"][1]) as b:
        for bad in ("nope", "0" * 24):
            assert (await b.get(f"/api/transactions/{bad}/messages")).status_code == 404
            assert (await b.post(f"/api/transactions/{bad}/messages", json={"body": "hi"})).status_code == 404


@pytest.mark.asyncio
async def test_body_validation_and_rate_limit():
    srv = _app()
    c = await _setup("rl")
    url = f"/api/transactions/{c['tid']}/messages"
    async with _client(srv, c["b"][1]) as b, _client(srv, c["s"][1]) as s:
        for bad in ("", "   ", "x" * 2001):
            assert (await b.post(url, json={"body": bad})).status_code in (400, 422)
        assert (await b.post(url, json={"body": "x" * 2000})).status_code == 201
        for i in range(19):
            assert (await b.post(url, json={"body": f"m{i}"})).status_code == 201
        assert (await b.post(url, json={"body": "21st"})).status_code == 429
        assert (await s.post(url, json={"body": "other sender unaffected"})).status_code == 201


@pytest.mark.asyncio
async def test_one_unread_notification_per_recipient_and_transaction():
    from app.db import db
    srv = _app()
    c = await _setup("nt")
    url = f"/api/transactions/{c['tid']}/messages"
    with patch("app.routers.messages.send_email", new=AsyncMock()) as mail:
        async with _client(srv, c["b"][1]) as b, _client(srv, c["s"][1]) as s:
            for i in range(3):
                await b.post(url, json={"body": f"<b>m{i}</b>"})
            q = {"user_id": c["s"][0], "type": "new_message"}
            assert await db.notifications.count_documents(q) == 1
            n = await db.notifications.find_one(q)
            assert n["message"] == "New message from Bob about MSG item"
            assert mail.await_count == 1
            assert "<b>" not in mail.await_args.kwargs["html"]
            # reading the thread clears it; the next message notifies again
            await s.get(url)
            await b.post(url, json={"body": "again"})
            assert await db.notifications.count_documents(q) == 2
            assert mail.await_count == 2


@pytest.mark.asyncio
async def test_socket_emit_goes_to_recipient_room_and_failure_is_harmless():
    srv = _app()
    c = await _setup("ws")
    url = f"/api/transactions/{c['tid']}/messages"
    from app.realtime import sio
    async with _client(srv, c["b"][1]) as b:
        with patch.object(sio, "emit", new=AsyncMock()) as emit:
            assert (await b.post(url, json={"body": "ping"})).status_code == 201
            msg_calls = [call for call in emit.await_args_list if call.args[0] == "message"]
            assert len(msg_calls) == 1
            call = msg_calls[0]
            assert call.kwargs["room"] == f"user_{c['s'][0]}"
            payload = call.args[1]
            json.dumps(payload)
            assert payload["transaction_id"] == c["tid"] and payload["message"]["body"] == "ping"
        with patch.object(sio, "emit", new=AsyncMock(side_effect=RuntimeError("down"))):
            assert (await b.post(url, json={"body": "still stored"})).status_code == 201
        msgs = (await b.get(url)).json()["messages"]
        assert [m["body"] for m in msgs] == ["ping", "still stored"]
