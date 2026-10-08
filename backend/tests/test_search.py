"""
test_search.py — `q` is plain text, not a regex: special characters can't 500 the API or
inject patterns (found during the Phase 4 browse page).
"""

from __future__ import annotations

import os
import sys
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


@pytest.mark.asyncio
async def test_search_treats_query_as_plain_text():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server as srv
    from app.db import db
    from httpx import AsyncClient, ASGITransport

    await db.listings.delete_many({"title": {"$regex": "^SRCH "}})
    for title in ("SRCH C++ primer", "SRCH Cxx primer"):
        await db.listings.insert_one({"title": title, "description": "x", "status": "active", "end_time": "2099-01-01", "seller_id": "000000000000000000000001"})

    async with AsyncClient(transport=ASGITransport(app=srv.fastapi_app), base_url="http://test") as c:
        for q in ("(", "[", "*", "a{1000}"):
            assert (await c.get("/api/listings", params={"q": q})).status_code == 200, q
        hits = (await c.get("/api/listings", params={"q": "SRCH C++"})).json()["listings"]
        assert [l["title"] for l in hits] == ["SRCH C++ primer"]
        assert (await c.get("/api/listings", params={"q": "SRCH C.."})).json()["total"] == 0
