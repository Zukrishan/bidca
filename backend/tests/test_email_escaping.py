"""
test_email_escaping.py — listing titles and saved-search names are user input; the HTML emails
built from them (closer won/sold, saved-search alerts) must escape them so a seller can't inject
links or markup into BidCa's own emails.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
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
EVIL = 'Drill <a href="https://evil.example">claim refund</a>'


def _import_app():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server  # noqa: F401


@pytest.mark.asyncio
async def test_closer_and_alert_emails_escape_user_text():
    _import_app()
    from app.db import db
    from app import closer, search_alerts

    sent = []

    async def capture(to, subject, html):
        sent.append(html)

    seller = await db.users.insert_one({"email": "esc-seller@x.ca", "full_name": "S", "city": "Victoria"})
    buyer = await db.users.insert_one({"email": "esc-buyer@x.ca", "full_name": "B", "city": "Victoria"})
    await db.saved_searches.insert_one({"user_id": str(buyer.inserted_id), "name": '<b>drills</b>', "query": "drill"})
    listing = {
        "title": EVIL, "description": "x", "category": "Tools", "seller_id": str(seller.inserted_id),
        "status": "active", "listing_type": "auction", "starting_bid": 10.0, "current_bid": 20.0,
        "bid_count": 1, "highest_bidder_id": str(buyer.inserted_id), "reserve_met": True,
        "end_time": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    }
    res = await db.listings.insert_one(dict(listing))
    listing["_id"] = res.inserted_id

    with patch("app.search_alerts.send_email", capture), patch("app.email.send_email", capture):
        await search_alerts.alert_saved_searches(listing)
        await closer.run_once(db)

    assert len(sent) >= 3, sent  # alert + winner + seller
    for body in sent:
        assert "<a href=\"https://evil.example\">" not in body
        assert "&lt;a href=" in body or "&lt;b&gt;" in body
