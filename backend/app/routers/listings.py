import re
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import math

from app.db import db
from app.security import get_current_user, get_optional_user, require_verified_email
from app.constants import PUBLIC_LISTING_STATUSES
from app.models import AuctionCreate
from app.helpers import calculate_positive_percentage
from app.listing_rules import (
    can_view_listing, check_complete, check_listing_cap, listing_content, new_invite_token,
    record_submission, resolve_invitees, seller_fields, strip_private_fields, timing_fields,
)

router = APIRouter()


# Listings/Auctions
@router.post("/listings", status_code=201)
async def create_listing(listing: AuctionCreate, user: dict = Depends(require_verified_email)):
    data = listing.model_dump()
    content = listing_content(data)
    if not listing.draft:
        check_complete(content)
        await check_listing_cap(user["_id"])
    private = content["listing_type"] == "private"
    invitees = await resolve_invitees(listing.invitees, user["_id"]) if private else []

    now = datetime.now(timezone.utc)
    listing_doc = {
        **content,
        # Timing: a draft gets its times when it is submitted
        "start_time": None,
        "end_time": None,
        **({} if listing.draft else timing_fields(content["duration_days"], now)),
        **seller_fields(user),
        # Bidding
        "bid_count": 0,
        "highest_bidder_id": None,
        "highest_bidder_name": None,
        "highest_bidder_max_bid": None,  # For proxy bidding
        # Status: drafts are seller-only; everything else waits for admin approval
        "status": "draft" if listing.draft else "pending",
        "winner_id": None,
        "sold_price": None,
        "watchers_count": 0,
        "views_count": 0,
        "created_at": now.isoformat()
    }
    if private:
        listing_doc["invitees"] = invitees
        listing_doc["invite_token"] = new_invite_token()
        listing_doc.setdefault("invite_expires_at", None)
    else:
        listing_doc.pop("invite_expires_at", None)

    result = await db.listings.insert_one(listing_doc)
    listing_doc["_id"] = str(result.inserted_id)
    listing_doc["seller_id"] = str(listing_doc["seller_id"])
    listing_doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
    if not listing.draft:
        await record_submission(user["_id"], listing_doc["_id"])

    return listing_doc

@router.get("/listings")
async def get_listings(
    q: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    condition: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    listing_type: Optional[str] = None,
    seller_id: Optional[str] = None,
    seller_rating: Optional[float] = None,
    status: str = "active",
    sort: str = "ending_soonest",
    page: int = 1,
    limit: int = 24
):
    if status not in PUBLIC_LISTING_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    query = {"status": status}
    
    if q:
        query["$or"] = [
            {"title": {"$regex": re.escape(q), "$options": "i"}},
            {"description": {"$regex": re.escape(q), "$options": "i"}}
        ]
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    if condition:
        query["condition"] = condition
    if province:
        query["province"] = province
    if city:
        query["city"] = city
    if min_price is not None or max_price is not None:
        # Fixed-price listings are priced by buy_it_now_price, everything else by current_bid
        bounds = {}
        if min_price is not None:
            bounds["$gte"] = min_price
        if max_price is not None:
            bounds["$lte"] = max_price
        price_clause = {"$or": [
            {"listing_type": "fixed_price", "buy_it_now_price": bounds},
            {"listing_type": {"$ne": "fixed_price"}, "current_bid": bounds},
        ]}
        query.setdefault("$and", []).append(price_clause)
    # Private listings are invite-only and never listed (FR-31)
    query["listing_type"] = {"$ne": "private"}
    if listing_type:
        query["listing_type"]["$eq"] = listing_type
    if seller_id:
        query["seller_id"] = seller_id
    if seller_rating:
        query["seller_rating"] = {"$gte": seller_rating}

    # Sorting
    sort_options = {
        # Fixed-price items (never any bids) go after the auctions (FR-07, lowest priority)
        "ending_soonest": [("fixed_price_last", 1), ("end_time", 1)],
        "newly_listed": [("created_at", -1)],
        "lowest_price": [("current_bid", 1)],
        "highest_price": [("current_bid", -1)],
        "most_bids": [("bid_count", -1)]
    }
    sort_order = sort_options.get(sort, [("end_time", 1)])
    
    skip = (page - 1) * limit
    cursor = db.listings.find(query).sort(sort_order).skip(skip).limit(limit)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
        listings.append(doc)
    
    total = await db.listings.count_documents(query)
    
    return {
        "listings": listings,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }

