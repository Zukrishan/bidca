"""
test_email_verification.py — FR-04: email address verification on registration.
Token emailed and stored only as a sha256, single-use, 24h expiry, resend cooldown,
and bidding/selling gated behind a confirmed email.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "bidca_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")

import mongomock_motor  # type: ignore

_mock_client = mongomock_motor.AsyncMongoMockClient()
PASSWORD = "Verify123!"


def _app():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server as srv
    return srv


def _client(srv):
    from httpx import AsyncClient, ASGITransport
    return AsyncClient(transport=ASGITransport(app=srv.fastapi_app), base_url="http://test")


async def _register(client, email):
    """Register and return (response, raw token from the emailed link)."""
    await _clean(email)
    with patch("app.email.send_email", new_callable=AsyncMock) as mock_send:
        resp = await client.post("/api/auth/register", json={
            "email": email, "password": PASSWORD, "full_name": "Vera Fy", "city": "Victoria",
            "postal_code": "V8W 1A1", "province": "British Columbia",
        })
    assert resp.status_code == 200, resp.text
    assert mock_send.await_count == 1
    kwargs = mock_send.await_args.kwargs
    assert kwargs["to"] == email and kwargs["subject"] == "Confirm your BidCa email"
    match = re.search(r"/verify-email\?token=([\w-]+)", kwargs["html"])
    assert match, "Email must contain the verification link"
    return resp, match.group(1)


async def _clean(email):
    from app.db import db
    user = await db.users.find_one({"email": email})
    if user:
        await db.email_verifications.delete_many({"user_id": str(user["_id"])})
        await db.users.delete_one({"_id": user["_id"]})


async def _user_doc(email):
    from app.db import db
    return await db.users.find_one({"email": email})


LISTING = {
    "title": "Verify item", "description": "x", "category": "Other", "city": "Victoria",
    "starting_bid": 10, "images": ["https://example.com/a.jpg"],
}


@pytest.mark.asyncio
async def test_register_sends_hashed_token_and_blocks_actions_until_verified():
    srv = _app()
    from app.db import db
    email = "fr04-flow@example.com"
    async with _client(srv) as c:
        resp, token = await _register(c, email)
        assert resp.json()["email_verified"] is False

        rec = await db.email_verifications.find_one({"user_id": str((await _user_doc(email))["_id"])})
        assert token not in rec.values(), "raw token must not be stored"
        assert rec["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
        assert rec["used"] is False
        ttl = datetime.fromisoformat(rec["expires_at"]) - datetime.now(timezone.utc)
        assert timedelta(hours=23) < ttl <= timedelta(hours=24)

        assert (await c.get("/api/auth/me")).json()["email_verified"] is False

        # Gated while unverified
        r = await c.post("/api/listings", json=LISTING)
        assert r.status_code == 403 and r.json()["detail"] == "Verify your email address to continue"
        assert (await c.post("/api/listings/abc/bid", json={"max_bid": 20})).status_code == 403
        assert (await c.post("/api/listings/abc/buy-now")).status_code == 403
        # Browsing and watchlist stay open
        assert (await c.get("/api/listings")).status_code == 200
        assert (await c.get("/api/users/me/watchlist")).status_code == 200

        # Public verify (no cookies needed), then single use
        async with _client(srv) as other:
            v = await other.post("/api/auth/verify-email", json={"token": token})
            assert v.status_code == 200 and "message" in v.json()
            again = await other.post("/api/auth/verify-email", json={"token": token})
            assert again.status_code == 400
            assert again.json()["detail"] == "Invalid or expired verification link"

        assert (await _user_doc(email))["email_verified"] is True
        assert (await c.get("/api/auth/me")).json()["email_verified"] is True
        assert (await c.post("/api/listings", json=LISTING)).status_code == 201


@pytest.mark.asyncio
async def test_missing_flag_counts_as_unverified():
    srv = _app()
    email = "fr04-legacy@example.com"
    async with _client(srv) as c:
        await _register(c, email)
        from app.db import db
        await db.users.update_one({"email": email}, {"$unset": {"email_verified": 1}})
        assert (await c.post("/api/listings", json=LISTING)).status_code == 403


@pytest.mark.asyncio
async def test_invalid_and_expired_tokens_rejected():
    srv = _app()
    from app.db import db
    email = "fr04-expired@example.com"
    async with _client(srv) as c:
        _, token = await _register(c, email)
        assert (await c.post("/api/auth/verify-email", json={"token": "nope"})).status_code == 400
        await db.email_verifications.update_many(
            {"token_hash": hashlib.sha256(token.encode()).hexdigest()},
            {"$set": {"expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}})
        assert (await c.post("/api/auth/verify-email", json={"token": token})).status_code == 400
        assert not (await _user_doc(email)).get("email_verified")


@pytest.mark.asyncio
async def test_resend_cooldown_replaces_token_and_rejects_verified():
    srv = _app()
    from app.db import db
    email = "fr04-resend@example.com"
    async with _client(srv) as c:
        _, old = await _register(c, email)
        # Within 60s of the registration token
        assert (await c.post("/api/auth/resend-verification")).status_code == 429

        await db.email_verifications.update_many({}, {"$set": {"created_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()}})
        with patch("app.email.send_email", new_callable=AsyncMock) as mock_send:
            r = await c.post("/api/auth/resend-verification")
        assert r.status_code == 200 and mock_send.await_count == 1
        new = re.search(r"token=([\w-]+)", mock_send.await_args.kwargs["html"]).group(1)
        assert new != old
        # The earlier token no longer works; the new one does
        assert (await c.post("/api/auth/verify-email", json={"token": old})).status_code == 400
        assert (await c.post("/api/auth/verify-email", json={"token": new})).status_code == 200

        assert (await c.post("/api/auth/resend-verification")).status_code == 400


@pytest.mark.asyncio
async def test_resend_requires_login():
    srv = _app()
    async with _client(srv) as c:
        assert (await c.post("/api/auth/resend-verification")).status_code == 401


@pytest.mark.asyncio
async def test_seeded_admin_is_verified():
    srv = _app()
    from app.db import db
    from app.seed import _seed_admin
    email = os.environ.get("ADMIN_EMAIL", "admin@bidca.ca")
    await db.users.delete_many({"email": email})
    with patch.dict(os.environ, {"ENV": ""}):
        await _seed_admin()
    assert (await db.users.find_one({"email": email}))["email_verified"] is True
    # An older admin row without the flag is fixed on startup
    await db.users.update_one({"email": email}, {"$unset": {"email_verified": 1}})
    with patch.dict(os.environ, {"ENV": ""}):
        await _seed_admin()
    assert (await db.users.find_one({"email": email}))["email_verified"] is True


@pytest.mark.asyncio
async def test_mock_email_logs_body_only_outside_production(caplog):
    from app.email import send_email
    html = "<a href='http://x/verify-email?token=SECRETLINK'>go</a>"
    with patch.dict(os.environ, {"ENV": "development"}):
        os.environ.pop("SENDGRID_API_KEY", None)
        with caplog.at_level("INFO", logger="app.email"):
            await send_email("a@b.c", "s", html)
    assert "SECRETLINK" in caplog.text
    caplog.clear()
    with patch.dict(os.environ, {"ENV": "production"}):
        os.environ.pop("SENDGRID_API_KEY", None)
        with caplog.at_level("INFO", logger="app.email"):
            await send_email("a@b.c", "s", html)
    assert "SECRETLINK" not in caplog.text
