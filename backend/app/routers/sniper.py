from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.db import db
from app.security import get_current_user, require_verified_email
from app.constants import get_bid_increment
from app.models import SniperBidCreate
from app.listing_rules import can_view_listing

router = APIRouter()


# Sniper Bid
@router.post("/listings/{listing_id}/sniper-bid")
async def create_sniper_bid(listing_id: str, sniper: SniperBidCreate, user: dict = Depends(require_verified_email)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing and not can_view_listing(listing, user):  # private: invitees only (FR-31)
        raise HTTPException(status_code=404, detail="Listing not found")
    if not listing or listing["status"] != "active":
        raise HTTPException(status_code=400, detail="Listing not available")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
    current_bid = listing["current_bid"]
    min_bid = current_bid + get_bid_increment(current_bid) if listing.get("bid_count", 0) > 0 else current_bid
    if sniper.max_bid < min_bid:
        raise HTTPException(status_code=400, detail=f"Minimum bid is ${min_bid:.2f}")
    
    end_time = datetime.fromisoformat(listing["end_time"])
    execute_time = end_time - timedelta(minutes=sniper.minutes_before_end)
    
    if execute_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Sniper bid time has already passed")
    
    sniper_doc = {
        "listing_id": listing_id,
        "user_id": user["_id"],
        "max_bid": sniper.max_bid,
        "minutes_before_end": sniper.minutes_before_end,
        "execute_at": execute_time.isoformat(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sniper_bids.insert_one(sniper_doc)
    
    return {"message": f"Sniper bid scheduled for {sniper.minutes_before_end} minutes before auction end"}