@router.get("/listings/featured")
async def get_featured_listings():
    # Get popular auctions (most bids, ending soon)
    cursor = db.listings.find(
        {"status": "active", "listing_type": {"$in": ["auction", "auction_bin"]}}
    ).sort([("bid_count", -1), ("end_time", 1)]).limit(8)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
        listings.append(doc)
    
    return {"listings": listings}

@router.get("/listings/ending-soon")
async def get_ending_soon():
    # Auctions ending in next 6 hours
    cutoff = datetime.now(timezone.utc) + timedelta(hours=6)
    cursor = db.listings.find(
        {
            "status": "active",
            "listing_type": {"$in": ["auction", "auction_bin"]},
            "end_time": {"$lte": cutoff.isoformat()}
        }
    ).sort("end_time", 1).limit(12)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
        listings.append(doc)
    
    return {"listings": listings}

@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, request: Request):
    user = await get_optional_user(request)
    
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Unapproved listings exist only for their seller and admins
    if listing["status"] not in PUBLIC_LISTING_STATUSES and not (
        user and (str(listing["seller_id"]) == user["_id"] or user.get("role") == "admin")
    ):
        raise HTTPException(status_code=404, detail="Listing not found")
    # Private listings exist only for their seller, invitees and admins (FR-31)
    if not can_view_listing(listing, user):
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Increment view count
    await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"views_count": 1}})
    
    listing["_id"] = str(listing["_id"])
    listing["seller_id"] = str(listing["seller_id"])
    listing.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
    strip_private_fields(listing, user)
    
    # Get bid history (masked usernames for non-sellers)
    bids_cursor = db.bids.find({"listing_id": listing_id}).sort("created_at", -1).limit(50)
    bids = []
    async for bid in bids_cursor:
        bidder_name = bid["bidder_name"]
        # Mask username unless user is the seller or the bidder
        if user and (listing["seller_id"] == user["_id"] or bid["bidder_id"] == user["_id"]):
            masked_name = bidder_name
        else:
            masked_name = bidder_name[:1] + "***" + bidder_name[-1:] if len(bidder_name) > 2 else "***"
        bids.append({
            "amount": bid["amount"],
            "bidder_name": masked_name,
            "created_at": bid["created_at"],
            "is_auto_bid": bid.get("is_auto_bid", False)
        })
    
    listing["bid_history"] = bids
    
    # Check if user is watching
    if user:
        watching = await db.watchlist.find_one({"user_id": user["_id"], "listing_id": listing_id})
        listing["is_watching"] = watching is not None
        listing["is_seller"] = listing["seller_id"] == user["_id"]
    else:
        listing["is_watching"] = False
        listing["is_seller"] = False
    
    # Get related items
    related_cursor = db.listings.find(
        {"category": listing["category"], "status": "active", "listing_type": {"$ne": "private"},
         "_id": {"$ne": ObjectId(listing_id)}}
    ).limit(6)
    related = []
    async for doc in related_cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        doc.pop("highest_bidder_max_bid", None)  # proxy max is secret (contract D9)
        related.append(doc)
    listing["related_items"] = related
    
    # Get seller info
    seller = await db.users.find_one({"_id": ObjectId(listing["seller_id"])})
    if seller:
        listing["seller_info"] = {
            "full_name": seller["full_name"],
            "city": seller["city"],
            "seller_rating": seller.get("seller_rating", 0),
            "total_ratings": seller.get("total_ratings", 0),
            "positive_percentage": calculate_positive_percentage(seller),
            "verification_badge": seller.get("verification_badge", False),
            "total_sales": seller.get("total_sales", 0),
            "member_since": seller.get("created_at")
        }
    
    return listing
