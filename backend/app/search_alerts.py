"""
search_alerts.py — FR-13: tell users when a newly public listing matches one of their saved searches.

`alert_saved_searches(listing)` is scheduled (FastAPI BackgroundTasks) when a listing becomes
`active`. It never raises: failures are logged so the admin action that triggered it is unaffected.
"""

import html
import logging
from datetime import datetime, timezone

from bson import ObjectId

from app.config import frontend_origin
from app.db import db
from app.email import send_email
from app.helpers import create_notification

logger = logging.getLogger(__name__)


def listing_price(listing: dict):
    """The price a saved-search price range is compared with."""
    if listing.get("listing_type") == "fixed_price":
        price = listing.get("buy_it_now_price")
        if price is None:
            price = listing.get("current_bid", listing.get("starting_bid"))
        return price
    price = listing.get("current_bid")
    return listing.get("starting_bid") if price is None else price


def search_matches(search: dict, listing: dict, price) -> bool:
    """True when every criterion the saved search sets matches. Plain substring, never a regex."""
    query = (search.get("query") or "").strip().lower()
    if query:
        haystack = f"{listing.get('title') or ''}\n{listing.get('description') or ''}".lower()
        if query not in haystack:
            return False
    if search.get("category") and search["category"] != listing.get("category"):
        return False
    if search.get("city") and search["city"] != listing.get("city"):
        return False
    if search.get("listing_type") and search["listing_type"] != listing.get("listing_type"):
        return False
    lo, hi = search.get("min_price"), search.get("max_price")
    if lo is not None or hi is not None:
        if price is None:
            return False
        if lo is not None and price < lo:
            return False
        if hi is not None and price > hi:
            return False
    return True


async def alert_saved_searches(listing: dict) -> int:
    """Notify the owners of matching saved searches about `listing`. Returns alerts sent."""
    try:
        return await _alert(listing)
    except Exception:
        logger.exception("saved-search alerts failed for listing %s", listing.get("_id"))
        return 0


async def _alert(listing: dict) -> int:
    listing_id = str(listing["_id"])
    seller_id = str(listing.get("seller_id"))
    price = listing_price(listing)
    price_text = f"${price:,.2f}" if isinstance(price, (int, float)) else "price on listing"
    title = listing.get("title") or "New listing"
    link = f"{frontend_origin()}/auctions/{listing_id}"

    sent = 0
    notified = set()
    cursor = db.saved_searches.find({"alerts_enabled": {"$ne": False}, "user_id": {"$ne": seller_id}})
    async for search in cursor:
        user_id = str(search["user_id"])
        if user_id in notified or not search_matches(search, listing, price):
            continue
        # One alert per user per listing, however many of their searches match (and across re-runs)
        if await db.saved_search_alerts.find_one({"listing_id": listing_id, "user_id": user_id}):
            notified.add(user_id)
            continue
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            user = None
        if not user or user.get("is_banned") or user.get("is_suspended"):
            continue
        notified.add(user_id)
        await db.saved_search_alerts.insert_one({
            "saved_search_id": str(search["_id"]), "listing_id": listing_id, "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        name = search.get("name") or "your saved search"
        await create_notification(
            user_id, "saved_search_match", f"New match for “{name}”: {title} — {price_text}", listing_id
        )
        if user.get("email"):
            # Titles and search names are user input: escape them in the HTML email
            safe_name, safe_title = html.escape(name), html.escape(title)
            await send_email(
                to=user["email"],
                subject=f"New match: {title}",
                html=(
                    f"<p>A new listing matches your saved search “{safe_name}”.</p>"
                    f"<p><strong>{safe_title}</strong> — {price_text}</p>"
                    f'<p><a href="{link}">{link}</a></p>'
                    "<p>To turn these alerts off, open your saved searches and switch alerts off "
                    "for this search, or delete it.</p>"
                ),
            )
        sent += 1
    return sent
