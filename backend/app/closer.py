"""
closer.py — background auction closer and sniper-bid executor.

Exposes:
  run_once(db)  — single pass; used by tests and the background loop.
  start_closer(db, sio)  — starts the 30-second asyncio loop on startup.
  stop_closer()  — cancels the loop on shutdown.
"""

import asyncio
import html
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Module-level handle so shutdown can cancel it
_closer_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Bid-increment helper (mirrors server.py — avoid circular import)
# ---------------------------------------------------------------------------

def _get_bid_increment(current_price: float) -> float:
    if current_price < 25:
        return 1
    elif current_price < 100:
        return 5
    elif current_price < 250:
        return 10
    elif current_price < 500:
        return 25
    elif current_price < 1000:
        return 50
    elif current_price < 2500:
        return 100
    elif current_price < 5000:
        return 250
    else:
        return 500


# ---------------------------------------------------------------------------
# Notification helper (in-app; does not import server.py sio at module level)
# ---------------------------------------------------------------------------

async def _create_notification(db, user_id: str, type_: str, message: str, listing_id: str | None = None):
    from datetime import datetime, timezone
    notification = {
        "user_id": user_id,
        "type": type_,
        "message": message,
        "listing_id": listing_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.notifications.insert_one(notification)
    notification["_id"] = str(result.inserted_id)  # JSON-safe for the Socket.IO push
    # Real-time push is best effort; the stored notification is the source of truth (backlog B2)
    try:
        from app.realtime import send_user_notification
        await send_user_notification(user_id, notification)
    except Exception as exc:
        logger.error("Notification push failed for user %s: %s", user_id, exc)
    return notification


# ---------------------------------------------------------------------------
# Sniper bid execution
# ---------------------------------------------------------------------------

async def _execute_sniper_bids(db) -> None:
    """Execute all sniper_bids whose execute_at <= now and status == 'pending'."""
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor = db.sniper_bids.find({"status": "pending", "execute_at": {"$lte": now_iso}})
    sniper_bids = []
    async for sb in cursor:
        sniper_bids.append(sb)

    for sb in sniper_bids:
        await _execute_single_sniper(db, sb)


async def _execute_single_sniper(db, sb: dict) -> None:
    from bson import ObjectId

    sb_id = sb["_id"]
    listing_id = sb["listing_id"]
    user_id = sb["user_id"]
    max_bid = sb["max_bid"]

    # Mark as executed (idempotent — if already executed skip)
    result = await db.sniper_bids.find_one_and_update(
        {"_id": sb_id, "status": "pending"},
        {"$set": {"status": "executed"}},
        return_document=True,
    )
    if result is None:
        return  # Already picked up by another pass

    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except Exception:
        listing = await db.listings.find_one({"listing_id": listing_id})

    if not listing or listing.get("status") != "active":
        logger.info("Sniper bid %s: listing %s not active, skipping", sb_id, listing_id)
        return

    # Bids and notifications key on the stringified listing _id, as server.py does
    listing_id = str(listing["_id"])

    user = await db.users.find_one({"_id": user_id} if not isinstance(user_id, str) else {"_id": user_id})
    if user is None:
        # Try string comparison
        try:
            from bson import ObjectId as OID
            user = await db.users.find_one({"_id": OID(user_id)})
        except Exception:
            pass
    if user is None:
        logger.warning("Sniper bid %s: user %s not found", sb_id, user_id)
        return

    current_bid = listing.get("current_bid", listing.get("starting_bid", 0))
    bid_count = listing.get("bid_count", 0)
    bid_increment = _get_bid_increment(current_bid)
    min_bid = current_bid + bid_increment if bid_count > 0 else current_bid

    if max_bid < min_bid:
        logger.info("Sniper bid %s: max_bid %.2f < min_bid %.2f, skipping", sb_id, max_bid, min_bid)
        return

    current_max_bid = listing.get("highest_bidder_max_bid") or 0
    current_highest_bidder = listing.get("highest_bidder_id")

    user_id_str = str(user["_id"])

    if current_highest_bidder and str(current_highest_bidder) == user_id_str:
        # Already winning — update max if higher
        if max_bid > current_max_bid:
            await db.listings.update_one(
                {"_id": listing["_id"]},
                {"$set": {"highest_bidder_max_bid": max_bid}},
            )
        return

    if current_max_bid > 0:
        if max_bid > current_max_bid:
            new_current_bid = min(current_max_bid + bid_increment, max_bid)
            new_highest_bidder = user_id_str
            new_max_bid = max_bid
            # Notify outbid user, in-app and by email (FR-32)
            if current_highest_bidder:
                outbid_msg = f"You've been outbid on '{listing['title']}'! Current bid: ${new_current_bid:.2f}"
                await _create_notification(db, str(current_highest_bidder), "outbid", outbid_msg, listing_id)
                from app.helpers import email_user
                await email_user(str(current_highest_bidder), f"You've been outbid: {listing['title']}",
                                 outbid_msg, f"/auctions/{listing_id}")
        else:
            new_current_bid = min(max_bid + bid_increment, current_max_bid)
            new_highest_bidder = str(current_highest_bidder)
            new_max_bid = current_max_bid
            # Notify sniper bidder they lost
            await _create_notification(
                db,
                user_id_str,
                "outbid",
                f"Your sniper bid on '{listing['title']}' was outbid. Current bid: ${new_current_bid:.2f}",
                listing_id,
            )
    else:
        new_current_bid = listing.get("starting_bid", 0)
        new_highest_bidder = user_id_str
        new_max_bid = max_bid

    reserve_met = True
    if listing.get("reserve_price"):
        reserve_met = new_current_bid >= listing["reserve_price"]

    now_iso = datetime.now(timezone.utc).isoformat()
    bid_doc = {
        "listing_id": listing_id,
        "bidder_id": user_id_str,
        "bidder_name": user.get("full_name", ""),
        "amount": new_current_bid,
        "max_bid": max_bid,
        "is_auto_bid": True,
        "is_sniper": True,
        "created_at": now_iso,
    }
    await db.bids.insert_one(bid_doc)

    new_bid_increment = _get_bid_increment(new_current_bid)
    await db.listings.update_one(
        {"_id": listing["_id"]},
        {
            "$set": {
                "current_bid": new_current_bid,
                "bid_increment": new_bid_increment,
                "highest_bidder_id": new_highest_bidder,
                "highest_bidder_name": user.get("full_name", "") if new_highest_bidder == user_id_str else listing.get("highest_bidder_name"),
                "highest_bidder_max_bid": new_max_bid,
                "reserve_met": reserve_met,
            },
            "$inc": {"bid_count": 1},
        },
    )

    logger.info("Sniper bid %s executed: listing=%s bid=%.2f", sb_id, listing_id, new_current_bid)


# ---------------------------------------------------------------------------
# Auction closing
# ---------------------------------------------------------------------------

async def _close_due_auctions(db, sio=None) -> None:
    """Close all auctions whose end_time <= now and status == 'active'."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Iterate until no more due auctions
    while True:
        listing = await db.listings.find_one_and_update(
            {
                "listing_type": {"$in": ["auction", "auction_bin"]},
                "status": "active",
                "end_time": {"$lte": now_iso},
            },
            {"$set": {"status": "closing"}},  # transient sentinel — prevents double-close
            return_document=True,
        )
        if listing is None:
            break
        await _close_listing(db, listing, sio)


async def _close_listing(db, listing: dict, sio=None) -> None:
    from bson import ObjectId

    listing_id = str(listing["_id"])
    seller_id = str(listing.get("seller_id", ""))
    title = listing.get("title", "")

    highest_bidder_id = listing.get("highest_bidder_id")
    current_bid = listing.get("current_bid", 0)
    reserve_met = listing.get("reserve_met", True)
    reserve_price = listing.get("reserve_price")

    # Re-evaluate reserve_met at close time
    if reserve_price:
        reserve_met = current_bid >= reserve_price

    from app.email import send_email

    if highest_bidder_id and reserve_met:
        # SOLD
        winner_id = str(highest_bidder_id)
        sold_price = current_bid
        now_iso = datetime.now(timezone.utc).isoformat()

        # Atomic transition from 'closing' → 'sold'
        await db.listings.update_one(
            {"_id": listing["_id"], "status": "closing"},
            {
                "$set": {
                    "status": "sold",
                    "winner_id": winner_id,
                    "sold_price": sold_price,
                    "closed_at": now_iso,
                }
            },
        )

        # Create transaction (idempotent by listing_id + type)
        existing_tx = await db.transactions.find_one({"listing_id": listing_id, "type": "auction"})
        if not existing_tx:
            await db.transactions.insert_one({
                "listing_id": listing_id,
                "seller_id": seller_id,
                "buyer_id": winner_id,
                "amount": sold_price,
                "type": "auction",
                "status": "open",  # no money involved (NFR-07); open until both sides complete
                "created_at": now_iso,
            })

        # Update user counters
        await db.users.update_one(
            {"_id": ObjectId(winner_id)},
            {"$inc": {"auctions_won": 1, "total_purchases": 1}},
        )
        await db.users.update_one(
            {"_id": ObjectId(seller_id)},
            {"$inc": {"total_sales": 1, "total_sales_amount": sold_price}},
        )

        # In-app notifications — wording from the client source (FR-11)
        winner_msg = f"You won! You won the bid for '{title}' at ${sold_price:.2f}. Message the seller to arrange the exchange."
        seller_msg = f"Your item '{title}' has a winning bidder at ${sold_price:.2f}. Message the buyer to arrange the exchange."
        await _create_notification(db, winner_id, "auction_won", winner_msg, listing_id)
        await _create_notification(db, seller_id, "item_sold", seller_msg, listing_id)

        # Emails go out immediately — this is time-sensitive (source L95–99)
        try:
            winner_user = await db.users.find_one({"_id": ObjectId(winner_id)})
            seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
            if winner_user:
                await send_email(
                    to=winner_user["email"],
                    subject=f"You won the bid for {title}",
                    html=f"<p>{html.escape(winner_msg)}</p>",  # titles are user input
                )
            if seller_user:
                await send_email(
                    to=seller_user["email"],
                    subject=f"Your item {title} has a winning bidder",
                    html=f"<p>{html.escape(seller_msg)}</p>",  # titles are user input
                )
        except Exception as exc:
            logger.error("Email send failed for listing %s: %s", listing_id, exc)

        await _notify_losing_bidders(listing_id, title, winner_id)

        # Socket.IO
        if sio:
            try:
                await sio.emit(
                    "auction_ended",
                    {
                        "listing_id": listing_id,
                        "status": "sold",
                        "sold_price": sold_price,
                        "winner_id": winner_id,
                    },
                    room=f"auction_{listing_id}",
                )
            except Exception as exc:
                logger.error("Socket.IO emit failed for listing %s: %s", listing_id, exc)

        logger.info("Auction %s closed: SOLD to %s for %.2f", listing_id, winner_id, sold_price)

    else:
        # UNSOLD — no bids or reserve not met
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.listings.update_one(
            {"_id": listing["_id"], "status": "closing"},
            {"$set": {"status": "unsold", "closed_at": now_iso}},
        )

        # Notify seller
        seller_msg = f"Your auction '{title}' ended without a sale."
        if reserve_price and highest_bidder_id:
            seller_msg = f"Your auction '{title}' ended — reserve price not met."
        await _create_notification(db, seller_id, "auction_unsold", seller_msg, listing_id)

        try:
            seller_user = await db.users.find_one({"_id": ObjectId(seller_id)})
            if seller_user:
                await send_email(
                    to=seller_user["email"],
                    subject=f"Auction ended unsold: {title}",
                    html=f"<p>{html.escape(seller_msg)}</p>",  # titles are user input
                )
        except Exception as exc:
            logger.error("Email send failed for listing %s: %s", listing_id, exc)

        # Bidders when the reserve wasn't met: nobody won
        await _notify_losing_bidders(listing_id, title, None)

        if sio:
            try:
                await sio.emit(
                    "auction_ended",
                    {"listing_id": listing_id, "status": "unsold"},
                    room=f"auction_{listing_id}",
                )
            except Exception as exc:
                logger.error("Socket.IO emit failed for listing %s: %s", listing_id, exc)

        logger.info("Auction %s closed: UNSOLD", listing_id)


async def _notify_losing_bidders(listing_id: str, title: str, winner_id: str | None) -> None:
    # Best effort: a failed notification must not leave the listing stuck in 'closing'
    try:
        from app.helpers import notify_losing_bidders
        await notify_losing_bidders(listing_id, title, winner_id)
    except Exception as exc:
        logger.error("Losing-bidder notifications failed for listing %s: %s", listing_id, exc)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def run_once(db, sio=None) -> None:
    """Single closer pass: execute due sniper bids then close due auctions."""
    try:
        await _execute_sniper_bids(db)
    except Exception as exc:
        logger.error("Sniper bid execution error: %s", exc)
    try:
        await _close_due_auctions(db, sio)
    except Exception as exc:
        logger.error("Auction close error: %s", exc)


async def _closer_loop(db, sio, interval: int = 30) -> None:
    logger.info("Auction closer started (interval=%ds)", interval)
    while True:
        await run_once(db, sio)
        await asyncio.sleep(interval)


def start_closer(db, sio, interval: int = 30) -> None:
    """Start the background closer task. Call from FastAPI startup."""
    global _closer_task
    _closer_task = asyncio.get_event_loop().create_task(
        _closer_loop(db, sio, interval)
    )
    logger.info("Closer task created")


def stop_closer() -> None:
    """Cancel the background closer task. Call from FastAPI shutdown."""
    global _closer_task
    if _closer_task and not _closer_task.done():
        _closer_task.cancel()
        logger.info("Closer task cancelled")
    _closer_task = None
