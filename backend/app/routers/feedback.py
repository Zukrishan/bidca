from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import FeedbackCreate

router = APIRouter()


# Feedback System
@router.post("/transactions/{transaction_id}/feedback")
async def leave_feedback(transaction_id: str, feedback: FeedbackCreate, user: dict = Depends(get_current_user)):
    try:
        transaction = await db.transactions.find_one({"_id": ObjectId(transaction_id)})
    except:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Determine who is leaving feedback
    if transaction["buyer_id"] == user["_id"]:
        target_id = transaction["seller_id"]
        feedback_type = "buyer_to_seller"
    elif transaction["seller_id"] == user["_id"]:
        target_id = transaction["buyer_id"]
        feedback_type = "seller_to_buyer"
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if already left feedback
    existing = await db.feedback.find_one({
        "transaction_id": transaction_id,
        "from_user_id": user["_id"]
    })
    if existing:
        raise HTTPException(status_code=400, detail="You have already left feedback for this transaction")
    
    feedback_doc = {
        "transaction_id": transaction_id,
        "listing_id": transaction["listing_id"],
        "from_user_id": user["_id"],
        "from_user_name": user["full_name"],
        "to_user_id": target_id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "feedback_type": feedback_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback_doc)
    
    # Update target user's rating stats
    rating_field = f"{feedback.rating}_ratings"
    await db.users.update_one(
        {"_id": ObjectId(target_id)},
        {"$inc": {"total_ratings": 1, rating_field: 1}}
    )
    
    # Recalculate seller rating
    target_user = await db.users.find_one({"_id": ObjectId(target_id)})
    if target_user:
        total = target_user.get("total_ratings", 0)
        positive = target_user.get("positive_ratings", 0)
        neutral = target_user.get("neutral_ratings", 0)
        # Weighted score: positive=5, neutral=3, negative=1
        score = (positive * 5 + neutral * 3) / (total * 5) * 5 if total > 0 else 0
        await db.users.update_one({"_id": ObjectId(target_id)}, {"$set": {"seller_rating": round(score, 1)}})
    
    return {"message": "Feedback submitted"}

@router.get("/users/{user_id}/feedback")
async def get_user_feedback(user_id: str, page: int = 1, limit: int = 20):
    skip = (page - 1) * limit
    cursor = db.feedback.find({"to_user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    
    feedbacks = []
    async for f in cursor:
        f["_id"] = str(f["_id"])
        feedbacks.append(f)
    
    total = await db.feedback.count_documents({"to_user_id": user_id})
    
    return {"feedback": feedbacks, "total": total}
