from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Literal
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import require_admin
from app.models import ListingUpdate, UserUpdate
from app.helpers import calculate_positive_percentage, create_notification

router = APIRouter()


# Admin endpoints
@router.get("/admin/stats")
async def admin_get_stats(admin: dict = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    total_listings = await db.listings.count_documents({})
    active_auctions = await db.listings.count_documents({"status": "active"})
    pending_listings = await db.listings.count_documents({"status": "pending"})
    pending_verifications = await db.verifications.count_documents({"status": "pending"})
    total_bids = await db.bids.count_documents({})
    total_transactions = await db.transactions.count_documents({})
    pending_reports = await db.reports.count_documents({"status": "pending"})
    
    # Revenue (10% fee on sold items)
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount"}}}]
    result = await db.transactions.aggregate(pipeline).to_list(1)
    total_gmv = result[0]["total"] if result else 0
    platform_revenue = 0  # Platform fee is free for now
    
    return {
        "total_users": total_users,
        "total_listings": total_listings,
        "active_auctions": active_auctions,
        "pending_listings": pending_listings,
        "pending_verifications": pending_verifications,
        "total_bids": total_bids,
        "total_transactions": total_transactions,
        "pending_reports": pending_reports,
        "total_gmv": total_gmv,
        "platform_revenue": platform_revenue
    }

@router.get("/admin/listings")
async def admin_get_listings(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    query = {}
    if status:
        query["status"] = status
    
    skip = (page - 1) * limit
    cursor = db.listings.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        listings.append(doc)
    
    total = await db.listings.count_documents(query)
    return {"listings": listings, "total": total, "page": page}

@router.put("/admin/listings/{listing_id}")
async def admin_update_listing(listing_id: str, update: ListingUpdate, admin: dict = Depends(require_admin)):
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$set": update_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if listing:
        await create_notification(
            str(listing["seller_id"]),
            "listing_status",
            f"Your listing '{listing['title']}' has been {update.status}",
            listing_id
        )
    
    return {"message": f"Listing updated"}

@router.delete("/admin/listings/{listing_id}")
async def admin_delete_listing(listing_id: str, admin: dict = Depends(require_admin)):
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    await db.listings.delete_one({"_id": ObjectId(listing_id)})
    await db.bids.delete_many({"listing_id": listing_id})
    
    return {"message": "Listing deleted"}

@router.get("/admin/users")
async def admin_get_users(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    query = {}
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    cursor = db.users.find(query, {"password_hash": 0}).skip(skip).limit(limit).sort("created_at", -1)
    
    users = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["positive_percentage"] = calculate_positive_percentage(doc)
        users.append(doc)
    
    total = await db.users.count_documents(query)
    return {"users": users, "total": total, "page": page}

@router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, update: UserUpdate, admin: dict = Depends(require_admin)):
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated"}

@router.get("/admin/verifications")
async def admin_get_verifications(
    status: str = "pending",
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    query = {"status": status}
    skip = (page - 1) * limit
    cursor = db.verifications.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    verifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        verifications.append(doc)
    
    total = await db.verifications.count_documents(query)
    return {"verifications": verifications, "total": total, "page": page}

@router.put("/admin/verifications/{verification_id}")
async def admin_review_verification(
    verification_id: str,
    status: Literal["approved", "rejected"],
    admin: dict = Depends(require_admin)
):
    verification = await db.verifications.find_one({"_id": ObjectId(verification_id)})
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    await db.verifications.update_one(
        {"_id": ObjectId(verification_id)},
        {"$set": {"status": status, "reviewed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    user_update = {"verification_status": "verified" if status == "approved" else "unverified"}
    if status == "approved":
        user_update["verification_badge"] = True
    
    await db.users.update_one({"_id": ObjectId(verification["user_id"])}, {"$set": user_update})
    
    await create_notification(verification["user_id"], "verification", f"Your verification has been {status}")
    
    return {"message": f"Verification {status}"}

@router.get("/admin/reports")
async def admin_get_reports(
    status: str = "pending",
    page: int = 1,
    limit: int = 20,
    admin: dict = Depends(require_admin)
):
    query = {"status": status}
    skip = (page - 1) * limit
    cursor = db.reports.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    reports = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        reports.append(doc)
    
    total = await db.reports.count_documents(query)
    return {"reports": reports, "total": total, "page": page}
