from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.db import db
from app.helpers import calculate_positive_percentage

router = APIRouter()


# User Profile (public)
@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get active listings
    # listings store seller_id as the stringified user id
    active_listings = await db.listings.count_documents({"seller_id": str(user["_id"]), "status": "active"})
    
    return {
        "id": str(user["_id"]),
        "full_name": user["full_name"],
        "city": user["city"],
        "province": user.get("province", "British Columbia"),
        "verification_badge": user.get("verification_badge", False),
        "seller_rating": user.get("seller_rating", 0),
        "total_ratings": user.get("total_ratings", 0),
        "positive_percentage": calculate_positive_percentage(user),
        "total_sales": user.get("total_sales", 0),
        "active_listings": active_listings,
        "member_since": user.get("created_at")
    }
