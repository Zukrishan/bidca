from datetime import datetime, timezone
from typing import Optional

from app.db import db
from app.realtime import send_user_notification


def calculate_positive_percentage(user: dict) -> float:
    total = user.get("total_ratings", 0)
    if total == 0:
        return 100.0
    positive = user.get("positive_ratings", 0)
    return round((positive / total) * 100, 1)

async def create_notification(user_id: str, type: str, message: str, listing_id: Optional[str] = None):
    notification = {
        "user_id": user_id,
        "type": type,
        "message": message,
        "listing_id": listing_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Send real-time notification
    await send_user_notification(user_id, notification)
