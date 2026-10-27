from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Literal
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user, require_verified_email
from app.models import BestOfferCreate
from app.helpers import create_notification
from app.sales import complete_sale
from app.accounts import public_name

router = APIRouter()


# Best Offer
@router.post("/listings/{listing_id}/best-offer")
async def submit_best_offer(listing_id: str, offer: BestOfferCreate, user: dict = Depends(require_verified_email)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This listing is not active")
    
    # Once an auction is open its price can't be negotiated (FR-28), whatever older listings stored
    if listing.get("listing_type") != "fixed_price" or not listing.get("accepts_best_offer"):
        raise HTTPException(status_code=400, detail="This listing does not accept offers")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot make an offer on your own listing")
    
    offer_doc = {
        "listing_id": listing_id,
        "buyer_id": user["_id"],
        "buyer_name": public_name(user),
        "amount": offer.offer_amount,
        "message": offer.message,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.offers.insert_one(offer_doc)
    
    # Notify seller
    await create_notification(
        str(listing["seller_id"]),
        "new_offer",
        f"New offer of ${offer.offer_amount:.2f} on '{listing['title']}'",
        listing_id
    )
    
    return {"message": "Offer submitted", "offer_id": str(result.inserted_id)}

@router.put("/offers/{offer_id}/respond")
async def respond_to_offer(
    offer_id: str,
    action: Literal["accept", "decline", "counter"],
    counter_amount: Optional[float] = None,
    user: dict = Depends(get_current_user)
):
    try:
        offer = await db.offers.find_one({"_id": ObjectId(offer_id)})
    except:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    listing = await db.listings.find_one({"_id": ObjectId(offer["listing_id"])})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if str(listing["seller_id"]) != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the seller can respond to offers")
    if offer.get("status") != "pending":
        raise HTTPException(status_code=400, detail="This offer has already been answered")
    
    if action == "accept":
        if listing.get("status") != "active":
            raise HTTPException(status_code=409, detail="This listing has already ended")
        # Same ending as Buy It Now: atomic sold transition, transaction, stats, notifications
        await complete_sale(listing, offer["buyer_id"], offer["amount"], "best_offer", offer_id=offer_id)
        await db.offers.update_one({"_id": ObjectId(offer_id)}, {"$set": {"status": "accepted"}})
        # Any other open offers on the item can no longer be accepted
        await db.offers.update_many(
            {"listing_id": offer["listing_id"], "status": "pending", "_id": {"$ne": ObjectId(offer_id)}},
            {"$set": {"status": "declined"}},
        )
        await create_notification(
            offer["buyer_id"],
            "offer_accepted",
            f"Your offer of ${offer['amount']:.2f} was accepted!",
            offer["listing_id"]
        )
        
    elif action == "decline":
        await db.offers.update_one({"_id": ObjectId(offer_id)}, {"$set": {"status": "declined"}})
        await create_notification(
            offer["buyer_id"],
            "offer_declined",
            f"Your offer of ${offer['amount']:.2f} was declined",
            offer["listing_id"]
        )
        
    elif action == "counter":
        if not counter_amount:
            raise HTTPException(status_code=400, detail="Counter amount required")
        await db.offers.update_one(
            {"_id": ObjectId(offer_id)},
            {"$set": {"status": "countered", "counter_amount": counter_amount}}
        )
        await create_notification(
            offer["buyer_id"],
            "counter_offer",
            f"Seller countered with ${counter_amount:.2f}",
            offer["listing_id"]
        )
    
    return {"message": f"Offer {action}ed"}
