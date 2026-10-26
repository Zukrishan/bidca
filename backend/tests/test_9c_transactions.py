"""
test_9c_transactions.py — Phase 9c (R38–R43): transaction page, Complete by both sides, disputes
with proof, ratings only after completion, the no-response job and reminders, user page tabs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from bson import ObjectId

from test_hardening import _app, _client, _listing, _user  # shared fixtures (same mongomock client)

PROOF = ["https://res.cloudinary.com/demo/image/upload/proof.jpg"]


def _ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


async def _deal(tag, created_hours_ago=0.0, **tx):
    """seller, buyer, stranger and an open auction transaction between seller and buyer."""
    from app.db import db
    s = await _user(f"s-{tag}@p9c.example", full_name="Sally Seller", exchange_methods=["cash", "e_transfer"])
    b = await _user(f"b-{tag}@p9c.example", full_name="Bob Buyer")
    x = await _user(f"x-{tag}@p9c.example")
    lid = await _listing(s[0], status="sold", listing_type="auction", title=f"P9C {tag}",
                         images=["http://img/1.jpg"], winner_id=b[0], sold_price=40.0)
    doc = {"listing_id": lid, "seller_id": s[0], "buyer_id": b[0], "amount": 40.0, "type": "auction",
           "status": "open", "created_at": _ago(created_hours_ago), **tx}
    tid = str((await db.transactions.insert_one(doc)).inserted_id)
    return dict(s=s, b=b, x=x, lid=lid, tid=tid)


async def _tx(tid):
    from app.db import db
    return await db.transactions.find_one({"_id": ObjectId(tid)})


# --- transaction page -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transaction_summary_is_for_buyer_and_seller_only():
    srv = _app()
    d = await _deal("summary")
    async with _client(srv, d["b"][1]) as c:
        r = await c.get(f"/api/transactions/{d['tid']}")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "buyer" and body["status"] == "open" and body["amount"] == 40.0
    assert body["listing"]["title"] == "P9C summary" and body["listing"]["image"] == "http://img/1.jpg"
    assert body["exchange_methods"] == ["cash", "e_transfer"]
    assert body["seller"]["full_name"] == "Sally Seller" and body["can_rate"] is False
    async with _client(srv, d["x"][1]) as c:
        assert (await c.get(f"/api/transactions/{d['tid']}")).status_code == 404
        assert (await c.get("/api/transactions/not-an-id")).status_code == 404


@pytest.mark.asyncio
async def test_complete_needs_both_sides_and_then_asks_for_ratings():
    srv = _app()
    from app.db import db
    d = await _deal("complete")
    with patch("app.email.send_email", new_callable=AsyncMock):
        async with _client(srv, d["b"][1]) as c:
            r = await c.post(f"/api/transactions/{d['tid']}/complete")
            assert r.status_code == 200
            assert r.json()["status"] == "open" and r.json()["my_completed"] and not r.json()["other_completed"]
            # rating before completion is refused (FR-25)
            fb = await c.post(f"/api/transactions/{d['tid']}/feedback", json={"rating": "positive", "comment": "ok"})
            assert fb.status_code == 400
        async with _client(srv, d["s"][1]) as c:
            r = await c.post(f"/api/transactions/{d['tid']}/complete")
    assert r.json()["status"] == "completed" and r.json()["can_rate"] is True
    t = await _tx(d["tid"])
    assert t["buyer_completed_at"] and t["seller_completed_at"] and t["completed_at"]
    for uid in (d["b"][0], d["s"][0]):
        assert await db.notifications.count_documents(
            {"user_id": uid, "type": "transaction_completed", "transaction_id": d["tid"]}) == 1
    async with _client(srv, d["b"][1]) as c:
        ok = await c.post(f"/api/transactions/{d['tid']}/feedback", json={"rating": "positive", "comment": "Great"})
        again = await c.post(f"/api/transactions/{d['tid']}/feedback", json={"rating": "negative", "comment": "x"})
        assert (await c.get(f"/api/transactions/{d['tid']}")).json()["my_feedback"]["rating"] == "positive"
    assert ok.status_code == 200 and again.status_code == 400


@pytest.mark.asyncio
async def test_dispute_needs_proof_blocks_complete_and_only_the_opener_cancels():
    srv = _app()
    from app.db import db
    d = await _deal("dispute")
    await _user("admin-9c@p9c.example", role="admin")
    with patch("app.email.send_email", new_callable=AsyncMock):
        async with _client(srv, d["b"][1]) as c:
            no_proof = await c.post(f"/api/transactions/{d['tid']}/dispute", json={"reason": "Broken", "proof_urls": []})
            bad_proof = await c.post(f"/api/transactions/{d['tid']}/dispute",
                                     json={"reason": "Broken", "proof_urls": ["javascript:alert(1)"]})
            r = await c.post(f"/api/transactions/{d['tid']}/dispute", json={"reason": "Broken", "proof_urls": PROOF})
            assert (await c.post(f"/api/transactions/{d['tid']}/complete")).status_code == 409
        async with _client(srv, d["s"][1]) as c:
            assert (await c.post(f"/api/transactions/{d['tid']}/complete")).status_code == 409
            assert (await c.post(f"/api/transactions/{d['tid']}/cancel-dispute")).status_code == 403
        async with _client(srv, d["b"][1]) as c:
            back = await c.post(f"/api/transactions/{d['tid']}/cancel-dispute")
            assert (await c.post(f"/api/transactions/{d['tid']}/complete")).status_code == 200
    assert no_proof.status_code == 422 and bad_proof.status_code == 422
    assert r.status_code == 200 and r.json()["status"] == "disputed"
    assert r.json()["dispute"]["proof_urls"] == PROOF and r.json()["dispute"]["opened_by_me"] is True
    assert back.json()["status"] == "open"
    assert await db.notifications.count_documents({"type": "dispute_opened", "transaction_id": d["tid"]}) >= 1


@pytest.mark.asyncio
async def test_admin_resolves_dispute_with_moderation_only():
    srv = _app()
    d = await _deal("resolve")
    _, admin_tok = await _user("admin-resolve@p9c.example", role="admin")
    with patch("app.email.send_email", new_callable=AsyncMock):
        async with _client(srv, d["s"][1]) as c:
            await c.post(f"/api/transactions/{d['tid']}/dispute", json={"reason": "No-show", "proof_urls": PROOF})
            assert (await c.get("/api/admin/disputes")).status_code == 403
        async with _client(srv, admin_tok) as c:
            listed = (await c.get("/api/admin/disputes")).json()["disputes"]
            assert any(x["_id"] == d["tid"] for x in listed)
            missing_target = await c.put(f"/api/admin/disputes/{d['tid']}", json={"note": "x", "outcome": "suspend"})
            r = await c.put(f"/api/admin/disputes/{d['tid']}",
                            json={"note": "Buyer never showed", "outcome": "suspend", "target_user_id": d["b"][0],
                                  "suspend_hours": 48})
            assert (await c.put(f"/api/admin/disputes/{d['tid']}", json={"note": "x", "outcome": "close"})).status_code == 409
    assert missing_target.status_code == 422
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    t = await _tx(d["tid"])
    assert t["dispute"]["resolved_at"] and t["dispute"]["resolution"]["outcome"] == "suspend"
    async with _client(srv, d["b"][1]) as c:
        me = await c.get("/api/auth/me")
    assert me.status_code == 403 and "locked until" in me.json()["detail"]


# --- account lock -----------------------------------------------------------------------

def test_suspended_until_blocks_only_while_in_the_future():
    _app()
    from app.security import account_block_reason
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert "locked until" in account_block_reason({"suspended_until": future, "suspension_reason": "test"})
    assert account_block_reason({"suspended_until": _ago(1)}) is None
    assert account_block_reason({"suspended_until": "garbage"}) is None


# --- no-response job (FR-26) ------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_response_cancels_locks_rates_and_lets_seller_relist():
    srv = _app()
    from app.db import db
    from app.transaction_jobs import run_transaction_jobs
    d = await _deal("noresp", created_hours_ago=25)
    with patch("app.email.send_email", new_callable=AsyncMock):
        await run_transaction_jobs(db)
        await run_transaction_jobs(db)  # idempotent
    t = await _tx(d["tid"])
    assert t["status"] == "cancelled" and t["cancelled_reason"] == "no_response"
    buyer = await db.users.find_one({"_id": ObjectId(d["b"][0])})
    assert buyer["suspended_until"] > datetime.now(timezone.utc).isoformat()
    assert buyer["negative_ratings"] == 1 and buyer["total_ratings"] == 1
    fb = await db.feedback.find({"transaction_id": d["tid"]}).to_list(10)
    assert len(fb) == 1 and fb[0]["comment"] == "No response within 24 hours" and fb[0]["system"] is True
    for uid in (d["b"][0], d["s"][0]):
        assert await db.notifications.count_documents(
            {"user_id": uid, "type": "transaction_cancelled", "transaction_id": d["tid"]}) == 1
    async with _client(srv, d["b"][1]) as c:
        assert (await c.get("/api/auth/me")).status_code == 403
    async with _client(srv, d["s"][1]) as c:
        assert (await c.post(f"/api/listings/{d['lid']}/relist")).status_code == 200


@pytest.mark.asyncio
async def test_buyer_message_or_complete_counts_as_a_response():
    srv = _app()
    from app.db import db
    from app.transaction_jobs import run_transaction_jobs
    messaged = await _deal("msg", created_hours_ago=1)
    legacy = await _deal("legacy", created_hours_ago=30)  # message sent before buyer_responded_at existed
    await db.messages.insert_one({"transaction_id": legacy["tid"], "sender_id": legacy["b"][0],
                                  "recipient_id": legacy["s"][0], "body": "hi", "created_at": _ago(29), "read_at": None})
    pressed = await _deal("pressed", created_hours_ago=30, buyer_completed_at=_ago(29))
    with patch("app.routers.messages.send_email", new=AsyncMock()):
        async with _client(srv, messaged["b"][1]) as c:
            assert (await c.post(f"/api/transactions/{messaged['tid']}/messages", json={"body": "On my way"})).status_code == 201
    assert (await _tx(messaged["tid"]))["buyer_responded_at"]
    with patch("app.email.send_email", new_callable=AsyncMock):
        await run_transaction_jobs(db)
    assert (await _tx(legacy["tid"]))["status"] == "open"
    assert (await _tx(legacy["tid"]))["buyer_responded_at"]
    assert (await _tx(pressed["tid"]))["status"] == "open"


@pytest.mark.asyncio
async def test_relist_refused_while_sale_is_live():
    srv = _app()
    d = await _deal("relist-live")
    async with _client(srv, d["s"][1]) as c:
        assert (await c.post(f"/api/listings/{d['lid']}/relist")).status_code == 400


# --- reminders (FR-27) ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reminders_every_interval_then_admins_alerted():
    _app()
    from app.db import db
    from app.transaction_jobs import run_transaction_jobs
    d = await _deal("remind", created_hours_ago=7, buyer_responded_at=_ago(6.5))
    last = await _deal("remind-last", created_hours_ago=7, buyer_responded_at=_ago(6.5),
                       reminders_sent=9, last_reminder_at=_ago(7))
    maxed = await _deal("remind-max", created_hours_ago=7, buyer_responded_at=_ago(6.5),
                        reminders_sent=10, last_reminder_at=_ago(7))
    disputed = await _deal("remind-disp", created_hours_ago=7, status="disputed")
    await _user("admin-remind@p9c.example", role="admin")
    with patch("app.email.send_email", new_callable=AsyncMock) as send:
        await run_transaction_jobs(db)
        await run_transaction_jobs(db)  # not due again yet
    subjects = [call.kwargs["subject"] for call in send.await_args_list]
    assert subjects.count("Your transaction for P9C remind is still open") == 2  # buyer + seller, once
    assert subjects.count("Your transaction for P9C remind-last is still open") == 2
    assert not any("remind-max" in s or "remind-disp" in s for s in subjects)
    t = await _tx(d["tid"])
    assert t["reminders_sent"] == 1 and t["last_reminder_at"]
    assert (await _tx(last["tid"]))["reminders_sent"] == 10
    assert (await _tx(maxed["tid"]))["reminders_sent"] == 10
    assert "reminders_sent" not in await _tx(disputed["tid"])
    assert await db.notifications.count_documents({"type": "transaction_stalled", "transaction_id": last["tid"]}) >= 1


def test_settings_read_env(monkeypatch):
    from app import config
    monkeypatch.setenv("NO_RESPONSE_HOURS", "12")
    monkeypatch.setenv("REMINDER_MAX", "3")
    monkeypatch.delenv("NO_RESPONSE_LOCK_HOURS", raising=False)
    assert config.no_response_window() == timedelta(hours=12)
    assert config.no_response_lock() == timedelta(hours=6)
    assert config.reminder_max() == 3


# --- user page tabs (FR-23) -------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_page_tabs():
    srv = _app()
    from app.db import db
    d = await _deal("tabs")
    done = await _deal("tabs-done", status="completed", completed_at=_ago(1))
    active = await _listing(d["s"][0], title="P9C active", listing_type="auction")
    await db.bids.insert_one({"listing_id": active, "bidder_id": d["b"][0], "amount": 10.0, "max_bid": 15.0,
                              "created_at": _ago(0)})
    async with _client(srv, d["b"][1]) as c:
        cur = (await c.get("/api/users/me/current-bids")).json()
    assert [b["_id"] for b in cur["bids"]] == [active] and cur["bids"][0]["my_max_bid"] == 15.0
    assert "highest_bidder_max_bid" not in cur["bids"][0]
    assert [w["_id"] for w in cur["won"]] == [d["tid"]] and cur["won"][0]["other_party"]["full_name"] == "Sally Seller"
    async with _client(srv, d["s"][1]) as c:
        selling = (await c.get("/api/users/me/selling")).json()["listings"]
    sold = next(l for l in selling if l["_id"] == d["lid"])
    assert sold["transaction"]["_id"] == d["tid"] and sold["transaction"]["status"] == "open"
    async with _client(srv, done["s"][1]) as c:
        selling_done = (await c.get("/api/users/me/selling")).json()["listings"]
        completed = (await c.get("/api/users/me/completed")).json()["transactions"]
    assert not any(l["_id"] == done["lid"] for l in selling_done)
    assert [t["_id"] for t in completed] == [done["tid"]] and completed[0]["role"] == "seller"
    assert completed[0]["rated"] is False
