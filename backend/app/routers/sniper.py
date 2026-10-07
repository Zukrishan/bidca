from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import SniperBidCreate

router = APIRouter()


# Sniper Bid
@router.post("/listings/{listing_id}/sniper-bid")
async def create_sniper_bid(listing_id: str, sniper: SniperBidCreate, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing or listing["status"] != "active":
        raise HTTPException(status_code=400, detail="Listing not available")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
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
