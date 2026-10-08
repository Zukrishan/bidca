from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

import logging
from datetime import datetime, timezone
from typing import Optional

from app.db import db
from app.realtime import send_user_notification

logger = logging.getLogger(__name__)


def calculate_positive_percentage(user: dict) -> float:
    total = user.get("total_ratings", 0)
    if total == 0:
        return 100.0
    positive = user.get("positive_ratings", 0)
    return round((positive / total) * 100, 1)

async def create_notification(user_id: str, type: str, message: str, listing_id: Optional[str] = None,
                              extra: Optional[dict] = None):
    notification = {
        "user_id": user_id,
        "type": type,
        "message": message,
        "listing_id": listing_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
    }
    result = await db.notifications.insert_one(notification)
    # insert_one adds a BSON ObjectId _id to the dict, which Socket.IO can't serialise
    notification["_id"] = str(result.inserted_id)

    # Real-time push is best effort: it must never fail the bid/sale that triggered it
    try:
        await send_user_notification(user_id, notification)
    except Exception as exc:
        logger.error("Notification push failed for user %s: %s", user_id, exc)


def parse_object_id(value: str, not_found: str = "Not found") -> ObjectId:
    """Parse a path id into an ObjectId; a malformed id is a 404 (`not_found`), never a 500."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=not_found)
