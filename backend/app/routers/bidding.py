from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user, require_verified_email
from app.constants import get_bid_increment
from app.models import BidCreate
from app.helpers import create_notification
from app.realtime import broadcast_bid_update

router = APIRouter()


# Proxy Bidding System
@router.post("/listings/{listing_id}/bid")
async def place_bid(listing_id: str, bid: BidCreate, user: dict = Depends(require_verified_email), background_tasks: BackgroundTasks = None):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This auction is not active")
    
    if listing["listing_type"] == "fixed_price":
        raise HTTPException(status_code=400, detail="This is a fixed-price listing")
    
    # Check if auction has ended
    end_time = datetime.fromisoformat(listing["end_time"])
    if datetime.now(timezone.utc) > end_time:
        raise HTTPException(status_code=400, detail="This auction has ended")
    
    # Check seller can't bid on own auction
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
    current_bid = listing["current_bid"]
    bid_increment = get_bid_increment(current_bid)
    min_bid = current_bid + bid_increment if listing["bid_count"] > 0 else current_bid
    
    if bid.max_bid < min_bid:
        raise HTTPException(status_code=400, detail=f"Minimum bid is ${min_bid:.2f}")
    
    # Proxy bidding logic
    current_max_bid = listing.get("highest_bidder_max_bid", 0) or 0
    current_highest_bidder = listing.get("highest_bidder_id")
    
    if current_highest_bidder and str(current_highest_bidder) == user["_id"]:
        # User is already highest bidder, just update their max
        if bid.max_bid <= current_max_bid:
            raise HTTPException(status_code=400, detail="Your new maximum must be higher than your current maximum bid")
        
        await db.listings.update_one(
            {"_id": ObjectId(listing_id)},
            {"$set": {"highest_bidder_max_bid": bid.max_bid}}
        )
        return {"message": "Maximum bid updated", "current_bid": current_bid, "your_max_bid": bid.max_bid}
    
    # Calculate new current bid
    if current_max_bid > 0:
        if bid.max_bid > current_max_bid:
            # New bidder wins, set price to previous max + increment
            new_current_bid = min(current_max_bid + bid_increment, bid.max_bid)
            new_highest_bidder = user["_id"]
            new_max_bid = bid.max_bid
            
            # Notify outbid user
            if current_highest_bidder:
                await create_notification(
                    str(current_highest_bidder),
                    "outbid",
                    f"You've been outbid on '{listing['title']}'! Current bid: ${new_current_bid:.2f}",
                    listing_id
                )
        else:
            # Current bidder stays, auto-bid up to new bid
            new_current_bid = min(bid.max_bid + bid_increment, current_max_bid)
            new_highest_bidder = current_highest_bidder
            new_max_bid = current_max_bid
            
            # Notify the new bidder they were outbid immediately
            await create_notification(
                user["_id"],
                "outbid",
                f"You were outbid on '{listing['title']}'. Current bid: ${new_current_bid:.2f}",
                listing_id
            )
    else:
        new_current_bid = listing["starting_bid"]
        new_highest_bidder = user["_id"]
        new_max_bid = bid.max_bid
    
    # Check reserve price
    reserve_met = True
    if listing.get("reserve_price"):
        reserve_met = new_current_bid >= listing["reserve_price"]
    
    # Create bid record
    bid_doc = {
        "listing_id": listing_id,
        "bidder_id": user["_id"],
        "bidder_name": user["full_name"],
        "amount": new_current_bid,
        "max_bid": bid.max_bid,
        "is_auto_bid": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bids.insert_one(bid_doc)
    
    # Update listing
    new_bid_increment = get_bid_increment(new_current_bid)
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "current_bid": new_current_bid,
                "bid_increment": new_bid_increment,
                "highest_bidder_id": new_highest_bidder,
                "highest_bidder_name": user["full_name"] if str(new_highest_bidder) == user["_id"] else listing.get("highest_bidder_name"),
                "highest_bidder_max_bid": new_max_bid,
                "reserve_met": reserve_met
            },
            "$inc": {"bid_count": 1}
        }
    )
    
    # Update user stats
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$inc": {"total_bids_placed": 1}})
    
    # Broadcast bid update
    await broadcast_bid_update(listing_id, {
        "listing_id": listing_id,
        "current_bid": new_current_bid,
        "bid_count": listing["bid_count"] + 1,
        "bid_increment": new_bid_increment,
        "reserve_met": reserve_met,
        "bidder_name": user["full_name"][:1] + "***"
    })
    
    return {
        "message": "Bid placed successfully",
        "current_bid": new_current_bid,
        "your_max_bid": bid.max_bid,
        "is_winning": str(new_highest_bidder) == user["_id"],
        "reserve_met": reserve_met
    }
