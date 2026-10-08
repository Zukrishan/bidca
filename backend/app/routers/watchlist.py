from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user

router = APIRouter()


# Watchlist
@router.post("/listings/{listing_id}/watch")
async def watch_listing(listing_id: str, user: dict = Depends(get_current_user)):
    existing = await db.watchlist.find_one({"user_id": user["_id"], "listing_id": listing_id})
    
    if existing:
        # Remove from watchlist
        await db.watchlist.delete_one({"_id": existing["_id"]})
        await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"watchers_count": -1}})
        return {"watching": False, "message": "Removed from watchlist"}
    else:
        # Add to watchlist
        await db.watchlist.insert_one({
            "user_id": user["_id"],
            "listing_id": listing_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"watchers_count": 1}})
        return {"watching": True, "message": "Added to watchlist"}

@router.get("/users/me/watchlist")
async def get_watchlist(user: dict = Depends(get_current_user)):
    cursor = db.watchlist.find({"user_id": user["_id"]}).sort("created_at", -1)
    
    items = []
    async for watch in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(watch["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
            items.append(listing)
    
    return {"watchlist": items}
