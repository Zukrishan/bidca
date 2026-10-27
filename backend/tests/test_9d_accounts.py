"""
test_9d_accounts.py — Phase 9d accounts (R44–R47): sign-up fields, phone verification, CAPTCHA,
inactivity logout, public profile (display name, badge, tiers, exchange methods), account settings
and delete account.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hardening import PASSWORD, _app, _client, _listing, _user  # noqa: E402  (same fixtures, same shared DB)


def _signup(email, phone, **extra):
    return {"email": email, "password": PASSWORD, "full_name": "Vera Fyodorova", "city": "Victoria",
            "postal_code": "V8W 1A1", "phone": phone, "age_confirmed_19_plus": True, "terms_accepted": True,
            **extra}


async def _clean(email):
    from app.db import db
    await db.users.delete_many({"email": email})


async def _tx(buyer_id, seller_id, status="completed", **extra):
    from app.db import db
    doc = {"buyer_id": buyer_id, "seller_id": seller_id, "listing_id": str(ObjectId()), "status": status,
           "created_at": datetime.now(timezone.utc).isoformat(), **extra}
    return str((await db.transactions.insert_one(doc)).inserted_id)


async def _feedback(to_user_id, rating, feedback_type):
    from app.db import db
    await db.feedback.insert_one({"to_user_id": to_user_id, "from_user_id": str(ObjectId()), "rating": rating,
                                  "feedback_type": feedback_type, "comment": "ok",
                                  "created_at": datetime.now(timezone.utc).isoformat()})


# --- sign-up (FR-01) ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_stores_new_fields_and_profile_hides_full_name():
    srv = _app()
    from app.db import db
    email = "vera@9d.example"
    await _clean(email)
    async with _client(srv) as c:
        resp = await c.post("/api/auth/register", json=_signup(email, "(250) 555-0111"))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        profile = (await c.get(f"/api/users/{body['id']}/profile")).json()
    assert body["display_name"] == "Vera F." and body["phone"] == "+12505550111"
    doc = await db.users.find_one({"email": email})
    assert doc["phone_verified"] is False and doc["age_confirmed_19_plus"] is True
    assert doc["terms_accepted_at"] and doc["last_active_at"] and doc["exchange_methods"] == []
    assert profile["display_name"] == "Vera F."
    for private in ("full_name", "email", "phone", "postal_code"):
        assert private not in profile


@pytest.mark.asyncio
@pytest.mark.parametrize("override,detail", [
    ({"age_confirmed_19_plus": False}, "19"),
    ({"terms_accepted": False}, "Terms"),
    ({"city": "Toronto"}, "city"),
    ({"phone": "12345"}, "phone"),
    ({"postal_code": "M5V 1A1"}, "British Columbia"),
    ({"avatar_url": "https://evil.example/x.png"}, "picture"),
])
async def test_register_rejects_missing_rules(override, detail):
    srv = _app()
    email = "rules@9d.example"
    await _clean(email)
    async with _client(srv) as c:
        resp = await c.post("/api/auth/register", json={**_signup(email, "250-555-0112"), **override})
    assert resp.status_code == 400 and detail in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_requires_phone_and_terms_fields():
    srv = _app()
    payload = _signup("nophone@9d.example", "250-555-0113")
    del payload["phone"]
    async with _client(srv) as c:
        assert (await c.post("/api/auth/register", json=payload)).status_code == 422


@pytest.mark.asyncio
async def test_one_account_per_verified_phone():
    srv = _app()
    await _user("holder@9d.example", phone="+12505550114", phone_verified=True)
    await _clean("second@9d.example")
    async with _client(srv) as c:
        resp = await c.post("/api/auth/register", json=_signup("second@9d.example", "250 555 0114"))
    assert resp.status_code == 400 and "phone" in resp.json()["detail"]


# --- phone verification -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phone_verification_dev_code(monkeypatch):
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID"):
        monkeypatch.delenv(k, raising=False)
    srv = _app()
    from app.db import db
    uid, token = await _user("phone@9d.example", phone="+12505550115", phone_verified=False)
    await db.phone_verifications.delete_many({"user_id": uid})
    async with _client(srv, token) as c:
        assert (await c.get("/api/auth/config")).json()["phone_verification"] == "dev"
        sent = await c.post("/api/auth/phone/send-code", json={})
        assert sent.status_code == 200, sent.text
        again = await c.post("/api/auth/phone/send-code", json={})
        assert again.status_code == 429  # one code a minute
        wrong = await c.post("/api/auth/phone/verify", json={"code": "123456"})
        assert wrong.status_code == 400
        ok = await c.post("/api/auth/phone/verify", json={"code": "000000"})
        assert ok.status_code == 200 and ok.json()["phone_verified"] is True
    assert (await db.users.find_one({"_id": ObjectId(uid)}))["phone_verified"] is True


@pytest.mark.asyncio
async def test_phone_verification_uses_twilio_when_configured(monkeypatch):
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID"):
        monkeypatch.setenv(k, "x")
    srv = _app()
    from app.db import db
    uid, token = await _user("twilio@9d.example", phone="+12505550122", phone_verified=False)
    await db.phone_verifications.delete_many({"user_id": uid})
    async with _client(srv, token) as c:
        with patch("app.phone._twilio_post", return_value={"status": "pending"}) as tw:
            assert (await c.post("/api/auth/phone/send-code", json={})).status_code == 200
        assert tw.await_args.args == ("Verifications", {"To": "+12505550122", "Channel": "sms"})
        with patch("app.phone._twilio_post", return_value={"status": "pending"}):
            assert (await c.post("/api/auth/phone/verify", json={"code": "000000"})).status_code == 400
        with patch("app.phone._twilio_post", return_value={"status": "approved"}):
            assert (await c.post("/api/auth/phone/verify", json={"code": "481516"})).status_code == 200


@pytest.mark.asyncio
async def test_phone_verify_refused_when_number_verified_elsewhere():
    srv = _app()
    from app.db import db
    await _user("first-phone@9d.example", phone="+12505550116", phone_verified=False)
    uid2, token2 = await _user("dup-phone@9d.example", phone="+12505550116", phone_verified=False)
    await db.users.update_one({"email": "first-phone@9d.example"}, {"$set": {"phone_verified": True}})
    async with _client(srv, token2) as c:
        resp = await c.post("/api/auth/phone/verify", json={"code": "000000"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_phone_change_resets_verification():
    srv = _app()
    from app.db import db
    uid, token = await _user("change-phone@9d.example", phone="+12505550117", phone_verified=True)
    await db.phone_verifications.delete_many({"user_id": uid})
    async with _client(srv, token) as c:
        resp = await c.post("/api/auth/phone/send-code", json={"phone": "604-555-0117"})
    assert resp.status_code == 200
    doc = await db.users.find_one({"_id": ObjectId(uid)})
    assert doc["phone"] == "+16045550117" and doc["phone_verified"] is False


@pytest.mark.asyncio
async def test_production_without_keys_refuses(monkeypatch):
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID", "TURNSTILE_SECRET_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ENV", "production")
    srv = _app()
    from app.accounts import check_production_settings
    with pytest.raises(RuntimeError):
        check_production_settings()
    uid, token = await _user("prod-phone@9d.example", phone="+12505550118")
    async with _client(srv, token) as c:
        assert (await c.post("/api/auth/phone/send-code", json={})).status_code == 503
        assert (await c.get("/api/auth/config")).json()["phone_verification"] == "off"


def test_production_with_keys_starts(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID",
              "TURNSTILE_SECRET_KEY", "TURNSTILE_SITE_KEY"):
        monkeypatch.setenv(k, "x")
    _app()
    from app.accounts import check_production_settings
    check_production_settings()


def test_normalize_phone():
    from app.phone import normalize_phone
    assert normalize_phone("+1 (604) 555-0199") == "+16045550199"
    assert normalize_phone("6045550199") == "+16045550199"
    assert normalize_phone("045550199") is None and normalize_phone("") is None


# --- CAPTCHA ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_captcha_required_on_login_when_configured(monkeypatch):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "secret")
    monkeypatch.setenv("TURNSTILE_SITE_KEY", "site")
    srv = _app()
    from app.db import db
    email = "captcha@9d.example"
    await _user(email)
    await db.login_attempts.delete_many({"identifier": email})
    creds = {"email": email, "password": PASSWORD}
    async with _client(srv) as c:
        assert (await c.get("/api/auth/config")).json()["captcha_site_key"] == "site"
        missing = await c.post("/api/auth/login", json=creds)
        with patch("app.captcha._siteverify", return_value={"success": False}):
            bad = await c.post("/api/auth/login", json={**creds, "captcha_token": "t"})
        with patch("app.captcha._siteverify", return_value={"success": True}) as verify:
            good = await c.post("/api/auth/login", json={**creds, "captcha_token": "t"})
            reg = await c.post("/api/auth/register", json=_signup("captcha-reg@9d.example", "250-555-0119"))
    assert missing.status_code == 400 and bad.status_code == 400
    assert good.status_code == 200
    assert reg.status_code == 400  # register without a token is refused before any check
    assert verify.call_count == 1


# --- inactivity logout (FR-02) ------------------------------------------------------------

@pytest.mark.asyncio
async def test_idle_session_is_refused_and_activity_is_tracked(monkeypatch):
    monkeypatch.delenv("INACTIVITY_LOGOUT_MINUTES", raising=False)
    srv = _app()
    from app.db import db
    from app.security import create_refresh_token
    now = datetime.now(timezone.utc)
    idle_id, idle_token = await _user("idle@9d.example", last_active_at=(now - timedelta(minutes=31)).isoformat())
    busy_id, busy_token = await _user("busy@9d.example", last_active_at=(now - timedelta(minutes=5)).isoformat())
    legacy_id, legacy_token = await _user("legacy@9d.example")  # no last_active_at at all
    async with _client(srv, idle_token) as c:
        me = await c.get("/api/auth/me")
        c.cookies.set("refresh_token", create_refresh_token(idle_id))
        refresh = await c.post("/api/auth/refresh")
    assert me.status_code == 401 and "inactivity" in me.json()["detail"]
    assert refresh.status_code == 401
    async with _client(srv, busy_token) as c:
        assert (await c.get("/api/auth/me")).status_code == 200
    async with _client(srv, legacy_token) as c:
        assert (await c.get("/api/auth/me")).status_code == 200
    busy = await db.users.find_one({"_id": ObjectId(busy_id)})
    assert datetime.fromisoformat(busy["last_active_at"]) > now - timedelta(seconds=5)
    assert (await db.users.find_one({"_id": ObjectId(legacy_id)}))["last_active_at"]

    # Signing in again starts a fresh session
    await db.login_attempts.delete_many({})
    async with _client(srv) as c:
        login = await c.post("/api/auth/login", json={"email": "idle@9d.example", "password": PASSWORD})
        assert login.status_code == 200
        assert (await c.get("/api/auth/me")).status_code == 200


# --- public profile (FR-22) ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_badge_needs_phone_and_two_completed_non_private_deals():
    srv = _app()
    from app.db import db
    uid, _ = await _user("badge@9d.example", phone="+12505550120", phone_verified=True)
    other, _ = await _user("badge-other@9d.example")
    await db.transactions.delete_many({"$or": [{"buyer_id": uid}, {"seller_id": uid}]})
    await _tx(uid, other)  # bought one
    private_listing = await _listing(other, listing_type="private")
    await _tx(uid, other, listing_id=private_listing)  # private deals don't count
    await _tx(uid, other, status="open")
    async with _client(srv) as c:
        one = (await c.get(f"/api/users/{uid}/profile")).json()
        await _tx(other, uid)  # sold one
        two = (await c.get(f"/api/users/{uid}/profile")).json()
    assert one["verified_badge"] is False and one["completed_as_buyer"] == 1
    assert two["verified_badge"] is True and two["completed_as_seller"] == 1

    unverified, _ = await _user("badge-nophone@9d.example", phone_verified=False)
    await _tx(unverified, other)
    await _tx(other, unverified)
    async with _client(srv) as c:
        assert (await c.get(f"/api/users/{unverified}/profile")).json()["verified_badge"] is False


@pytest.mark.asyncio
async def test_tiers_and_rating_colours():
    srv = _app()
    from app.db import db
    uid, _ = await _user("tiers@9d.example", exchange_methods=["cash_on_pickup", "meet_public"])
    other, _ = await _user("tiers-other@9d.example")
    await db.feedback.delete_many({"to_user_id": uid})
    for _ in range(10):
        await _tx(other, uid)  # 10 sales
        await _tx(uid, other)  # 10 purchases
    for _ in range(19):
        await _feedback(uid, "positive", "buyer_to_seller")
    await _feedback(uid, "neutral", "buyer_to_seller")  # yellow counts as neither
    await _feedback(uid, "positive", "seller_to_buyer")
    await _feedback(uid, "negative", "seller_to_buyer")  # 50% as a buyer
    async with _client(srv) as c:
        p = (await c.get(f"/api/users/{uid}/profile")).json()
    assert p["tiers"] == ["top_seller"]
    assert p["ratings"] == {"positive": 20, "neutral": 1, "negative": 1}
    assert p["exchange_methods"] == ["cash_on_pickup", "meet_public"]
    assert p["completed_as_seller"] == 10 and p["completed_as_buyer"] == 10


@pytest.mark.asyncio
async def test_listing_seller_info_uses_display_name():
    srv = _app()
    uid, _ = await _user("seller-name@9d.example", full_name="Private Person", display_name="Shop BC")
    lid = await _listing(uid)
    async with _client(srv) as c:
        body = (await c.get(f"/api/listings/{lid}")).json()
    assert body["seller_info"]["display_name"] == "Shop BC"
    assert "full_name" not in body["seller_info"]
    assert "Private Person" not in str(body)


# --- account settings ---------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_account_settings_and_name_propagates():
    srv = _app()
    from app.db import db
    uid, token = await _user("settings@9d.example")
    lid = await _listing(uid, seller_name="Settings")
    async with _client(srv, token) as c:
        ok = await c.patch("/api/users/me", json={"display_name": "  Bargain   Hunter ", "city": "Kelowna",
                                                  "exchange_methods": ["e_transfer", "e_transfer"]})
        bad_method = await c.patch("/api/users/me", json={"exchange_methods": ["paypal"]})
        bad_city = await c.patch("/api/users/me", json={"city": "Calgary"})
        bad_avatar = await c.patch("/api/users/me", json={"avatar_url": "http://res.cloudinary.com/x.png"})
        good_avatar = await c.patch("/api/users/me", json={"avatar_url": "https://res.cloudinary.com/demo/a.png"})
        clear_avatar = await c.patch("/api/users/me", json={"avatar_url": ""})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["display_name"] == "Bargain Hunter" and body["city"] == "Kelowna"
    assert body["exchange_methods"] == ["e_transfer"] and "password_hash" not in body
    assert bad_method.status_code == 422 and bad_city.status_code == 400 and bad_avatar.status_code == 400
    assert good_avatar.json()["avatar_url"].startswith("https://res.cloudinary.com/")
    assert clear_avatar.json()["avatar_url"] is None
    assert (await db.listings.find_one({"_id": ObjectId(lid)}))["seller_name"] == "Bargain Hunter"


@pytest.mark.asyncio
async def test_startup_backfills_display_names():
    _app()
    from app.db import db
    from app.accounts import accounts_startup
    uid, _ = await _user("backfill@9d.example", full_name="Old Timer Name")
    await db.users.update_one({"_id": ObjectId(uid)}, {"$unset": {"display_name": ""}})
    lid = await _listing(uid, seller_name="Old Timer Name", seller_verified=True)
    await accounts_startup()
    assert (await db.users.find_one({"_id": ObjectId(uid)}))["display_name"] == "Old N."
    listing = await db.listings.find_one({"_id": ObjectId(lid)})
    assert listing["seller_name"] == "Old N." and listing["seller_verified"] is False  # ID badge hidden (Q009)
    # The phone index only covers verified numbers: many accounts without a phone are fine
    await _user("nophone-a@9d.example")
    await _user("nophone-b@9d.example")


# --- delete account -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_refused_with_open_transaction_or_bids():
    srv = _app()
    uid, token = await _user("del-open@9d.example")
    other, _ = await _user("del-open-other@9d.example")
    tx = await _tx(uid, other, status="open")
    async with _client(srv, token) as c:
        wrong_pw = await c.post("/api/users/me/delete", json={"password": "nope"})
        open_tx = await c.post("/api/users/me/delete", json={"password": PASSWORD})
        from app.db import db
        await db.transactions.update_one({"_id": ObjectId(tx)}, {"$set": {"status": "completed"}})
        await _listing(uid, bid_count=2)
        with_bids = await c.post("/api/users/me/delete", json={"password": PASSWORD})
    assert wrong_pw.status_code == 403
    assert open_tx.status_code == 409 and "transactions" in open_tx.json()["detail"]
    assert with_bids.status_code == 409 and "bids" in with_bids.json()["detail"]


@pytest.mark.asyncio
async def test_delete_account_anonymises_and_keeps_records():
    srv = _app()
    from app.db import db
    email = "del-ok@9d.example"
    uid, token = await _user(email, full_name="Gone Person", phone="+12505550121", phone_verified=True)
    other, _ = await _user("del-ok-other@9d.example")
    tx = await _tx(other, uid)
    lid = await _listing(uid, bid_count=0)
    await db.feedback.insert_one({"from_user_id": uid, "from_user_name": "Gone P.", "to_user_id": other,
                                  "rating": "positive", "comment": "great", "transaction_id": tx})
    await db.watchlist.insert_one({"user_id": uid, "listing_id": lid})
    async with _client(srv, token) as c:
        resp = await c.post("/api/users/me/delete", json={"password": PASSWORD})
        after = await c.get("/api/auth/me")
        profile = await c.get(f"/api/users/{uid}/profile")
        login = await c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    assert after.status_code == 401 and profile.status_code == 404 and login.status_code == 401
    doc = await db.users.find_one({"_id": ObjectId(uid)})
    assert doc["deleted_at"] and doc["email"] != email and doc["phone"] is None
    assert doc["full_name"] == "Deleted user" and doc["display_name"] == "Deleted user"
    assert (await db.transactions.find_one({"_id": ObjectId(tx)}))["status"] == "completed"
    assert (await db.listings.find_one({"_id": ObjectId(lid)}))["status"] == "cancelled"
    assert (await db.feedback.find_one({"transaction_id": tx}))["from_user_name"] == "Deleted user"
    assert await db.watchlist.count_documents({"user_id": uid}) == 0
    # The email and phone are free for a new account
    await _clean("del-ok@9d.example")
    async with _client(srv) as c:
        again = await c.post("/api/auth/register", json=_signup(email, "250-555-0121"))
    assert again.status_code == 200, again.text
