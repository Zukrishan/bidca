"""
listing_rules.py — Phase 9e/9f listing rules shared by the listing routers.

- FR-05: what a complete listing needs, the category → subcategory rule, category fields,
  the Vehicles disclosure (Q008).
- FR-34: the monthly listing cap (Q015), counted from `listing_submissions`.
- FR-31: who may see a private (invite-only) listing (Q007).
- FR-29: the suspension schedule for cancelling a listing that has bids (Q010, Q012).
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.config import (
    free_period_months, free_period_start, listing_cap_per_month,
    seller_cancel_suspension_days, seller_cancel_window,
)
from app.constants import CATEGORIES, CATEGORY_FIELDS, VEHICLES_CATEGORY, get_bid_increment
from app.db import db
from app.helpers import calculate_positive_percentage

try:
    from zoneinfo import ZoneInfo
    PACIFIC = ZoneInfo("America/Vancouver")
except Exception:  # no tz database: fixed UTC-7 (tzdata 2025.3 has BC on UTC-7 all year from Nov 2026)
    PACIFIC = timezone(timedelta(hours=-7))

REQUIRED_FIELDS = ("title", "category", "description", "condition", "city")
DISCLOSURE_REQUIRED = ("accident_history", "mechanical_issues", "previous_owners", "safety_certificate",
                       "odometer_km", "liens")


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


# --- FR-05: listing content ----------------------------------------------------------------

def clean_category_fields(category: Optional[str], fields: Optional[dict]) -> dict:
    """Keep only the extra fields this category defines, with the right types; blanks are dropped."""
    spec = CATEGORY_FIELDS.get(category or "", {})
    out = {}
    for name, kind in spec.items():
        value = (fields or {}).get(name)
        if _blank(value):
            continue
        try:
            out[name] = int(value) if kind is int else str(value).strip()[:100]
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"{name.capitalize()} must be a whole number")
        if kind is int and out[name] < 0:
            raise HTTPException(status_code=422, detail=f"{name.capitalize()} must not be negative")
    return out


def check_category(category: Optional[str], subcategory: Optional[str]) -> None:
    """The category must exist; a subcategory must belong to it (FR-05)."""
    if _blank(category):
        if not _blank(subcategory):
            raise HTTPException(status_code=422, detail="Choose a category before a subcategory")
        return
    if category not in CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown category")
    if not _blank(subcategory) and subcategory not in CATEGORIES[category]:
        raise HTTPException(status_code=422, detail="Subcategory does not belong to this category")


def clean_disclosure(category: Optional[str], disclosure) -> Optional[dict]:
    """The vehicle disclosure is kept for Vehicles listings only."""
    if category != VEHICLES_CATEGORY or disclosure is None:
        return None
    data = disclosure if isinstance(disclosure, dict) else disclosure.model_dump()
    for text in ("accident_description", "mechanical_description", "safety_certificate_url"):
        if isinstance(data.get(text), str):
            data[text] = data[text].strip()[:2000] or None
    return data


def check_complete(doc: dict) -> None:
    """A listing submitted for approval needs every required field (FR-05, Q008). 422 lists what's missing."""
    missing = [f for f in REQUIRED_FIELDS if _blank(doc.get(f))]
    if doc.get("starting_bid") is None and doc.get("listing_type") != "fixed_price":
        missing.append("starting_bid")
    if doc.get("listing_type") == "fixed_price" and doc.get("buy_it_now_price") is None:
        missing.append("buy_it_now_price")
    if missing:
        raise HTTPException(status_code=422, detail=f"Required: {', '.join(missing)}")
    if doc.get("category") == VEHICLES_CATEGORY:
        d = doc.get("vehicle_disclosure") or {}
        gaps = [f for f in DISCLOSURE_REQUIRED if d.get(f) is None]
        if d.get("accident_history") and _blank(d.get("accident_description")):
            gaps.append("accident_description")
        if d.get("mechanical_issues") and _blank(d.get("mechanical_description")):
            gaps.append("mechanical_description")
        if gaps:
            raise HTTPException(status_code=422, detail=f"Vehicle disclosure required: {', '.join(gaps)}")


def check_prices(doc: dict) -> None:
    starting = doc.get("starting_bid")
    if starting is not None and starting < 0:
        raise HTTPException(status_code=422, detail="Starting bid must not be negative")
    if doc.get("reserve_price") and starting is not None and doc["reserve_price"] < starting:
        raise HTTPException(status_code=400, detail="Reserve price must be higher than starting bid")
    if doc.get("buy_it_now_price") and starting is not None and doc["buy_it_now_price"] <= starting:
        raise HTTPException(status_code=400, detail="Buy It Now price must be higher than starting bid")


