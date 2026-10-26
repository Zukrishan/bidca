"""
listing_manage.py — the seller's side of a listing after it is created (Phase 9e/9f):
drafts (FR-05), cancelling (FR-29), the monthly cap (FR-34) and private-listing invites (FR-31).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db import db
from app.helpers import create_notification, email_user, parse_object_id
from app.listing_rules import (
    cancellation_penalty, check_complete, check_listing_cap, find_user_by_identifier, is_private,
    listing_content, listing_quota, new_invite_token, penalty_text, record_submission, resolve_invitees,
    suspend_seller, timing_fields,
)
from app.models import AuctionCreate, CancelListingRequest, InviteCreate
from app.security import get_current_user, require_verified_email

router = APIRouter()


def _out(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    doc["seller_id"] = str(doc["seller_id"])
    doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
    return doc


async def _own_listing(listing_id: str, user: dict) -> dict:
    """The caller's own listing; anyone else's is a 404 (no hint it exists)."""
    oid = parse_object_id(listing_id, "Listing not found")
    listing = await db.listings.find_one({"_id": oid})
    if not listing or str(listing["seller_id"]) != user["_id"]:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/users/me/listing-quota")
async def get_listing_quota(user: dict = Depends(get_current_user)):
    """How many of this month's listings (FR-34) the seller has used."""
    return await listing_quota(user["_id"])


# --- Drafts (FR-05) ------------------------------------------------------------------------

@router.put("/listings/{listing_id}")
async def update_draft(listing_id: str, update: AuctionCreate, user: dict = Depends(require_verified_email)):
    """Edit a draft. Only fields sent are changed; a listing that was submitted can't be edited."""
    listing = await _own_listing(listing_id, user)
    if listing["status"] != "draft":
        raise HTTPException(status_code=400, detail="Only drafts can be edited")
    current = {k: listing.get(k) for k in AuctionCreate.model_fields if k in listing and k != "invitees"}
    changes = update.model_dump(exclude_unset=True)
    changes.pop("draft", None)
    merged = {**current, **changes}
    content = listing_content(merged)
    unset = {}
    if content["listing_type"] == "private":
        if "invitees" in changes:
            content["invitees"] = await resolve_invitees(update.invitees, user["_id"])
        elif not listing.get("invitees"):
            content["invitees"] = []
        if not listing.get("invite_token"):
            content["invite_token"] = new_invite_token()
    else:
        unset = {"invitees": "", "invite_token": "", "invite_expires_at": ""}
    op = {"$set": {**content, "updated_at": datetime.now(timezone.utc).isoformat()}}
    if unset:
        op["$unset"] = unset
    await db.listings.update_one({"_id": listing["_id"], "status": "draft"}, op)
    return _out(await db.listings.find_one({"_id": listing["_id"]}))


