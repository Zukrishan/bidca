from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.helpers import parse_object_id
from app.listing_rules import can_view_listing

router = APIRouter()


# Watchlist
@router.post("/listings/{listing_id}/watch")
async def watch_listing(listing_id: str, user: dict = Depends(get_current_user)):
    oid = parse_object_id(listing_id, "Listing not found")
    found = await db.listings.find_one({"_id": oid}, {"listing_type": 1, "seller_id": 1, "invitees": 1})
    if not found or not can_view_listing(found, user):  # private: invitees only (FR-31)
        raise HTTPException(status_code=404, detail="Listing not found")
    existing = await db.watchlist.find_one({"user_id": user["_id"], "listing_id": listing_id})
    
    if existing:
        # Remove from watchlist
        await db.watchlist.delete_one({"_id": existing["_id"]})
        await db.listings.update_one({"_id": oid}, {"$inc": {"watchers_count": -1}})
        return {"watching": False, "message": "Removed from watchlist"}
    else:
        # Add to watchlist
        await db.watchlist.insert_one({
            "user_id": user["_id"],
            "listing_id": listing_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        await db.listings.update_one({"_id": oid}, {"$inc": {"watchers_count": 1}})
        return {"watching": True, "message": "Added to watchlist"}

@router.get("/users/me/watchlist")
async def get_watchlist(user: dict = Depends(get_current_user)):
    cursor = db.watchlist.find({"user_id": user["_id"]}).sort("created_at", -1)
    
    items = []
    async for watch in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(watch["listing_id"])})
        if listing and can_view_listing(listing, user):  # e.g. no longer invited (FR-31)
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
            items.append(listing)
    
    return {"watchlist": items}
