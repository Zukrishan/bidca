from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.db import db
from app.security import get_current_user
from app.models import VerifyEmailRequest
from app.email_verification import hash_token, issue_verification_email, RESEND_COOLDOWN

router = APIRouter()


@router.post("/auth/verify-email")
async def verify_email(body: VerifyEmailRequest):
    """Public: the link may be opened on another device than the one that registered."""
    now_iso = datetime.now(timezone.utc).isoformat()
    record = await db.email_verifications.find_one_and_update(
        {"token_hash": hash_token(body.token), "used": False, "expires_at": {"$gt": now_iso}},
        {"$set": {"used": True}},
    )
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    await db.users.update_one({"_id": ObjectId(record["user_id"])}, {"$set": {"email_verified": True}})
    return {"message": "Email confirmed"}


@router.post("/auth/resend-verification")
async def resend_verification(user: dict = Depends(get_current_user)):
    if user.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Email already verified")
    last = await db.email_verifications.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    if last and datetime.fromisoformat(last["created_at"]) > datetime.now(timezone.utc) - RESEND_COOLDOWN:
        raise HTTPException(status_code=429, detail="Please wait a minute before requesting another email")
    await issue_verification_email(user["_id"], user["email"])
    return {"message": "Verification email sent"}