def listing_content(data: dict) -> dict:
    """The seller-editable part of a listing doc, from AuctionCreate data (create or draft edit)."""
    listing_type = data.get("listing_type") or "auction"
    category = data.get("category") or None
    check_category(category, data.get("subcategory"))
    starting = data.get("starting_bid")
    if starting is None and listing_type == "fixed_price":
        starting = 0
    content = {
        "title": (data.get("title") or "").strip(),
        "category": category,
        "subcategory": data.get("subcategory") or None,
        "description": (data.get("description") or "").strip(),
        "city": data.get("city") or None,
        "province": data.get("province") or "British Columbia",
        "images": list(data.get("images") or [])[:10],
        "condition": data.get("condition") or "good",
        "listing_type": listing_type,
        "fixed_price_last": listing_type == "fixed_price",  # browse order (FR-07)
        "starting_bid": starting,
        "current_bid": starting,
        "reserve_price": data.get("reserve_price"),
        "reserve_met": False if data.get("reserve_price") else True,
        # A private listing is a pure auction: no Buy-now, no offers (FR-31)
        "buy_it_now_price": None if listing_type == "private" else data.get("buy_it_now_price"),
        # No negotiating once an auction is open (FR-28): offers are for fixed-price listings only
        "accepts_best_offer": bool(data.get("accepts_best_offer")) and listing_type == "fixed_price",
        "duration_days": data.get("duration_days") or 7,
        "bid_increment": get_bid_increment(starting or 0),
        "category_fields": clean_category_fields(category, data.get("category_fields")),
        "vehicle_disclosure": clean_disclosure(category, data.get("vehicle_disclosure")),
    }
    check_prices(content)
    return content


def seller_fields(user: dict) -> dict:
    return {
        "seller_id": user["_id"],
        "seller_name": user["full_name"],
        "seller_city": user["city"],
        "seller_verified": user.get("verification_badge", False),
        "seller_rating": user.get("seller_rating", 0),
        "seller_total_ratings": user.get("total_ratings", 0),
        "seller_positive_pct": calculate_positive_percentage(user),
    }


def timing_fields(duration_days: int, now: Optional[datetime] = None) -> dict:
    """Start/end times for a listing submitted now; a private listing's invite link ends with it."""
    now = now or datetime.now(timezone.utc)
    end = (now + timedelta(days=duration_days)).isoformat()
    return {"start_time": now.isoformat(), "end_time": end, "invite_expires_at": end}


# --- FR-34: monthly cap --------------------------------------------------------------------

