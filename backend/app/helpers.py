from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

import html
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


async def email_user(user_id: str, subject: str, message: str, path: Optional[str] = None):
    """Email `message` (plain text, escaped here) to a user, with an optional site link. Best effort."""
    from app.config import frontend_origin
    from app.email import send_email
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("email"):
            return
        body = f"<p>{html.escape(message)}</p>"  # titles and names are user input
        if path:
            link = f"{frontend_origin()}{path}"
            body += f'<p><a href="{link}">{link}</a></p>'
        await send_email(to=user["email"], subject=subject, html=body)
    except Exception as exc:
        logger.error("Email to user %s failed: %s", user_id, exc)


async def notify_outbid(user_id: str, listing: dict, message: str):
    """Outbid alert: in-app and email, straight away (FR-32)."""
    listing_id = str(listing["_id"])
    await create_notification(user_id, "outbid", message, listing_id)
    await email_user(user_id, f"You've been outbid: {listing.get('title', '')}", message,
                     f"/auctions/{listing_id}")


async def notify_losing_bidders(listing_id: str, title: str, winner_id: Optional[str]):
    """Tell every bidder who didn't win that the auction is over (FR-11) — no silent status change."""
    bidder_ids = await db.bids.distinct("bidder_id", {"listing_id": listing_id})
    for bidder_id in bidder_ids:
        if bidder_id and str(bidder_id) != str(winner_id):
            await create_notification(str(bidder_id), "auction_lost",
                                      f"Auction ended — you didn't win '{title}'.", listing_id)


def parse_object_id(value: str, not_found: str = "Not found") -> ObjectId:
    """Parse a path id into an ObjectId; a malformed id is a 404 (`not_found`), never a 500."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail=not_found)
