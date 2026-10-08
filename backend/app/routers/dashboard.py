from fastapi import APIRouter, Depends
from typing import Optional
from bson import ObjectId

from app.db import db
from app.security import get_current_user

router = APIRouter()


# User Dashboard
@router.get("/users/me/bids")
async def get_my_bids(user: dict = Depends(get_current_user)):
    cursor = db.bids.find({"bidder_id": user["_id"]}).sort("created_at", -1)
    
    bids_by_listing = {}
    async for bid in cursor:
        if bid["listing_id"] not in bids_by_listing:
            listing = await db.listings.find_one({"_id": ObjectId(bid["listing_id"])})
            if listing:
                listing["_id"] = str(listing["_id"])
                listing["seller_id"] = str(listing["seller_id"])
                listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
                listing["my_max_bid"] = bid.get("max_bid", bid.get("amount", 0))
                listing["is_winning"] = str(listing.get("highest_bidder_id")) == user["_id"]
                bids_by_listing[bid["listing_id"]] = listing
    
    return {"bids": list(bids_by_listing.values())}

@router.get("/users/me/listings")
async def get_my_listings(user: dict = Depends(get_current_user), status: Optional[str] = None):
    query = {"seller_id": user["_id"]}
    if status:
        query["status"] = status
    
    cursor = db.listings.find(query).sort("created_at", -1)
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
        listings.append(doc)
    
    return {"listings": listings}

@router.get("/users/me/purchases")
async def get_my_purchases(user: dict = Depends(get_current_user)):
    cursor = db.transactions.find({"buyer_id": user["_id"]}).sort("created_at", -1)
    
    purchases = []
    async for t in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(t["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
            t["listing"] = listing
            t["_id"] = str(t["_id"])
            purchases.append(t)
    
    return {"purchases": purchases}

@router.get("/users/me/sales")
async def get_my_sales(user: dict = Depends(get_current_user)):
    cursor = db.transactions.find({"seller_id": user["_id"]}).sort("created_at", -1)
    
    sales = []
    async for t in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(t["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
            t["listing"] = listing
            t["_id"] = str(t["_id"])
            
            # Get buyer info
            buyer = await db.users.find_one({"_id": ObjectId(t["buyer_id"])})
            if buyer:
                t["buyer_name"] = buyer["full_name"]
            sales.append(t)
    
    return {"sales": sales}
