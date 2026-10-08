"""
test_visibility.py — contract D8 (pending/rejected listings are seller- and admin-only) and
D9 (the leading bidder's proxy max is never returned to non-admins).

Uses mongomock-motor; no real MongoDB required.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "bidca_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")

import mongomock_motor  # type: ignore

_mock_client = mongomock_motor.AsyncMongoMockClient()


async def _setup():
    """Import the app against mongomock and seed seller, stranger, admin and one listing per status."""
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server as srv
    from app.db import db
    from app.security import create_access_token

    await db.users.delete_many({"email": {"$regex": "@vis.test$"}})
    await db.listings.delete_many({"title": {"$regex": "^VIS "}})

    users = {}
    for name, role in (("seller", "user"), ("stranger", "user"), ("admin", "admin")):
        res = await db.users.insert_one({
            "email": f"{name}@vis.test", "full_name": name.title(), "city": "Victoria",
            "role": role, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        users[name] = create_access_token(str(res.inserted_id), f"{name}@vis.test")
    # listings store seller_id as the stringified user id, as POST /listings does
    seller_id = str((await db.users.find_one({"email": "seller@vis.test"}))["_id"])

    listings = {}
    end = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    for status in ("pending", "rejected", "active", "sold"):
        res = await db.listings.insert_one({
            "title": f"VIS {status}", "description": "x", "category": "Tools",
            "seller_id": seller_id, "status": status, "listing_type": "auction",
            "current_bid": 10.0, "starting_bid": 10.0, "bid_count": 0, "end_time": end,
            "highest_bidder_max_bid": 99.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        listings[status] = str(res.inserted_id)
    return srv, users, listings, seller_id


async def _get(srv, path, token=None):
    from httpx import AsyncClient, ASGITransport
    cookies = {"access_token": token} if token else None
    async with AsyncClient(transport=ASGITransport(app=srv.fastapi_app), base_url="http://test", cookies=cookies) as c:
        return await c.get(path)


@pytest.mark.asyncio
async def test_unapproved_listing_hidden_from_public():
    srv, users, listings, _ = await _setup()
    for status in ("pending", "rejected"):
        assert (await _get(srv, f"/api/listings/{listings[status]}")).status_code == 404
        assert (await _get(srv, f"/api/listings/{listings[status]}", users["stranger"])).status_code == 404


@pytest.mark.asyncio
async def test_unapproved_listing_visible_to_seller_and_admin():
    srv, users, listings, _ = await _setup()
    for who in ("seller", "admin"):
        resp = await _get(srv, f"/api/listings/{listings['pending']}", users[who])
        assert resp.status_code == 200, f"{who}: {resp.status_code}"
        assert resp.json()["title"] == "VIS pending"


@pytest.mark.asyncio
async def test_public_statuses_still_visible():
    srv, users, listings, _ = await _setup()
    for status in ("active", "sold"):
        assert (await _get(srv, f"/api/listings/{listings[status]}")).status_code == 200


@pytest.mark.asyncio
async def test_browse_rejects_non_public_status():
    srv, _, _, _ = await _setup()
    assert (await _get(srv, "/api/listings?status=pending")).status_code == 400
    assert (await _get(srv, "/api/listings?status=rejected")).status_code == 400
    resp = await _get(srv, "/api/listings?status=active&q=VIS")
    assert resp.status_code == 200
    assert [l["title"] for l in resp.json()["listings"]] == ["VIS active"]


@pytest.mark.asyncio
async def test_proxy_max_bid_never_exposed():
    srv, users, listings, _ = await _setup()
    detail = (await _get(srv, f"/api/listings/{listings['active']}", users["seller"])).json()
    assert "highest_bidder_max_bid" not in detail
    browse = (await _get(srv, "/api/listings?status=active&q=VIS")).json()["listings"]
    assert browse and all("highest_bidder_max_bid" not in l for l in browse)


@pytest.mark.asyncio
async def test_browse_filters_by_seller_and_profile_counts_listings():
    srv, _, _, seller_id = await _setup()
    resp = (await _get(srv, f"/api/listings?status=active&seller_id={seller_id}")).json()
    assert [l["title"] for l in resp["listings"]] == ["VIS active"]
    assert (await _get(srv, "/api/listings?status=active&seller_id=000000000000000000000000")).json()["total"] == 0
    profile = (await _get(srv, f"/api/users/{seller_id}/profile")).json()
    assert profile["active_listings"] == 1