def month_start(now: Optional[datetime] = None) -> datetime:
    """Start of the current calendar month in Pacific time, as a UTC datetime."""
    local = (now or datetime.now(timezone.utc)).astimezone(PACIFIC)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def next_month_start(now: Optional[datetime] = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(PACIFIC)
    year, month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    return local.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


async def listings_used_this_month(seller_id: str) -> int:
    """Submissions for approval this month (relists included); drafts never get here, rejected don't count."""
    return await db.listing_submissions.count_documents({
        "seller_id": seller_id,
        "submitted_at": {"$gte": month_start().isoformat()},
        "rejected": {"$ne": True},
    })


async def check_listing_cap(seller_id: str) -> None:
    cap = listing_cap_per_month()
    if await listings_used_this_month(seller_id) >= cap:
        local = next_month_start().astimezone(PACIFIC)
        resets = f"{local:%B} {local.day}"
        raise HTTPException(
            status_code=429,
            detail=f"You've reached the limit of {cap} listings this month. You can list again from {resets} (Pacific time).",
        )


async def record_submission(seller_id: str, listing_id: str) -> None:
    await db.listing_submissions.insert_one({
        "seller_id": seller_id, "listing_id": listing_id, "rejected": False,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    })


async def mark_submission_rejected(listing_id: str) -> None:
    """An admin rejected the listing: its latest submission stops counting toward the cap."""
    latest = await db.listing_submissions.find_one({"listing_id": listing_id}, sort=[("submitted_at", -1)])
    if latest:
        await db.listing_submissions.update_one({"_id": latest["_id"]}, {"$set": {"rejected": True}})


def _add_months(day, months: int):
    import calendar
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


async def listing_quota(seller_id: str) -> dict:
    cap = listing_cap_per_month()
    used = await listings_used_this_month(seller_id)
    start = free_period_start()
    free = None
    if start:
        end = _add_months(start, free_period_months())
        today = datetime.now(timezone.utc).astimezone(PACIFIC).date()
        free = {"start": start.isoformat(), "end": end.isoformat(), "active": start <= today < end}
    return {
        "cap": cap, "used": used, "remaining": max(0, cap - used),
        "resets_at": next_month_start().isoformat(), "free_period": free,
    }


# --- FR-31: private listings ---------------------------------------------------------------

def is_private(listing: dict) -> bool:
    return listing.get("listing_type") == "private"


def can_view_listing(listing: dict, user: Optional[dict]) -> bool:
    """Private listings exist only for their seller, invitees and admins (FR-31); others get a 404."""
    if not is_private(listing):
        return True
    if not user:
        return False
    uid = str(user["_id"])
    return (uid == str(listing.get("seller_id")) or user.get("role") == "admin"
            or uid in [str(i) for i in listing.get("invitees") or []])


def new_invite_token() -> str:
    return secrets.token_urlsafe(24)


async def find_user_by_identifier(identifier: str) -> Optional[dict]:
    """A BidCa account by user id, email or phone number."""
    ident = (identifier or "").strip()
    if not ident:
        return None
    try:
        user = await db.users.find_one({"_id": ObjectId(ident)})
        if user:
            return user
    except (InvalidId, TypeError):
        pass
    if "@" in ident:
        user = await db.users.find_one({"email": ident.lower()})
        return user or await db.users.find_one({"email": ident})
    digits = "".join(ch for ch in ident if ch.isdigit())
    if len(digits) >= 7:
        for candidate in {ident, digits, f"+{digits}", f"+1{digits}" if len(digits) == 10 else digits}:
            user = await db.users.find_one({"phone": candidate})
            if user:
                return user
    return None


async def resolve_invitees(identifiers, seller_id: str) -> list:
    """User ids for the given identifiers; 422 naming any that have no BidCa account."""
    ids, unknown = [], []
    for ident in identifiers or []:
        if _blank(ident):
            continue
        user = await find_user_by_identifier(ident)
        if not user:
            unknown.append(ident.strip())
            continue
        uid = str(user["_id"])
        if uid != seller_id and uid not in ids:
            ids.append(uid)
    if unknown:
        raise HTTPException(status_code=422, detail=f"No BidCa account for: {', '.join(unknown)}")
    return ids


def strip_private_fields(listing: dict, user: Optional[dict]) -> dict:
    """Only the seller (and admins) see the invite list and link."""
    is_owner = user and (str(listing.get("seller_id")) == str(user["_id"]) or user.get("role") == "admin")
    if not is_owner:
        for key in ("invitees", "invite_token", "invite_expires_at"):
            listing.pop(key, None)
    return listing


# --- FR-29: seller cancellation ------------------------------------------------------------

async def cancellation_penalty(seller_id: str) -> dict:
    """What cancelling one more listing with bids would cost this seller now (Q010)."""
    since = (datetime.now(timezone.utc) - seller_cancel_window()).isoformat()
    earlier = await db.seller_cancellations.count_documents(
        {"seller_id": seller_id, "with_bids": True, "created_at": {"$gte": since}})
    offence = earlier + 1
    schedule = seller_cancel_suspension_days()
    if offence <= len(schedule):
        return {"offence": offence, "suspension_days": schedule[offence - 1], "until_admin_review": False}
    return {"offence": offence, "suspension_days": None, "until_admin_review": True}


def penalty_text(penalty: dict) -> str:
    if penalty["until_admin_review"]:
        return "Your account will be suspended until an admin reviews it."
    days = penalty["suspension_days"]
    days_text = f"{days:g} day" + ("" if days == 1 else "s")
    return f"Your account will be suspended for {days_text}."


async def suspend_seller(seller_id: str, penalty: dict, title: str) -> dict:
    """Set suspended_until / suspension_reason (auth enforcement is Phase 9c). Returns the fields set."""
    reason = f"Cancelled the listing '{title}' while people were bidding (cancellation {penalty['offence']})"
    if penalty["until_admin_review"]:
        fields = {"suspended_until": None, "is_suspended": True, "suspension_reason": reason + " — until admin review"}
    else:
        until = datetime.now(timezone.utc) + timedelta(days=penalty["suspension_days"])
        user = await db.users.find_one({"_id": ObjectId(seller_id)}, {"suspended_until": 1})
        current = (user or {}).get("suspended_until")
        if current and current > until.isoformat():
            until_iso = current  # never shorten a longer suspension
        else:
            until_iso = until.isoformat()
        fields = {"suspended_until": until_iso, "suspension_reason": reason}
    await db.users.update_one({"_id": ObjectId(seller_id)}, {"$set": fields})
    return fields
