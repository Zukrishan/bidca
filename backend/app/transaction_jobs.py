"""
transaction_jobs.py — background rules for open transactions, run on every closer pass.

  No response (FR-26, Q013): a buyer who has not sent a message (or pressed Complete) within
    NO_RESPONSE_HOURS of the sale loses it — the transaction is `cancelled` (`no_response`), the
    buyer is locked for NO_RESPONSE_LOCK_HOURS (`suspended_until`) and gets a system `negative`
    rating, both sides are told, and the seller may relist.
  Reminders (FR-27, Q010): while a transaction is `open`, both sides are emailed every
    REMINDER_INTERVAL_HOURS, at most REMINDER_MAX times; the last one alerts the admins instead of
    going on forever. Completed, cancelled and disputed transactions get none.

Each step claims its transaction with one atomic find_one_and_update on stored timestamps, so a
pass is idempotent, two passes never act twice, and a restart picks up where it left off.
"""

import logging
from datetime import datetime, timezone

from bson import ObjectId

from app.config import no_response_lock, no_response_window, reminder_interval, reminder_max

logger = logging.getLogger(__name__)

NO_RESPONSE_LABEL = "No response within 24 hours"


async def notify_admins(type_: str, message: str, extra: dict | None = None) -> None:
    """In-app notification to every admin (dispute opened, reminders exhausted)."""
    from app.db import db
    from app.helpers import create_notification
    async for admin in db.users.find({"role": "admin"}, {"_id": 1}):
        await create_notification(str(admin["_id"]), type_, message, (extra or {}).get("listing_id"), extra=extra)


async def _title(db, listing_id: str) -> str:
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)}, {"title": 1})
    except Exception:
        listing = None
    return (listing or {}).get("title", "your item")


async def _first_name(db, user_id: str) -> str:
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)}, {"full_name": 1})
    except Exception:
        user = None
    return ((user or {}).get("full_name") or "the other person").split(" ")[0]


# ---------------------------------------------------------------------------
# No response (FR-26)
# ---------------------------------------------------------------------------

async def _cancel_unanswered(db) -> None:
    now = datetime.now(timezone.utc)
    cutoff = (now - no_response_window()).isoformat()
    query = {"status": "open", "buyer_responded_at": None, "buyer_completed_at": None,
             "created_at": {"$lte": cutoff}}
    skipped = []
    while True:
        # Transactions made before buyer_responded_at existed: a buyer message still counts.
        candidate = await db.transactions.find_one({**query, "_id": {"$nin": skipped}})
        if candidate is None:
            return
        first = await db.messages.find_one({"transaction_id": str(candidate["_id"]),
                                            "sender_id": str(candidate["buyer_id"])},
                                           sort=[("created_at", 1)])
        if first:
            await db.transactions.update_one({"_id": candidate["_id"], "buyer_responded_at": None},
                                             {"$set": {"buyer_responded_at": first["created_at"]}})
            skipped.append(candidate["_id"])
            continue
        t = await db.transactions.find_one_and_update(
            {**query, "_id": candidate["_id"]},
            {"$set": {"status": "cancelled", "cancelled_reason": "no_response",
                      "cancelled_at": now.isoformat()}},
            return_document=True,
        )
        if t is None:
            skipped.append(candidate["_id"])  # answered or completed meanwhile
            continue
        await _apply_no_response(db, t, now)


async def _apply_no_response(db, t: dict, now: datetime) -> None:
    from app.helpers import create_notification, email_user
    from app.routers.feedback import SYSTEM_USER_ID, record_feedback

    buyer_id, seller_id = str(t["buyer_id"]), str(t["seller_id"])
    title = await _title(db, t["listing_id"])
    lock_until = now + no_response_lock()
    try:
        buyer = await db.users.find_one({"_id": ObjectId(buyer_id)}, {"suspended_until": 1})
        current = (buyer or {}).get("suspended_until")
        if not current or current < lock_until.isoformat():  # never shorten a longer lock
            await db.users.update_one({"_id": ObjectId(buyer_id)}, {"$set": {
                "suspended_until": lock_until.isoformat(),
                "suspension_reason": f"you didn't respond to the seller of '{title}' within 24 hours",
            }})
        await record_feedback(t, SYSTEM_USER_ID, "BidCa", buyer_id, "negative", NO_RESPONSE_LABEL,
                              "seller_to_buyer", system=True)
    except Exception as exc:
        logger.error("No-response penalty failed for transaction %s: %s", t["_id"], exc)

    hours = round(no_response_lock().total_seconds() / 3600, 1)
    hours_text = f"{hours:g} hour{'s' if hours != 1 else ''}"
    buyer_msg = (f"Your purchase of '{title}' was cancelled because you didn't message the seller within "
                 f"24 hours. Your account is locked for {hours_text} and a negative rating was added.")
    seller_msg = (f"The buyer of '{title}' didn't respond within 24 hours, so the sale was cancelled. "
                  f"You can relist the item from your dashboard.")
    await create_notification(buyer_id, "transaction_cancelled", buyer_msg, t["listing_id"],
                              extra={"transaction_id": str(t["_id"])})
    await create_notification(seller_id, "transaction_cancelled", seller_msg, t["listing_id"],
                              extra={"transaction_id": str(t["_id"])})
    await email_user(buyer_id, f"Purchase cancelled: {title}", buyer_msg)
    await email_user(seller_id, f"Sale cancelled: {title}", seller_msg, "/dashboard")
    logger.info("Transaction %s cancelled: no response from buyer %s", t["_id"], buyer_id)


# ---------------------------------------------------------------------------
# Reminders (FR-27)
# ---------------------------------------------------------------------------

async def _send_reminders(db) -> None:
    from app.helpers import email_user

    limit = reminder_max()
    while True:
        now = datetime.now(timezone.utc).isoformat()
        due = (datetime.now(timezone.utc) - reminder_interval()).isoformat()
        t = await db.transactions.find_one_and_update(
            {"status": "open",
             "$and": [
                 {"$or": [{"reminders_sent": {"$exists": False}}, {"reminders_sent": {"$lt": limit}}]},
                 {"$or": [{"last_reminder_at": {"$lte": due}},
                          {"last_reminder_at": None, "created_at": {"$lte": due}}]},
             ]},
            {"$set": {"last_reminder_at": now}, "$inc": {"reminders_sent": 1}},
            return_document=True,
        )
        if t is None:
            return
        tid = str(t["_id"])
        buyer_id, seller_id = str(t["buyer_id"]), str(t["seller_id"])
        title = await _title(db, t["listing_id"])
        for me, other in ((buyer_id, seller_id), (seller_id, buyer_id)):
            name = await _first_name(db, other)
            await email_user(me, f"Your transaction for {title} is still open",
                             f"Your transaction for {title} is still open. "
                             f"Please coordinate with {name} to complete it.",
                             f"/messages/{tid}")
        if t.get("reminders_sent", 0) >= limit:
            await notify_admins("transaction_stalled",
                                f"Transaction for '{title}' is still open after {limit} reminders.",
                                {"listing_id": t["listing_id"], "transaction_id": tid})


async def run_transaction_jobs(db) -> None:
    """One pass of both rules; the no-response check runs first so a cancelled sale gets no reminder."""
    try:
        await _cancel_unanswered(db)
    except Exception as exc:
        logger.error("No-response job error: %s", exc)
    try:
        await _send_reminders(db)
    except Exception as exc:
        logger.error("Reminder job error: %s", exc)
