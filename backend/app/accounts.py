"""
accounts.py — account rules shared by auth, profile and settings (FR-01, FR-02, FR-22; Q009, Q013).

- Public names: the display name (default first name + last initial); `full_name` stays private.
- Trust: the phone-verified badge shows only after 2 completed transactions; tiers from completed
  counts + rating ratio. Private (invite-only) listings count toward neither (FR-31).
- Sessions: `last_active_at` drives the inactivity logout.
- Delete account: anonymise and soft-delete; transactions, bids and ratings stay intact.
"""

import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import HTTPException

from app.config import inactivity_logout, is_production
from app.db import db

logger = logging.getLogger(__name__)

DELETED_NAME = "Deleted user"
EXCHANGE_METHODS = ("cash_on_pickup", "e_transfer", "meet_public")

# Q013 provisional defaults
BADGE_MIN_COMPLETED = 2
TIER_MIN_COMPLETED = 10
TIER_MIN_POSITIVE_RATIO = 0.95

# Write `last_active_at` at most this often (every authenticated request would be a write otherwise)
ACTIVITY_WRITE_EVERY = timedelta(seconds=60)

# Transaction states (built by 9c) that still need both parties
UNFINISHED_TRANSACTION_STATUSES = ["open", "disputed"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _oid(user_id) -> ObjectId:
    return user_id if isinstance(user_id, ObjectId) else ObjectId(str(user_id))


# --- names --------------------------------------------------------------------------------

def default_display_name(full_name: Optional[str]) -> str:
    """'Vera Fyodorova' → 'Vera F.'; a single name stays as it is."""
    parts = (full_name or "").split()
    if not parts:
        return "Member"
    if len(parts) == 1:
        return parts[0][:30]
    return f"{parts[0][:27]} {parts[-1][0].upper()}."


def validate_display_name(value: str) -> str:
    name = " ".join((value or "").split())
    if not 2 <= len(name) <= 30:
        raise HTTPException(status_code=400, detail="Display name must be 2 to 30 characters")
    if "@" in name:
        raise HTTPException(status_code=400, detail="Display name can't contain an email address")
    if name.lower() == DELETED_NAME.lower():
        raise HTTPException(status_code=400, detail="Choose a different display name")
    return name


def validate_avatar_url(value: str) -> str:
    """Profile pictures come from our Cloudinary uploads only (no arbitrary third-party images)."""
    parsed = urlparse(value or "")
    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
        raise HTTPException(status_code=400, detail="Upload your profile picture with the photo picker")
    return value


async def phone_taken(phone: str, exclude_user_id: Optional[str] = None) -> bool:
    """True when another (not deleted) account has already verified this number."""
    query = {"phone": phone, "phone_verified": True, "deleted_at": None}
    if exclude_user_id:
        query["_id"] = {"$ne": _oid(exclude_user_id)}
    return await db.users.find_one(query, {"_id": 1}) is not None


def public_name(user: Optional[dict]) -> str:
    """The name other people see for `user`."""
    if not user:
        return DELETED_NAME
    if user.get("deleted_at"):
        return DELETED_NAME
    return user.get("display_name") or default_display_name(user.get("full_name"))


# --- trust: completed deals, badge, tiers -------------------------------------------------

async def _private_listing_ids() -> list:
    return [str(i) for i in await db.listings.distinct("_id", {"listing_type": "private"})]


async def completed_counts(user_id: str) -> tuple:
    """(completed as buyer, completed as seller), not counting private listings."""
    excluded = await _private_listing_ids()
    base = {"status": "completed", "listing_type": {"$ne": "private"}, "listing_id": {"$nin": excluded}}
    as_buyer = await db.transactions.count_documents({**base, "buyer_id": user_id})
    as_seller = await db.transactions.count_documents({**base, "seller_id": user_id})
    return as_buyer, as_seller


async def rating_counts(user_id: str) -> dict:
    """Ratings received: totals by colour, and per role for the tiers (neutral counts as neither)."""
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    roles = {"seller": {"positive": 0, "negative": 0}, "buyer": {"positive": 0, "negative": 0}}
    async for f in db.feedback.find({"to_user_id": user_id}, {"rating": 1, "feedback_type": 1}):
        rating = f.get("rating")
        if rating not in counts:
            continue
        counts[rating] += 1
        role = "seller" if f.get("feedback_type") == "buyer_to_seller" else "buyer"
        if rating in roles[role]:
            roles[role][rating] += 1
    return {**counts, "by_role": roles}


def _good_ratio(role_counts: dict) -> Optional[float]:
    graded = role_counts["positive"] + role_counts["negative"]
    return role_counts["positive"] / graded if graded else None


def tiers_for(as_buyer: int, as_seller: int, ratings: dict) -> list:
    tiers = []
    seller_ratio = _good_ratio(ratings["by_role"]["seller"])
    buyer_ratio = _good_ratio(ratings["by_role"]["buyer"])
    if as_seller >= TIER_MIN_COMPLETED and seller_ratio is not None and seller_ratio >= TIER_MIN_POSITIVE_RATIO:
        tiers.append("top_seller")
    if as_buyer >= TIER_MIN_COMPLETED and buyer_ratio is not None and buyer_ratio >= TIER_MIN_POSITIVE_RATIO:
        tiers.append("power_bidder")
    return tiers


def badge_for(user: dict, as_buyer: int, as_seller: int) -> bool:
    """Phone verified ✓, shown only after two successful transactions (FR-22). The only badge (Q009)."""
    return bool(user.get("phone_verified")) and (as_buyer + as_seller) >= BADGE_MIN_COMPLETED


async def verified_badge(user: dict) -> bool:
    as_buyer, as_seller = await completed_counts(str(user["_id"]))
    return badge_for(user, as_buyer, as_seller)


async def refresh_public_snapshots(user_id: str) -> None:
    """Re-copy the user's public name and badge onto the documents that store a snapshot of them.

    Listings store `seller_name`/`seller_verified` (and `highest_bidder_name`), bids `bidder_name`,
    feedback `from_user_name`, offers `buyer_name`. Call after a display-name change, phone
    verification, a completed transaction, or account deletion.
    """
    user = await db.users.find_one({"_id": _oid(user_id)})
    if not user:
        return
    name = public_name(user)
    badge = False if user.get("deleted_at") else await verified_badge(user)
    ids = [user_id, _oid(user_id)]  # seller_id is stored as a string, but be lenient
    await db.listings.update_many({"seller_id": {"$in": ids}},
                                  {"$set": {"seller_name": name, "seller_verified": badge}})
    await db.listings.update_many({"highest_bidder_id": {"$in": ids}}, {"$set": {"highest_bidder_name": name}})
    await db.bids.update_many({"bidder_id": {"$in": ids}}, {"$set": {"bidder_name": name}})
    await db.feedback.update_many({"from_user_id": {"$in": ids}}, {"$set": {"from_user_name": name}})
    await db.offers.update_many({"buyer_id": {"$in": ids}}, {"$set": {"buyer_name": name}})


# --- sessions -----------------------------------------------------------------------------

def _parse_time(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def mark_active(user_id) -> None:
    await db.users.update_one({"_id": _oid(user_id)}, {"$set": {"last_active_at": _now().isoformat()}})


async def check_session_activity(user: dict) -> None:
    """Refuse a deleted account or a session idle longer than INACTIVITY_LOGOUT_MINUTES; else record activity.

    A user with no `last_active_at` yet (accounts from before 9d) counts as active now.
    """
    if user.get("deleted_at"):
        raise HTTPException(status_code=401, detail="Account deleted")
    now = _now()
    last = _parse_time(user.get("last_active_at"))
    if last and now - last > inactivity_logout():
        raise HTTPException(status_code=401, detail="Signed out after inactivity")
    if not last or now - last >= ACTIVITY_WRITE_EVERY:
        await mark_active(user["_id"])


# --- startup ------------------------------------------------------------------------------

def check_production_settings() -> None:
    """Production refuses to start without phone verification and CAPTCHA keys (Q011)."""
    if not is_production():
        return
    from app.phone import TWILIO_ENV
    required = (*TWILIO_ENV, "TURNSTILE_SECRET_KEY", "TURNSTILE_SITE_KEY")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"ENV=production but {', '.join(missing)} not set (phone verification and CAPTCHA are required)")


async def accounts_startup() -> None:
    check_production_settings()
    try:
        # One account per *verified* phone; unverified duplicates may exist until one of them verifies
        await db.users.create_index("phone", unique=True, name="phone_verified_unique",
                                    partialFilterExpression={"phone_verified": True})
    except Exception as exc:  # e.g. existing duplicates — the app-level check still applies
        logger.warning("phone index not created: %s", exc)
    # Users from before 9d get a display name, and their stored names/badges are refreshed so
    # full names stop showing publicly and ID-verification badges stop showing (Q009).
    async for u in db.users.find({"display_name": {"$exists": False}}, {"full_name": 1, "deleted_at": 1}):
        await db.users.update_one({"_id": u["_id"]}, {"$set": {"display_name": default_display_name(u.get("full_name"))}})
        await refresh_public_snapshots(str(u["_id"]))


# --- delete account -----------------------------------------------------------------------

async def delete_account(user: dict) -> None:
    """Anonymise and soft-delete. Refused while the user still owes someone a finished deal."""
    uid = user["_id"]
    if await db.transactions.count_documents({"$or": [{"buyer_id": uid}, {"seller_id": uid}],
                                              "status": {"$in": UNFINISHED_TRANSACTION_STATUSES}}):
        raise HTTPException(status_code=409, detail="Finish or resolve your open transactions before deleting your account")
    if await db.listings.count_documents({"seller_id": uid, "status": "active", "bid_count": {"$gt": 0}}):
        raise HTTPException(status_code=409, detail="You have active listings with bids; wait for them to end before deleting your account")
    if await db.listings.count_documents({"highest_bidder_id": uid, "status": "active"}):
        raise HTTPException(status_code=409, detail="You are the highest bidder on an active auction; wait for it to end before deleting your account")

    now = _now().isoformat()
    # Listings nobody has bid on are withdrawn; ended/sold ones stay for the other party's records
    await db.listings.update_many({"seller_id": uid, "status": {"$in": ["active", "pending", "draft"]}},
                                  {"$set": {"status": "cancelled", "cancelled_at": now, "cancel_reason": "account_deleted"}})
    await db.sniper_bids.update_many({"user_id": uid, "status": "pending"}, {"$set": {"status": "cancelled"}})
    await db.offers.update_many({"buyer_id": uid, "status": "pending"}, {"$set": {"status": "withdrawn"}})
    for coll in (db.watchlist, db.saved_searches, db.notifications, db.email_verifications,
                 db.password_reset_tokens):
        await coll.delete_many({"user_id": uid})
    await db.login_attempts.delete_many({"identifier": user.get("email")})

    await db.users.update_one({"_id": _oid(uid)}, {
        "$set": {
            "deleted_at": now,
            "email": f"deleted+{uid}@deleted.bidca.invalid",
            "password_hash": "!deleted:" + secrets.token_hex(16),  # never matches a bcrypt check
            "full_name": DELETED_NAME,
            "display_name": DELETED_NAME,
            "phone": None,
            "phone_verified": False,
            "avatar_url": None,
            "postal_code": None,
            "exchange_methods": [],
        },
    })
    await refresh_public_snapshots(uid)
