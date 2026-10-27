from fastapi import APIRouter, HTTPException, Depends, Response
from bson import ObjectId

from app.db import db
from app.accounts import (
    public_name, completed_counts, rating_counts, tiers_for, badge_for, validate_display_name,
    validate_avatar_url, refresh_public_snapshots, delete_account,
)
from app.constants import BC_CITIES
from app.helpers import parse_object_id
from app.models import AccountUpdate, AccountDelete
from app.security import get_current_user, verify_password, clear_auth_cookies

router = APIRouter()


# User Profile (public, FR-22; contract D25). Never exposes full_name, email, phone or postal code.
@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    user = await db.users.find_one({"_id": parse_object_id(user_id, "User not found")})
    if not user or user.get("deleted_at"):
        raise HTTPException(status_code=404, detail="User not found")
    uid = str(user["_id"])

    active_listings = await db.listings.count_documents(
        {"seller_id": uid, "status": "active", "listing_type": {"$ne": "private"}})
    as_buyer, as_seller = await completed_counts(uid)
    ratings = await rating_counts(uid)
    total_ratings = ratings["positive"] + ratings["neutral"] + ratings["negative"]
    badge = badge_for(user, as_buyer, as_seller)

    return {
        "id": uid,
        "display_name": public_name(user),
        "avatar_url": user.get("avatar_url"),
        "city": user.get("city"),
        "province": user.get("province", "British Columbia"),
        "member_since": user.get("created_at"),
        # Phone verified ✓ after two completed transactions — the only badge (Q009)
        "verified_badge": badge,
        "verification_badge": badge,  # older clients read this name
        "completed_as_buyer": as_buyer,
        "completed_as_seller": as_seller,
        "ratings": {k: ratings[k] for k in ("positive", "neutral", "negative")},
        "total_ratings": total_ratings,
        "positive_percentage": round(ratings["positive"] / total_ratings * 100, 1) if total_ratings else 100.0,
        "seller_rating": user.get("seller_rating", 0),
        "total_sales": as_seller,
        "tiers": tiers_for(as_buyer, as_seller, ratings),
        "exchange_methods": user.get("exchange_methods") or [],
        "active_listings": active_listings,
    }


# Account settings (owner only, FR-22; contract D26)
@router.patch("/users/me")
async def update_my_account(body: AccountUpdate, user: dict = Depends(get_current_user)):
    updates = {}
    if body.display_name is not None:
        updates["display_name"] = validate_display_name(body.display_name)
    if body.city is not None:
        if body.city not in BC_CITIES:
            raise HTTPException(status_code=400, detail="Choose your city from the list")
        updates["city"] = body.city
    if body.avatar_url is not None:
        updates["avatar_url"] = validate_avatar_url(body.avatar_url) if body.avatar_url else None
    if body.exchange_methods is not None:
        updates["exchange_methods"] = list(dict.fromkeys(body.exchange_methods))  # de-duplicated, order kept
    if updates:
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": updates})
        if "display_name" in updates:
            await refresh_public_snapshots(user["_id"])
    fresh = await db.users.find_one({"_id": ObjectId(user["_id"])}, {"password_hash": 0})
    fresh["_id"] = str(fresh["_id"])
    return fresh


@router.post("/users/me/delete")
async def delete_my_account(body: AccountDelete, response: Response, user: dict = Depends(get_current_user)):
    record = await db.users.find_one({"_id": ObjectId(user["_id"])}, {"password_hash": 1})
    if not record or not verify_password(body.password, record["password_hash"]):
        raise HTTPException(status_code=403, detail="Password is not correct")
    await delete_account(user)
    clear_auth_cookies(response)
    return {"message": "Account deleted"}
