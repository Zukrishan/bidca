"""
test_notifications.py — backlog B2: the real-time notification payload must be JSON-serialisable.
Before the fix, an outbid notification crashed POST /listings/{id}/bid with a 500 whenever a
Socket.IO client was connected.
"""

from __future__ import annotations

import json
import os
import sys
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


@pytest.mark.asyncio
async def test_notification_payload_is_json_serialisable():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server  # noqa: F401
    from app import helpers

    sent = []

    async def fake_push(user_id, notification):
        sent.append(json.dumps(notification))  # raises TypeError on a BSON ObjectId

    with patch.object(helpers, "send_user_notification", fake_push):
        await helpers.create_notification("u1", "outbid", "You've been outbid", "l1")
    assert len(sent) == 1 and isinstance(json.loads(sent[0])["_id"], str)


@pytest.mark.asyncio
async def test_push_failure_does_not_raise():
    with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=_mock_client):
        import server  # noqa: F401
    from app import helpers

    with patch.object(helpers, "send_user_notification", AsyncMock(side_effect=RuntimeError("socket down"))):
        await helpers.create_notification("u1", "outbid", "x", "l1")  # must not raise
