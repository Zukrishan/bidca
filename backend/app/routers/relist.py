from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.db import db
from app.security import get_current_user, require_verified_email

router = APIRouter()


# Relist Item
@router.post("/listings/{listing_id}/relist")
async def relist_item(listing_id: str, duration_days: int = 7, user: dict = Depends(require_verified_email)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if str(listing["seller_id"]) != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if listing["status"] not in ["ended", "unsold"]:
        raise HTTPException(status_code=400, detail="Can only relist ended or unsold items")
    
    end_time = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "status": "pending",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": end_time.isoformat(),
                "current_bid": listing["starting_bid"],
                "bid_count": 0,
                "highest_bidder_id": None,
                "highest_bidder_name": None,
                "highest_bidder_max_bid": None,
                "reserve_met": False if listing.get("reserve_price") else True,
                "winner_id": None,
                "sold_price": None
            }
        }
    )
    
    return {"message": "Item relisted for approval"}
