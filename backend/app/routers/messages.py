"""
messages.py — FR-20: buyer–seller messaging after a sale.

A conversation is one transaction; only its buyer and seller can read or write it (anyone else
gets 404, so a transaction id never confirms its own existence). Bodies are plain text.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import db
from app.email import send_email
from app.helpers import create_notification
from app.realtime import sio
from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_BODY = 2000
RATE_LIMIT = 20            # messages per sender per transaction ...
RATE_WINDOW = timedelta(minutes=10)  # ... per window


class MessageIn(BaseModel):
    body: str


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Conversation not found")


async def _participant_transaction(transaction_id: str, user: dict) -> dict:
    t = await db.transactions.find_one({"_id": _oid(transaction_id)})
    if not t or user["_id"] not in (str(t.get("buyer_id")), str(t.get("seller_id"))):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return t


def _other_id(t: dict, user: dict) -> str:
    return str(t["seller_id"]) if user["_id"] == str(t["buyer_id"]) else str(t["buyer_id"])


def _public(m: dict) -> dict:
    return {"_id": str(m["_id"]), "sender_id": m["sender_id"], "body": m["body"],
            "created_at": m["created_at"], "read_at": m.get("read_at")}


async def _users_by_id(ids) -> dict:
    oids = []
    for i in set(ids):
        try:
            oids.append(ObjectId(i))
        except (InvalidId, TypeError):
            pass
    out = {}
    async for u in db.users.find({"_id": {"$in": oids}}):
        out[str(u["_id"])] = u
    return out


async def _listings_by_id(ids) -> dict:
    oids = []
    for i in set(ids):
        try:
            oids.append(ObjectId(i))
        except (InvalidId, TypeError):
            pass
    out = {}
    async for l in db.listings.find({"_id": {"$in": oids}}):
        out[str(l["_id"])] = l
    return out


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    uid = user["_id"]
    txs = []
    # Bounded: the 100 most recent transactions. Queries: transactions, users, listings, then
    # two per transaction (last message, unread count) — acceptable for <= 100 rows.
    cursor = db.transactions.find({"$or": [{"buyer_id": uid}, {"seller_id": uid}]}).sort("created_at", -1).limit(100)
    async for t in cursor:
        txs.append(t)
    users = await _users_by_id([_other_id(t, user) for t in txs])
    listings = await _listings_by_id([t["listing_id"] for t in txs])

    items = []
    for t in txs:
        tid = str(t["_id"])
        last = await db.messages.find({"transaction_id": tid}).sort("created_at", -1).limit(1).to_list(1)
        unread = await db.messages.count_documents({"transaction_id": tid, "recipient_id": uid, "read_at": None})
        other = users.get(_other_id(t, user), {})
        listing = listings.get(t["listing_id"], {})
        images = listing.get("images") or []
        items.append({
            "transaction_id": tid,
            "listing_id": t["listing_id"],
            "listing_title": listing.get("title", "Removed listing"),
            "listing_image": images[0] if images else None,
            "other_party": {"id": _other_id(t, user), "full_name": other.get("full_name", "Former user")},
            "role": "buyer" if uid == str(t["buyer_id"]) else "seller",
            "last_message": ({"body": last[0]["body"], "created_at": last[0]["created_at"],
                              "sender_id": last[0]["sender_id"]} if last else None),
            "unread_count": unread,
            "amount": t.get("amount"),
            "_activity": last[0]["created_at"] if last else t.get("created_at", ""),
        })
    items.sort(key=lambda i: i["_activity"], reverse=True)
    for i in items:
        del i["_activity"]
    return {"conversations": items}


@router.get("/messages/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    return {"unread": await db.messages.count_documents({"recipient_id": user["_id"], "read_at": None})}


@router.get("/transactions/{transaction_id}/messages")
async def get_messages(transaction_id: str, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    tid = str(t["_id"])
    now = datetime.now(timezone.utc).isoformat()
    await db.messages.update_many({"transaction_id": tid, "recipient_id": user["_id"], "read_at": None},
                                  {"$set": {"read_at": now}})
    # The message notification is about this thread, so it is no longer news either.
    await db.notifications.update_many(
        {"user_id": user["_id"], "type": "new_message", "transaction_id": tid, "read": False},
        {"$set": {"read": True}})
    msgs = [_public(m) async for m in db.messages.find({"transaction_id": tid}).sort("created_at", 1)]
    other = (await _users_by_id([_other_id(t, user)])).get(_other_id(t, user), {})
    listing = (await _listings_by_id([t["listing_id"]])).get(t["listing_id"], {})
    images = listing.get("images") or []
    return {
        "transaction_id": tid,
        "listing": {"id": t["listing_id"], "title": listing.get("title", "Removed listing"),
                    "image": images[0] if images else None},
        "other_party": {"id": _other_id(t, user), "full_name": other.get("full_name", "Former user"),
                        "city": other.get("city")},
        "messages": msgs,
    }


@router.post("/transactions/{transaction_id}/messages", status_code=201)
async def send_message(transaction_id: str, payload: MessageIn, user: dict = Depends(get_current_user)):
    t = await _participant_transaction(transaction_id, user)
    body = payload.body.strip()
    if not body or len(body) > MAX_BODY:
        raise HTTPException(status_code=422, detail=f"Message must be 1-{MAX_BODY} characters")
    tid = str(t["_id"])
    uid = user["_id"]

    since = (datetime.now(timezone.utc) - RATE_WINDOW).isoformat()
    recent = await db.messages.count_documents(
        {"transaction_id": tid, "sender_id": uid, "created_at": {"$gte": since}})
    if recent >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="You're sending messages too quickly. Try again in a few minutes.")

    recipient_id = _other_id(t, user)
    doc = {"transaction_id": tid, "sender_id": uid, "recipient_id": recipient_id, "body": body,
           "created_at": datetime.now(timezone.utc).isoformat(), "read_at": None}
    res = await db.messages.insert_one(doc)
    message = _public({**doc, "_id": res.inserted_id})

    # The buyer's first message is their response to the win; it stops the no-response job (FR-26).
    if uid == str(t["buyer_id"]) and not t.get("buyer_responded_at"):
        await db.transactions.update_one({"_id": t["_id"], "buyer_responded_at": None},
                                         {"$set": {"buyer_responded_at": doc["created_at"]}})

    # Real-time push is best effort: it must never fail the send.
    try:
        await sio.emit("message", {"transaction_id": tid, "message": message}, room=f"user_{recipient_id}")
    except Exception as exc:
        logger.error("Message push failed for user %s: %s", recipient_id, exc)

    await _notify(t, user, recipient_id, body)
    return message


async def _notify(t: dict, sender: dict, recipient_id: str, body: str) -> None:
    """One unread `new_message` notification (and email) per (recipient, transaction)."""
    tid = str(t["_id"])
    try:
        if await db.notifications.find_one({"user_id": recipient_id, "type": "new_message",
                                            "transaction_id": tid, "read": False}):
            return
        listing = (await _listings_by_id([t["listing_id"]])).get(t["listing_id"], {})
        title = listing.get("title", "your sale")
        first = (sender.get("full_name") or "Someone").split(" ")[0]
        text = f"New message from {first} about {title}"
        await create_notification(recipient_id, "new_message", text, t["listing_id"], extra={"transaction_id": tid})
        recipient = await db.users.find_one({"_id": _oid(recipient_id)})
        if recipient and recipient.get("email"):
            await send_email(to=recipient["email"], subject=text,
                             html=f"<p>{_esc(text)}.</p><p>Sign in to BidCa and open Messages to reply.</p>")
    except Exception as exc:
        logger.error("Message notification failed for user %s: %s", recipient_id, exc)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
