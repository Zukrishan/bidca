from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import FeedbackCreate

router = APIRouter()


SYSTEM_USER_ID = "system"  # from_user_id of ratings BidCa issues itself (no-response, dispute decisions)


async def record_feedback(transaction: dict, from_user_id: str, from_user_name: str, to_user_id: str,
                          rating: str, comment: str, feedback_type: str, system: bool = False) -> bool:
    """Store one rating and update the target's counters. False if this rater already rated this deal."""
    transaction_id = str(transaction["_id"])
    if await db.feedback.find_one({"transaction_id": transaction_id, "from_user_id": from_user_id}):
        return False

    feedback_doc = {
        "transaction_id": transaction_id,
        "listing_id": transaction["listing_id"],
        "from_user_id": from_user_id,
        "from_user_name": from_user_name,
        "to_user_id": to_user_id,
        "rating": rating,
        "comment": comment,
        "feedback_type": feedback_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    if system:
        feedback_doc["system"] = True  # issued by BidCa; counts like any other rating (Q013)
    await db.feedback.insert_one(feedback_doc)

    # Update target user's rating stats
    rating_field = f"{rating}_ratings"
    await db.users.update_one(
        {"_id": ObjectId(to_user_id)},
        {"$inc": {"total_ratings": 1, rating_field: 1}}
    )

    # Recalculate seller rating
    target_user = await db.users.find_one({"_id": ObjectId(to_user_id)})
    if target_user:
        total = target_user.get("total_ratings", 0)
        positive = target_user.get("positive_ratings", 0)
        neutral = target_user.get("neutral_ratings", 0)
        # Weighted score: positive=5, neutral=3, negative=1
        score = (positive * 5 + neutral * 3) / (total * 5) * 5 if total > 0 else 0
        await db.users.update_one({"_id": ObjectId(to_user_id)}, {"$set": {"seller_rating": round(score, 1)}})
    return True


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

    # Ratings come after the deal: only once both sides pressed Complete (FR-25)
    if transaction.get("status") != "completed":
        raise HTTPException(status_code=400, detail="You can rate once both of you have completed the transaction")

    recorded = await record_feedback(transaction, user["_id"], user["full_name"], target_id,
                                     feedback.rating, feedback.comment, feedback_type)
    if not recorded:
        raise HTTPException(status_code=400, detail="You have already left feedback for this transaction")
    
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
