"""
transactions.py — FR-23/FR-24: the deal after a win, and the user page lists built on it.

A transaction is `open` until both sides press Complete (`completed`). Either side may open a
dispute (`disputed`, proof required), which disables Complete until the opener cancels it or an
admin resolves it. The no-response job (app/transaction_jobs.py) can move it to `cancelled`.

BidCa never touches money: there is no payment, refund or escrow anywhere here. Admin dispute
outcomes are moderation only (warn, suspend, ban, close).

Only the buyer and seller see a transaction; anyone else gets 404, as for its messages.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional
from urllib.parse import urlparse

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import db
from app.helpers import create_notification, email_user, parse_object_id
from app.security import get_current_user, require_admin
from app.transaction_jobs import notify_admins

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_REASON = 2000
MAX_PROOFS = 10
MAX_NOTE = 2000


class DisputeCreate(BaseModel):
    reason: str
    proof_urls: List[str] = []


class DisputeResolve(BaseModel):
    note: str
    outcome: Literal["warn", "suspend", "ban", "close"]
    target_user_id: Optional[str] = None  # buyer or seller; required unless outcome is "close"
    suspend_hours: Optional[float] = None  # outcome "suspend"; default 72
    reopen: bool = False                   # True: back to `open` so they can still complete; else `cancelled`


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _role(t: dict, user: dict) -> Optional[str]:
    if user["_id"] == str(t.get("buyer_id")):
        return "buyer"
    if user["_id"] == str(t.get("seller_id")):
        return "seller"
    return None


async def _participant_transaction(transaction_id: str, user: dict) -> dict:
    t = await db.transactions.find_one({"_id": parse_object_id(transaction_id, "Transaction not found")})
    if not t or _role(t, user) is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return t


async def _docs_by_id(collection, ids) -> dict:
    oids = []
    for i in set(ids):
        try:
            oids.append(ObjectId(i))
        except (InvalidId, TypeError):
            pass
    return {str(d["_id"]): d async for d in collection.find({"_id": {"$in": oids}})}


def _listing_summary(listing_id: str, listing: dict) -> dict:
    images = listing.get("images") or []
    return {"id": listing_id, "title": listing.get("title", "Removed listing"),
            "image": images[0] if images else None, "listing_type": listing.get("listing_type")}


def _person(user_id: str, u: dict) -> dict:
    return {"id": user_id, "full_name": u.get("full_name", "Former user"), "city": u.get("city")}


def _brief(t: dict, uid: str, listings: dict, users: dict) -> dict:
    """List row for the user page tabs."""
    role = "buyer" if uid == str(t["buyer_id"]) else "seller"
    other_id = str(t["seller_id"]) if role == "buyer" else str(t["buyer_id"])
    return {
        "_id": str(t["_id"]),
        "listing": _listing_summary(t["listing_id"], listings.get(t["listing_id"], {})),
        "amount": t.get("amount"),
        "type": t.get("type"),
        "status": t.get("status"),
        "role": role,
        "other_party": _person(other_id, users.get(other_id, {})),
        "created_at": t.get("created_at"),
        "completed_at": t.get("completed_at"),
        "my_completed": bool(t.get(f"{role}_completed_at")),
    }


async def _detail(t: dict, user: dict) -> dict:
    """GET /transactions/{id} body: order summary plus everything the transaction page shows."""
    role = _role(t, user)
    tid = str(t["_id"])
    buyer_id, seller_id = str(t["buyer_id"]), str(t["seller_id"])
    users = await _docs_by_id(db.users, [buyer_id, seller_id])
    listings = await _docs_by_id(db.listings, [t["listing_id"]])
    seller = users.get(seller_id, {})
    other = "seller" if role == "buyer" else "buyer"
    mine = await db.feedback.find_one({"transaction_id": tid, "from_user_id": user["_id"]})
    dispute = t.get("dispute")
    return {
        "_id": tid,
        "status": t.get("status"),
        "type": t.get("type"),
        "amount": t.get("amount"),
        "created_at": t.get("created_at"),
        "role": role,
        "listing": _listing_summary(t["listing_id"], listings.get(t["listing_id"], {})),
        "buyer": _person(buyer_id, users.get(buyer_id, {})),
        "seller": _person(seller_id, seller),
        # Chosen on the seller's profile (FR-22, owned by profile work); empty until they pick
        "exchange_methods": seller.get("exchange_methods") or [],
        "buyer_completed_at": t.get("buyer_completed_at"),
        "seller_completed_at": t.get("seller_completed_at"),
        "completed_at": t.get("completed_at"),
        "my_completed": bool(t.get(f"{role}_completed_at")),
        "other_completed": bool(t.get(f"{other}_completed_at")),
        "dispute": ({**dispute, "opened_by_me": dispute.get("opened_by") == user["_id"]} if dispute else None),
        "cancelled_reason": t.get("cancelled_reason"),
        "my_feedback": ({"rating": mine["rating"], "comment": mine.get("comment", "")} if mine else None),
        "can_rate": t.get("status") == "completed" and mine is None,
    }


def _valid_proof_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


# ---------------------------------------------------------------------------
# Transaction page (FR-24)
# ---------------------------------------------------------------------------

@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    return await _detail(t, user)


@router.post("/transactions/{transaction_id}/complete")
async def complete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    role = _role(t, user)
    status = t.get("status")
    if status == "disputed":
        raise HTTPException(status_code=409, detail="Complete is disabled while the dispute is open")
    if status == "cancelled":
        raise HTTPException(status_code=409, detail="This transaction was cancelled")
    if status == "completed":
        return await _detail(t, user)

    now = _now()
    field = f"{role}_completed_at"
    pressed = await db.transactions.update_one(
        {"_id": t["_id"], "status": "open", field: None}, {"$set": {field: now}})
    # Only when both have pressed it does it complete — atomically, so it happens once (FR-24)
    done = await db.transactions.find_one_and_update(
        {"_id": t["_id"], "status": "open", "buyer_completed_at": {"$ne": None},
         "seller_completed_at": {"$ne": None}},
        {"$set": {"status": "completed", "completed_at": now}},
        return_document=True,
    )
    fresh = await db.transactions.find_one({"_id": t["_id"]})
    if fresh.get("status") == "disputed":  # a dispute won the race
        raise HTTPException(status_code=409, detail="Complete is disabled while the dispute is open")

    title = (await _docs_by_id(db.listings, [t["listing_id"]])).get(t["listing_id"], {}).get("title", "your item")
    other_id = str(t["seller_id"]) if role == "buyer" else str(t["buyer_id"])
    extra = {"transaction_id": str(t["_id"])}
    if done is not None:
        # Ask both to rate straight away (FR-25)
        msg = f"Your transaction for '{title}' is complete. Please rate the other person."
        for uid in (str(t["buyer_id"]), str(t["seller_id"])):
            await create_notification(uid, "transaction_completed", msg, t["listing_id"], extra=extra)
            await email_user(uid, f"Transaction complete: {title}", msg, f"/messages/{t['_id']}")
    elif pressed.modified_count:
        first = (user.get("full_name") or "The other person").split(" ")[0]
        msg = f"{first} marked the transaction for '{title}' as complete. Press Complete when you're happy too."
        await create_notification(other_id, "transaction_complete_pressed", msg, t["listing_id"], extra=extra)
    return await _detail(fresh, user)


@router.post("/transactions/{transaction_id}/dispute")
async def open_dispute(transaction_id: str, payload: DisputeCreate, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    reason = payload.reason.strip()
    proofs = [u.strip() for u in payload.proof_urls if u and u.strip()]
    if not reason or len(reason) > MAX_REASON:
        raise HTTPException(status_code=422, detail=f"Describe the problem (1-{MAX_REASON} characters)")
    if not proofs:
        raise HTTPException(status_code=422, detail="Attach at least one proof (screenshot or photo)")
    if len(proofs) > MAX_PROOFS or not all(_valid_proof_url(u) for u in proofs):
        raise HTTPException(status_code=422, detail=f"Proof must be 1-{MAX_PROOFS} uploaded files")
    if t.get("status") != "open":
        raise HTTPException(status_code=409, detail="Only an open transaction can be disputed")

    dispute = {"opened_by": user["_id"], "reason": reason, "proof_urls": proofs, "opened_at": _now(),
               "resolved_at": None, "resolution": None}
    updated = await db.transactions.find_one_and_update(
        {"_id": t["_id"], "status": "open"},
        {"$set": {"status": "disputed", "dispute": dispute}},
        return_document=True,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="Only an open transaction can be disputed")

    title = (await _docs_by_id(db.listings, [t["listing_id"]])).get(t["listing_id"], {}).get("title", "your item")
    other_id = str(t["seller_id"]) if _role(t, user) == "buyer" else str(t["buyer_id"])
    extra = {"transaction_id": str(t["_id"])}
    msg = f"A dispute was opened on the transaction for '{title}'. Our team will review the proof from both sides."
    await create_notification(other_id, "transaction_disputed", msg, t["listing_id"], extra=extra)
    await email_user(other_id, f"Dispute opened: {title}", msg, f"/messages/{t['_id']}")
    await notify_admins("dispute_opened", f"New dispute on '{title}'.", {"listing_id": t["listing_id"], **extra})
    return await _detail(updated, user)


@router.post("/transactions/{transaction_id}/cancel-dispute")
async def cancel_dispute(transaction_id: str, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    dispute = t.get("dispute") or {}
    if t.get("status") != "disputed":
        raise HTTPException(status_code=409, detail="There is no open dispute")
    if dispute.get("opened_by") != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the person who opened the dispute can cancel it")

    now = _now()
    updated = await db.transactions.find_one_and_update(
        {"_id": t["_id"], "status": "disputed", "dispute.opened_by": user["_id"]},
        {"$set": {"status": "open", "dispute.resolved_at": now,
                  "dispute.resolution": {"outcome": "withdrawn", "note": "Cancelled by the person who opened it",
                                         "resolved_by": user["_id"]}}},
        return_document=True,
    )
    if updated is None:
        raise HTTPException(status_code=409, detail="There is no open dispute")

    title = (await _docs_by_id(db.listings, [t["listing_id"]])).get(t["listing_id"], {}).get("title", "your item")
    other_id = str(t["seller_id"]) if _role(t, user) == "buyer" else str(t["buyer_id"])
    await create_notification(other_id, "dispute_cancelled",
                              f"The dispute on '{title}' was cancelled. You can complete the transaction again.",
                              t["listing_id"], extra={"transaction_id": str(t["_id"])})
    return await _detail(updated, user)


# ---------------------------------------------------------------------------
# Admin dispute queue (FR-24) — moderation only, never money
# ---------------------------------------------------------------------------

@router.get("/admin/disputes")
async def admin_list_disputes(status: Literal["open", "resolved", "all"] = "open",
                              admin: dict = Depends(require_admin)):
    if status == "open":
        query = {"status": "disputed"}
    elif status == "resolved":
        query = {"dispute.resolved_at": {"$ne": None}}
    else:
        query = {"dispute": {"$ne": None}}
    txs = [t async for t in db.transactions.find(query).sort("dispute.opened_at", -1).limit(200)]
    users = await _docs_by_id(db.users, [str(t[k]) for t in txs for k in ("buyer_id", "seller_id")])
    listings = await _docs_by_id(db.listings, [t["listing_id"] for t in txs])
    out = []
    for t in txs:
        b, s = str(t["buyer_id"]), str(t["seller_id"])
        out.append({
            "_id": str(t["_id"]),
            "status": t.get("status"),
            "amount": t.get("amount"),
            "created_at": t.get("created_at"),
            "listing": _listing_summary(t["listing_id"], listings.get(t["listing_id"], {})),
            "buyer": _person(b, users.get(b, {})),
            "seller": _person(s, users.get(s, {})),
            "dispute": t.get("dispute"),
        })
    return {"disputes": out}


@router.put("/admin/disputes/{transaction_id}")
async def admin_resolve_dispute(transaction_id: str, payload: DisputeResolve, admin: dict = Depends(require_admin)):
    t = await db.transactions.find_one({"_id": parse_object_id(transaction_id, "Dispute not found")})
    if not t or not t.get("dispute"):
        raise HTTPException(status_code=404, detail="Dispute not found")
    if t.get("status") != "disputed":
        raise HTTPException(status_code=409, detail="This dispute is already closed")
    note = payload.note.strip()
    if not note or len(note) > MAX_NOTE:
        raise HTTPException(status_code=422, detail=f"Add a note (1-{MAX_NOTE} characters)")
    target = payload.target_user_id
    parties = (str(t["buyer_id"]), str(t["seller_id"]))
    if payload.outcome != "close":
        if target not in parties:
            raise HTTPException(status_code=422, detail="Choose the buyer or the seller for this outcome")
    elif target and target not in parties:
        raise HTTPException(status_code=422, detail="target_user_id must be the buyer or the seller")

    now = datetime.now(timezone.utc)
    resolution = {"outcome": payload.outcome, "note": note, "target_user_id": target,
                  "resolved_by": admin["_id"]}
    new_status = "open" if payload.reopen else "cancelled"
    update = {"status": new_status, "dispute.resolved_at": now.isoformat(), "dispute.resolution": resolution}
    if new_status == "cancelled":
        update.update({"cancelled_reason": "dispute", "cancelled_at": now.isoformat()})
    updated = await db.transactions.find_one_and_update(
        {"_id": t["_id"], "status": "disputed"}, {"$set": update}, return_document=True)
    if updated is None:
        raise HTTPException(status_code=409, detail="This dispute is already closed")

    title = (await _docs_by_id(db.listings, [t["listing_id"]])).get(t["listing_id"], {}).get("title", "your item")
    if payload.outcome == "suspend":
        hours = payload.suspend_hours if payload.suspend_hours and payload.suspend_hours > 0 else 72
        until = (now + timedelta(hours=hours)).isoformat()
        resolution["suspended_until"] = until
        await db.users.update_one({"_id": ObjectId(target)}, {"$set": {
            "suspended_until": until, "suspension_reason": f"dispute decision on '{title}'"}})
    elif payload.outcome == "ban":
        await db.users.update_one({"_id": ObjectId(target)}, {"$set": {"is_banned": True}})
    elif payload.outcome == "warn":
        await db.users.update_one({"_id": ObjectId(target)}, {"$inc": {"warning_count": 1}})
    if payload.outcome == "suspend":
        await db.transactions.update_one({"_id": t["_id"]}, {"$set": {"dispute.resolution": resolution}})

    after = ("It's open again, so you can still complete it." if payload.reopen
             else "The transaction is closed.")
    for uid in parties:
        msg = f"The dispute on '{title}' was reviewed. {after} Note from BidCa: {note}"
        if payload.outcome == "warn" and uid == target:
            msg = f"You received a warning after the dispute on '{title}'. {after} Note from BidCa: {note}"
        await create_notification(uid, "dispute_resolved", msg, t["listing_id"],
                                  extra={"transaction_id": str(t["_id"])})
        await email_user(uid, f"Dispute reviewed: {title}", msg, f"/messages/{t['_id']}")
    return {"message": "Dispute resolved", "status": new_status, "resolution": resolution}


# ---------------------------------------------------------------------------
# User page tabs (FR-23)
# ---------------------------------------------------------------------------

@router.get("/users/me/current-bids")
async def my_current_bids(user: dict = Depends(get_current_user)):
    """Active auctions I've bid on, plus items I won/bought that aren't finished yet (with a Message link)."""
    uid = user["_id"]
    listing_ids = await db.bids.distinct("listing_id", {"bidder_id": uid})
    my_max = {}
    async for b in db.bids.find({"bidder_id": uid}):
        my_max[b["listing_id"]] = max(my_max.get(b["listing_id"], 0), b.get("max_bid") or b.get("amount") or 0)
    oids = []
    for i in listing_ids:
        try:
            oids.append(ObjectId(i))
        except (InvalidId, TypeError):
            pass
    active = []
    async for l in db.listings.find({"_id": {"$in": oids}, "status": "active"}).sort("end_time", 1):
        lid = str(l["_id"])
        images = l.get("images") or []
        active.append({
            "_id": lid, "title": l.get("title"), "image": images[0] if images else None,
            "listing_type": l.get("listing_type"), "current_bid": l.get("current_bid"),
            "bid_count": l.get("bid_count", 0), "end_time": l.get("end_time"), "status": l.get("status"),
            "my_max_bid": my_max.get(lid), "is_winning": str(l.get("highest_bidder_id")) == uid,
        })

    txs = [t async for t in db.transactions.find(
        {"buyer_id": uid, "status": {"$in": ["open", "disputed"]}}).sort("created_at", -1)]
    listings = await _docs_by_id(db.listings, [t["listing_id"] for t in txs])
    users = await _docs_by_id(db.users, [str(t["seller_id"]) for t in txs])
    return {"bids": active, "won": [_brief(t, uid, listings, users) for t in txs]}


@router.get("/users/me/selling")
async def my_selling(user: dict = Depends(get_current_user)):
    """My listings that aren't finished deals, each with its live transaction (if sold) for the Message link."""
    uid = user["_id"]
    txs = {}
    async for t in db.transactions.find({"seller_id": uid}).sort("created_at", 1):
        txs[t["listing_id"]] = t  # newest sale of each listing wins
    out = []
    async for l in db.listings.find({"seller_id": uid}).sort("created_at", -1):
        lid = str(l["_id"])
        t = txs.get(lid)
        if t and t.get("status") == "completed" and l.get("status") == "sold":
            continue  # shown under Successfully Completed
        images = l.get("images") or []
        out.append({
            "_id": lid, "title": l.get("title"), "image": images[0] if images else None,
            "listing_type": l.get("listing_type"), "status": l.get("status"), "category": l.get("category"),
            "current_bid": l.get("current_bid"), "buy_it_now_price": l.get("buy_it_now_price"),
            "bid_count": l.get("bid_count", 0), "end_time": l.get("end_time"), "sold_price": l.get("sold_price"),
            "transaction": ({"_id": str(t["_id"]), "status": t.get("status"),
                             "cancelled_reason": t.get("cancelled_reason")} if t and l.get("status") == "sold" else None),
        })
    return {"listings": out}


@router.get("/users/me/completed")
async def my_completed(user: dict = Depends(get_current_user)):
    """Successfully completed deals, buy and sell side, newest first."""
    uid = user["_id"]
    txs = [t async for t in db.transactions.find(
        {"$or": [{"buyer_id": uid}, {"seller_id": uid}], "status": "completed"}).sort("completed_at", -1)]
    listings = await _docs_by_id(db.listings, [t["listing_id"] for t in txs])
    users = await _docs_by_id(db.users, [str(t[k]) for t in txs for k in ("buyer_id", "seller_id")])
    rated = set(await db.feedback.distinct("transaction_id", {"from_user_id": uid}))
    items = []
    for t in txs:
        row = _brief(t, uid, listings, users)
        row["rated"] = row["_id"] in rated
        items.append(row)
    return {"transactions": items}
