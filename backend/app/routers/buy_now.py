from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.helpers import create_notification
from app.realtime import broadcast_auction_end

router = APIRouter()


# Buy It Now
@router.post("/listings/{listing_id}/buy-now")
async def buy_it_now(listing_id: str, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This listing is not active")
    
    if not listing.get("buy_it_now_price"):
        raise HTTPException(status_code=400, detail="This listing does not have a Buy It Now option")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot buy your own listing")
    
    bin_price = listing["buy_it_now_price"]
    
    # End auction immediately
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "status": "sold",
                "winner_id": user["_id"],
                "sold_price": bin_price,
                "end_time": datetime.now(timezone.utc).isoformat(),
                "sold_via": "buy_it_now"
            }
        }
    )
    
    # Create transaction record
    transaction = {
        "listing_id": listing_id,
        "seller_id": str(listing["seller_id"]),
        "buyer_id": user["_id"],
        "amount": bin_price,
        "type": "buy_it_now",
        "status": "pending_payment",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(transaction)
    
    # Notify seller
    await create_notification(
        str(listing["seller_id"]),
        "item_sold",
        f"Your item '{listing['title']}' was sold via Buy It Now for ${bin_price:.2f}!",
        listing_id
    )
    
    # Update stats
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$inc": {"total_purchases": 1, "auctions_won": 1}})
    await db.users.update_one(
        {"_id": listing["seller_id"]},
        {"$inc": {"total_sales": 1, "total_sales_amount": bin_price}}
    )
    
    # Broadcast auction end
    await broadcast_auction_end(listing_id, {"listing_id": listing_id, "sold_via": "buy_it_now", "price": bin_price})
    
    return {"message": "Purchase successful!", "price": bin_price}