@router.post("/listings/{listing_id}/submit")
async def submit_draft(listing_id: str, user: dict = Depends(require_verified_email)):
    """Send a draft for admin approval: it must be complete and fit this month's cap (FR-34)."""
    listing = await _own_listing(listing_id, user)
    if listing["status"] != "draft":
        raise HTTPException(status_code=400, detail="Only drafts can be submitted")
    check_complete(listing)
    await check_listing_cap(user["_id"])
    fields = timing_fields(listing.get("duration_days") or 7)
    if not is_private(listing):
        fields.pop("invite_expires_at")
    fields["status"] = "pending"
    fields["submitted_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.listings.update_one({"_id": listing["_id"], "status": "draft"}, {"$set": fields})
    if result.modified_count == 0:
        raise HTTPException(status_code=409, detail="This draft was already submitted")
    await record_submission(user["_id"], listing_id)
    return _out(await db.listings.find_one({"_id": listing["_id"]}))


# --- Seller cancel (FR-29, Q012) -----------------------------------------------------------

async def _cancel_outcome(listing: dict) -> dict:
    status = listing["status"]
    if status in ("draft", "pending"):
        return {"outcome": "withdraw", "penalty": None,
                "message": "This listing hasn't gone live. Withdrawing it has no penalty."}
    if status != "active":
        return {"outcome": "not_allowed", "penalty": None, "message": "This listing can no longer be cancelled."}
    if not listing.get("bid_count"):
        return {"outcome": "cancel", "penalty": None, "message": "No one has bid yet. Cancelling has no penalty."}
    penalty = await cancellation_penalty(str(listing["seller_id"]))
    n = listing["bid_count"]
    return {"outcome": "cancel_with_penalty", "penalty": penalty,
            "message": f"This listing has {n} bid{'' if n == 1 else 's'}. Every bidder will be told it was "
                       f"cancelled. {penalty_text(penalty)}"}


@router.get("/listings/{listing_id}/cancel-preview")
async def cancel_preview(listing_id: str, user: dict = Depends(get_current_user)):
    """What cancelling would do now — shown in the confirmation step before POST .../cancel."""
    listing = await _own_listing(listing_id, user)
    return {"status": listing["status"], "bid_count": listing.get("bid_count", 0), **await _cancel_outcome(listing)}


@router.post("/listings/{listing_id}/cancel")
async def cancel_listing(listing_id: str, body: CancelListingRequest = None, user: dict = Depends(get_current_user)):
    """Withdraw a draft/pending listing, or cancel an active one. With bids, `confirm_penalty` must be
    true: bidders are notified and the seller is suspended per the schedule (Q010)."""
    body = body or CancelListingRequest()
    listing = await _own_listing(listing_id, user)
    now = datetime.now(timezone.utc).isoformat()
    cancel_set = {"status": "cancelled", "cancelled_at": now}

    if listing["status"] in ("draft", "pending"):
        before = await db.listings.find_one_and_update(
            {"_id": listing["_id"], "status": {"$in": ["draft", "pending"]}},
            {"$set": {**cancel_set, "cancelled_from": listing["status"]}})
        if before:
            return {"status": "cancelled", "outcome": "withdraw", "penalty": None, "suspension": None}
        listing = await db.listings.find_one({"_id": listing["_id"]})

    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This listing can no longer be cancelled")

    # No bids: cancel only while it still has none (a bid may land between preview and confirm)
    before = await db.listings.find_one_and_update(
        {"_id": listing["_id"], "status": "active", "bid_count": {"$in": [0, None]}},
        {"$set": {**cancel_set, "cancelled_from": "active"}})
    if before:
        await _close_side_effects(listing_id)
        await _record_cancellation(listing, with_bids=False, penalty=None)
        return {"status": "cancelled", "outcome": "cancel", "penalty": None, "suspension": None}

    if not body.confirm_penalty:
        preview = await _cancel_outcome(await db.listings.find_one({"_id": listing["_id"]}))
        raise HTTPException(status_code=409, detail=preview["message"])

    before = await db.listings.find_one_and_update(
        {"_id": listing["_id"], "status": "active"},
        {"$set": {**cancel_set, "cancelled_from": "active", "cancelled_with_bids": True}})
    if not before:
        raise HTTPException(status_code=400, detail="This listing can no longer be cancelled")
    penalty = await cancellation_penalty(user["_id"])
    await _record_cancellation(before, with_bids=True, penalty=penalty)
    suspension = await suspend_seller(user["_id"], penalty, before.get("title", ""))
    await _close_side_effects(listing_id)
    await _notify_bidders(listing_id, before.get("title", ""))
    return {"status": "cancelled", "outcome": "cancel_with_penalty", "penalty": penalty, "suspension": suspension}


async def _record_cancellation(listing: dict, with_bids: bool, penalty) -> None:
    await db.seller_cancellations.insert_one({
        "seller_id": str(listing["seller_id"]), "listing_id": str(listing["_id"]),
        "listing_title": listing.get("title"), "bid_count": listing.get("bid_count", 0),
        "with_bids": with_bids, "penalty": penalty, "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def _close_side_effects(listing_id: str) -> None:
    """Nothing scheduled on a cancelled listing may still fire."""
    await db.sniper_bids.update_many({"listing_id": listing_id, "status": "pending"}, {"$set": {"status": "cancelled"}})
    await db.offers.update_many({"listing_id": listing_id, "status": {"$in": ["pending", "countered"]}},
                                {"$set": {"status": "declined"}})


async def _notify_bidders(listing_id: str, title: str) -> None:
    message = f"The seller cancelled '{title}'. Your bid no longer stands."
    for bidder_id in await db.bids.distinct("bidder_id", {"listing_id": listing_id}):
        if bidder_id:
            await create_notification(str(bidder_id), "listing_cancelled", message, listing_id)
            await email_user(str(bidder_id), f"Listing cancelled: {title}", message)


# --- Private listing invites (FR-31, Q007) -------------------------------------------------

async def _own_private(listing_id: str, user: dict) -> dict:
    listing = await _own_listing(listing_id, user)
    if not is_private(listing):
        raise HTTPException(status_code=400, detail="Only private listings have invites")
    return listing


async def _invite_view(listing: dict) -> dict:
    people = []
    for uid in listing.get("invitees") or []:
        try:
            u = await db.users.find_one({"_id": parse_object_id(uid)}, {"full_name": 1, "email": 1})
        except HTTPException:
            u = None
        people.append({"user_id": uid, "full_name": (u or {}).get("full_name"), "email": (u or {}).get("email")})
    return {"invitees": people, "invite_token": listing.get("invite_token"),
            "invite_expires_at": listing.get("invite_expires_at")}


@router.get("/listings/{listing_id}/invites")
async def list_invites(listing_id: str, user: dict = Depends(get_current_user)):
    return await _invite_view(await _own_private(listing_id, user))


@router.post("/listings/{listing_id}/invites", status_code=201)
async def add_invite(listing_id: str, invite: InviteCreate, user: dict = Depends(get_current_user)):
    """Invite a registered BidCa user by user id, email or phone number."""
    listing = await _own_private(listing_id, user)
    if listing["status"] not in ("draft", "pending", "active"):
        raise HTTPException(status_code=400, detail="This listing has ended")
    invitee = await find_user_by_identifier(invite.identifier)
    if not invitee:
        raise HTTPException(status_code=404, detail="No BidCa account matches that email, phone or id")
    uid = str(invitee["_id"])
    if uid == user["_id"]:
        raise HTTPException(status_code=400, detail="You can't invite yourself")
    await db.listings.update_one({"_id": listing["_id"]}, {"$addToSet": {"invitees": uid}})
    if listing["status"] == "active":
        await create_notification(uid, "private_invite",
                                  f"{user['full_name']} invited you to a private listing: '{listing.get('title')}'",
                                  listing_id)
    return await _invite_view(await db.listings.find_one({"_id": listing["_id"]}))


@router.delete("/listings/{listing_id}/invites/{user_id}")
async def remove_invite(listing_id: str, user_id: str, user: dict = Depends(get_current_user)):
    listing = await _own_private(listing_id, user)
    await db.listings.update_one({"_id": listing["_id"]}, {"$pull": {"invitees": user_id}})
    return await _invite_view(await db.listings.find_one({"_id": listing["_id"]}))


@router.post("/listings/{listing_id}/invite-link")
async def reset_invite_link(listing_id: str, user: dict = Depends(get_current_user)):
    """A new invite link; the old one stops working. People who already joined stay invited."""
    listing = await _own_private(listing_id, user)
    await db.listings.update_one({"_id": listing["_id"]}, {"$set": {"invite_token": new_invite_token()}})
    return await _invite_view(await db.listings.find_one({"_id": listing["_id"]}))


@router.post("/invites/{token}/accept")
async def accept_invite(token: str, user: dict = Depends(get_current_user)):
    """Join a private listing through its invite link. Needs an account; the link ends with the listing."""
    listing = await db.listings.find_one({"invite_token": token, "listing_type": "private"}) if token else None
    if not listing:
        raise HTTPException(status_code=404, detail="This invite link is not valid")
    expires = listing.get("invite_expires_at")
    ended = listing["status"] not in ("draft", "pending", "active") or (
        expires and expires <= datetime.now(timezone.utc).isoformat())
    if ended:
        raise HTTPException(status_code=410, detail="This invite link has expired")
    if str(listing["seller_id"]) != user["_id"]:
        await db.listings.update_one({"_id": listing["_id"]}, {"$addToSet": {"invitees": user["_id"]}})
    return {"listing_id": str(listing["_id"]), "title": listing.get("title")}
