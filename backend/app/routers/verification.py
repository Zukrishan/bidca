from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import VerificationSubmit

router = APIRouter()


# Verification
@router.post("/verification/submit")
async def submit_verification(data: VerificationSubmit, user: dict = Depends(get_current_user)):
    if user["verification_status"] == "verified":
        raise HTTPException(status_code=400, detail="Already verified")
    
    verification_doc = {
        "user_id": user["_id"],
        "user_email": user["email"],
        "user_name": user["full_name"],
        "government_id_url": data.government_id_url,
        "selfie_url": data.selfie_url,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.verifications.insert_one(verification_doc)
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"verification_status": "pending"}})
    
    return {"message": "Verification submitted"}

@router.get("/verification/status")
async def get_verification_status(user: dict = Depends(get_current_user)):
    verification = await db.verifications.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    return {
        "verification_status": user["verification_status"],
        "verification_badge": user.get("verification_badge", False),
        "submission": verification if verification else None
    }
