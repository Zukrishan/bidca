"""
test_9e_listings.py — Phase 9e: the listing form rules (R48 / FR-05), seller cancel and suspension
(R49 / FR-29, Q010, Q012), the monthly listing cap (R53 / FR-34, Q015) and browse order (FR-07).
The vehicle checklist (R50 / FR-30) is a static web file; its disclosure fields are tested here.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_hardening import _app, _client, _listing, _user  # noqa: E402  (same fixtures, same shared DB)

DISCLOSURE = {
    "accident_history": False, "mechanical_issues": True, "mechanical_description": "AC needs a recharge",
    "previous_owners": 2, "safety_certificate": True, "odometer_km": 123456, "liens": False,
}


def _form(**extra):
    return {"title": "9E chair", "category": "Home & Garden", "subcategory": "Furniture",
            "description": "A sturdy chair", "condition": "good", "city": "Victoria", "starting_bid": 10, **extra}


# --- R48 required fields, subcategory, category fields ---------------------------------------

@pytest.mark.asyncio
async def test_required_fields_are_checked_by_the_server():
    srv = _app()
    _, token = await _user("req@9e.example")
    async with _client(srv, token) as c:
        blank_title = await c.post("/api/listings", json=_form(title="  "))
        no_city = await c.post("/api/listings", json=_form(city=None))
        no_category = await c.post("/api/listings", json=_form(category=None, subcategory=None))
        ok = await c.post("/api/listings", json=_form())
    assert blank_title.status_code == 422 and "title" in blank_title.json()["detail"]
    assert no_city.status_code == 422 and "city" in no_city.json()["detail"]
    assert no_category.status_code == 422 and "category" in no_category.json()["detail"]
    assert ok.status_code == 201 and ok.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_subcategory_must_belong_to_the_category():
    srv = _app()
    _, token = await _user("sub@9e.example")
    async with _client(srv, token) as c:
        wrong = await c.post("/api/listings", json=_form(subcategory="Cars"))
        orphan = await c.post("/api/listings", json=_form(category=None, subcategory="Furniture", draft=True))
        unknown = await c.post("/api/listings", json=_form(category="Spaceships", subcategory=None))
    assert wrong.status_code == 422 and "Subcategory" in wrong.json()["detail"]
    assert orphan.status_code == 422
    assert unknown.status_code == 422


@pytest.mark.asyncio
async def test_category_fields_keep_only_the_category_s_own_fields():
    srv = _app()
    _, token = await _user("catf@9e.example")
    async with _client(srv, token) as c:
        r = await c.post("/api/listings", json=_form(
            category="Electronics", subcategory="Smartphones",
            category_fields={"brand": "Pixel", "model": "8", "year": 2020, "junk": "x"}))
        bad = await c.post("/api/listings", json=_form(
            category="Vehicles", subcategory="Cars", vehicle_disclosure=DISCLOSURE,
            category_fields={"year": "twenty"}))
    assert r.status_code == 201, r.text
    assert r.json()["category_fields"] == {"brand": "Pixel", "model": "8"}
    assert r.json()["vehicle_disclosure"] is None
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_vehicles_need_the_full_disclosure():
    srv = _app()
    _, token = await _user("veh@9e.example")
    car = dict(category="Vehicles", subcategory="Cars",
               category_fields={"year": 2015, "make": "Honda", "model": "Civic", "mileage": 123456})
    async with _client(srv, token) as c:
        none = await c.post("/api/listings", json=_form(**car))
        no_story = await c.post("/api/listings", json=_form(**car, vehicle_disclosure={**DISCLOSURE, "accident_history": True}))
        partial = await c.post("/api/listings", json=_form(**car, vehicle_disclosure={"liens": False}))
        ok = await c.post("/api/listings", json=_form(**car, vehicle_disclosure=DISCLOSURE))
        draft = await c.post("/api/listings", json=_form(**car, draft=True))
    assert none.status_code == 422 and "Vehicle disclosure" in none.json()["detail"]
    assert no_story.status_code == 422 and "accident_description" in no_story.json()["detail"]
    assert partial.status_code == 422
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["vehicle_disclosure"]["odometer_km"] == 123456 and body["vehicle_disclosure"]["liens"] is False
    assert body["category_fields"] == {"year": 2015, "make": "Honda", "model": "Civic", "mileage": 123456}
    assert draft.status_code == 201  # a draft may be incomplete


# --- R48 drafts ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_draft_is_private_editable_and_submitted_for_approval():
    srv = _app()
    seller, token = await _user("draft@9e.example")
    _, other = await _user("draft-other@9e.example")
    async with _client(srv, token) as c:
        r = await c.post("/api/listings", json={"title": "9E half-done", "draft": True})
        assert r.status_code == 201, r.text
        draft = r.json()
        assert draft["status"] == "draft" and draft["end_time"] is None
        lid = draft["_id"]

        assert (await c.get(f"/api/listings/{lid}")).status_code == 200  # the seller sees it
        mine = (await c.get("/api/users/me/listings", params={"status": "draft"})).json()["listings"]
        assert [l["_id"] for l in mine] == [lid]

        incomplete = await c.post(f"/api/listings/{lid}/submit")
        assert incomplete.status_code == 422

        edited = await c.put(f"/api/listings/{lid}", json={k: v for k, v in _form().items() if k != "title"})
        assert edited.status_code == 200, edited.text
        assert edited.json()["title"] == "9E half-done" and edited.json()["category"] == "Home & Garden"

        submitted = await c.post(f"/api/listings/{lid}/submit")
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "pending" and submitted.json()["end_time"]

        assert (await c.put(f"/api/listings/{lid}", json={"title": "late"})).status_code == 400
        assert (await c.post(f"/api/listings/{lid}/submit")).status_code == 400

    async with _client(srv) as anon:
        assert (await anon.get(f"/api/listings/{lid}")).status_code == 404
        assert (await anon.get("/api/listings", params={"status": "draft"})).status_code == 400
    async with _client(srv, other) as c:
        assert (await c.get(f"/api/listings/{lid}")).status_code == 404
        assert (await c.put(f"/api/listings/{lid}", json={"title": "x"})).status_code == 404


# --- R53 monthly cap ------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_monthly_cap_counts_submissions_not_drafts_or_rejected(monkeypatch):
    srv = _app()
    monkeypatch.setenv("LISTING_CAP_PER_MONTH", "2")
    _, token = await _user("cap@9e.example")
    _, admin = await _user("cap-admin@9e.example", role="admin")
    async with _client(srv, token) as c:
        a = await c.post("/api/listings", json=_form())
        await c.post("/api/listings", json=_form())
        third = await c.post("/api/listings", json=_form())
        draft = await c.post("/api/listings", json=_form(draft=True))
        quota = (await c.get("/api/users/me/listing-quota")).json()
        blocked_submit = await c.post(f"/api/listings/{draft.json()['_id']}/submit")
    assert third.status_code == 429 and "limit of 2" in third.json()["detail"]
    assert draft.status_code == 201
    assert quota["cap"] == 2 and quota["used"] == 2 and quota["remaining"] == 0
    assert blocked_submit.status_code == 429

    async with _client(srv, admin) as c:
        r = await c.put(f"/api/admin/listings/{a.json()['_id']}", json={"status": "rejected"})
        assert r.status_code == 200
    async with _client(srv, token) as c:
        assert (await c.post(f"/api/listings/{draft.json()['_id']}/submit")).status_code == 200


@pytest.mark.asyncio
async def test_relist_counts_toward_the_cap(monkeypatch):
    srv = _app()
    monkeypatch.setenv("LISTING_CAP_PER_MONTH", "1")
    seller, token = await _user("cap-relist@9e.example")
    old = await _listing(seller, status="unsold")
    async with _client(srv, token) as c:
        assert (await c.post(f"/api/listings/{old}/relist")).status_code == 200
        assert (await c.post("/api/listings", json=_form())).status_code == 429


def test_month_start_is_pacific():
    from app.listing_rules import month_start, next_month_start
    # 06:30 UTC on 1 Nov 2026 is still 31 Oct in Vancouver (PDT, UTC-7)
    now = datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc)
    assert month_start(now) == datetime(2026, 10, 1, 7, 0, tzinfo=timezone.utc)
    assert next_month_start(now) == datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
    # December rolls into January — midnight Pacific, whatever offset the tz database gives BC then
    from app.listing_rules import PACIFIC
    jan = next_month_start(datetime(2026, 12, 15, tzinfo=timezone.utc)).astimezone(PACIFIC)
    assert (jan.year, jan.month, jan.day, jan.hour, jan.minute) == (2027, 1, 1, 0, 0)


def test_free_period_setting(monkeypatch):
    from app.config import free_period_start
    monkeypatch.setenv("FREE_PERIOD_START", "2026-12-01")
    assert free_period_start().isoformat() == "2026-12-01"
    monkeypatch.setenv("FREE_PERIOD_START", "")
    assert free_period_start() is None


# --- R49 seller cancel ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_withdraw_pending_and_cancel_unbid_listing_without_penalty():
    srv = _app()
    from app.db import db
    seller, token = await _user("cancel-free@9e.example")
    pending = await _listing(seller, status="pending")
    active = await _listing(seller)
    async with _client(srv, token) as c:
        preview = (await c.get(f"/api/listings/{active}/cancel-preview")).json()
        w = await c.post(f"/api/listings/{pending}/cancel")
        a = await c.post(f"/api/listings/{active}/cancel")
        again = await c.post(f"/api/listings/{active}/cancel")
    assert preview["outcome"] == "cancel" and preview["penalty"] is None
    assert w.json()["outcome"] == "withdraw" and a.json()["outcome"] == "cancel"
    assert again.status_code == 400
    user = await db.users.find_one({"email": "cancel-free@9e.example"})
    assert not user.get("suspended_until") and not user.get("is_suspended")
    async with _client(srv) as anon:
        assert (await anon.get(f"/api/listings/{active}")).status_code == 404  # cancelled isn't public


@pytest.mark.asyncio
async def test_only_the_seller_can_cancel():
    srv = _app()
    seller, _ = await _user("cancel-owner@9e.example")
    _, other = await _user("cancel-other@9e.example")
    lid = await _listing(seller)
    async with _client(srv, other) as c:
        assert (await c.post(f"/api/listings/{lid}/cancel")).status_code == 404


async def _bid_listing(seller, bidder_ids, title):
    from app.db import db
    lid = await _listing(seller, title=title, listing_type="auction", bid_count=len(bidder_ids), current_bid=15.0)
    for b in bidder_ids:
        await db.bids.insert_one({"listing_id": lid, "bidder_id": b, "bidder_name": "B", "amount": 15.0,
                                  "created_at": datetime.now(timezone.utc).isoformat()})
    return lid


@pytest.mark.asyncio
async def test_cancel_with_bids_needs_confirmation_notifies_bidders_and_suspends_on_a_schedule(monkeypatch):
    srv = _app()
    from app.db import db
    monkeypatch.delenv("SELLER_CANCEL_SUSPENSION_DAYS", raising=False)
    seller, token = await _user("cancel-bids@9e.example")
    b1, _ = await _user("cancel-b1@9e.example")
    b2, _ = await _user("cancel-b2@9e.example")
    email = "cancel-bids@9e.example"

    first = await _bid_listing(seller, [b1, b2], "9E first")
    async with _client(srv, token) as c:
        preview = (await c.get(f"/api/listings/{first}/cancel-preview")).json()
        unconfirmed = await c.post(f"/api/listings/{first}/cancel")
        done = await c.post(f"/api/listings/{first}/cancel", json={"confirm_penalty": True})
    assert preview["outcome"] == "cancel_with_penalty" and "2 days" in preview["message"]
    assert unconfirmed.status_code == 409 and "2 days" in unconfirmed.json()["detail"]
    assert done.status_code == 200, done.text
    assert done.json()["penalty"] == {"offence": 1, "suspension_days": 2, "until_admin_review": False}
    user = await db.users.find_one({"email": email})
    left = datetime.fromisoformat(user["suspended_until"]) - datetime.now(timezone.utc)
    assert timedelta(days=2) - timedelta(minutes=1) < left <= timedelta(days=2)
    assert "9E first" in user["suspension_reason"]
    for b in (b1, b2):
        assert await db.notifications.find_one({"user_id": b, "type": "listing_cancelled", "listing_id": first})
    assert (await db.listings.find_one({"title": "9E first"}))["status"] == "cancelled"
    assert await db.seller_cancellations.count_documents({"seller_id": seller, "with_bids": True}) == 1

    second = await _bid_listing(seller, [b1], "9E second")
    async with _client(srv, token) as c:
        r = await c.post(f"/api/listings/{second}/cancel", json={"confirm_penalty": True})
    assert r.json()["penalty"]["suspension_days"] == 7
    user = await db.users.find_one({"email": email})
    left = datetime.fromisoformat(user["suspended_until"]) - datetime.now(timezone.utc)
    assert left > timedelta(days=6)

    third = await _bid_listing(seller, [b1], "9E third")
    async with _client(srv, token) as c:
        r = await c.post(f"/api/listings/{third}/cancel", json={"confirm_penalty": True})
    assert r.json()["penalty"]["until_admin_review"] is True
    user = await db.users.find_one({"email": email})
    assert user["is_suspended"] is True and "admin review" in user["suspension_reason"]


@pytest.mark.asyncio
async def test_old_cancellations_fall_out_of_the_window(monkeypatch):
    srv = _app()
    from app.db import db
    monkeypatch.setenv("SELLER_CANCEL_SUSPENSION_DAYS", "1,3")
    seller, token = await _user("cancel-window@9e.example")
    b1, _ = await _user("cancel-window-b@9e.example")
    long_ago = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    await db.seller_cancellations.insert_one({"seller_id": seller, "with_bids": True, "created_at": long_ago})
    lid = await _bid_listing(seller, [b1], "9E window")
    async with _client(srv, token) as c:
        r = await c.post(f"/api/listings/{lid}/cancel", json={"confirm_penalty": True})
    assert r.json()["penalty"] == {"offence": 1, "suspension_days": 1, "until_admin_review": False}


# --- FR-07 browse order ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_browse_default_puts_fixed_price_after_auctions():
    srv = _app()
    from app.db import db
    seller, token = await _user("order@9e.example")
    _, admin = await _user("order-admin@9e.example", role="admin")
    async with _client(srv, token) as c:
        fixed = (await c.post("/api/listings", json=_form(
            title="9E order fixed", listing_type="fixed_price", buy_it_now_price=30, duration_days=1))).json()["_id"]
        auction = (await c.post("/api/listings", json=_form(title="9E order auction", duration_days=10))).json()["_id"]
    async with _client(srv, admin) as c:
        for lid in (fixed, auction):
            await c.put(f"/api/admin/listings/{lid}", json={"status": "active"})
    async with _client(srv) as anon:
        ids = [l["_id"] for l in (await anon.get("/api/listings", params={"q": "9E order"})).json()["listings"]]
    assert ids == [auction, fixed]
