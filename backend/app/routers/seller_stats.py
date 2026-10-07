from fastapi import APIRouter, Depends

from app.db import db
from app.security import get_current_user
from app.helpers import calculate_positive_percentage

router = APIRouter()


# Seller Dashboard Stats
@router.get("/users/me/seller-stats")
async def get_seller_stats(user: dict = Depends(get_current_user)):
    active_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "active"})
    pending_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "pending"})
    sold_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "sold"})
    unsold_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "unsold"})
    
    # Total watchers on active listings
    pipeline = [
        {"$match": {"seller_id": user["_id"], "status": "active"}},
        {"$group": {"_id": None, "total_watchers": {"$sum": "$watchers_count"}, "total_views": {"$sum": "$views_count"}}}
    ]
    result = await db.listings.aggregate(pipeline).to_list(1)
    watchers = result[0]["total_watchers"] if result else 0
    views = result[0]["total_views"] if result else 0
    
    # Active bids
    active_bids = await db.bids.count_documents({
        "listing_id": {"$in": [str(l["_id"]) async for l in db.listings.find({"seller_id": user["_id"], "status": "active"})]}
    })
    
    return {
        "active_listings": active_listings,
        "pending_listings": pending_listings,
        "sold_listings": sold_listings,
        "unsold_listings": unsold_listings,
        "total_watchers": watchers,
        "total_views": views,
        "total_sales": user.get("total_sales", 0),
        "total_revenue": user.get("total_sales_amount", 0),
        "seller_rating": user.get("seller_rating", 0),
        "total_ratings": user.get("total_ratings", 0),
        "positive_percentage": calculate_positive_percentage(user)
    }
