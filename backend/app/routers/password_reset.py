from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import hashlib
import os
import secrets

from app.db import db
from app.security import hash_password
from app.models import ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter()


# Forgot / reset password
@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Always returns 200 to avoid user enumeration."""
    from app.email import send_email
    token_plain = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_plain.encode()).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    user = await db.users.find_one({"email": body.email.lower()})
    if user:
        # Store hashed token; invalidate any previous tokens for this user
        await db.password_reset_tokens.delete_many({"user_id": str(user["_id"])})
        await db.password_reset_tokens.insert_one({
            "user_id": str(user["_id"]),
            "token_hash": token_hash,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        reset_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3100')}/reset-password?token={token_plain}"
        await send_email(
            to=user["email"],
            subject="Reset your BidCa password",
            html=f"<p>Click the link to reset your password (valid 1 hour):</p><p><a href='{reset_url}'>{reset_url}</a></p>",
        )

    return {"message": "If that email is registered you will receive a reset link."}

@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    record = await db.password_reset_tokens.find_one({
        "token_hash": token_hash,
        "used": False,
        "expires_at": {"$gt": now_iso},
    })
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Mark single-use
    result = await db.password_reset_tokens.find_one_and_update(
        {"_id": record["_id"], "used": False},
        {"$set": {"used": True}},
        return_document=True,
    )
    if result is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    new_hash = hash_password(body.password)
    await db.users.update_one(
        {"_id": ObjectId(record["user_id"])},
        {"$set": {"password_hash": new_hash}},
    )
    return {"message": "Password reset successfully"}
