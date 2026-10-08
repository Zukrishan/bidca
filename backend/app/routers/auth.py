from fastapi import APIRouter, HTTPException, Request, Response, Depends
from datetime import datetime, timezone
from bson import ObjectId
import jwt

from app.db import db
from app.security import (
    JWT_ALGORITHM, get_jwt_secret, hash_password, verify_password, create_access_token,
    create_refresh_token, increment_login_attempts, get_current_user,
    account_block_reason, set_auth_cookies, clear_auth_cookies,
)
from app.constants import is_valid_bc_postal_code
from app.models import UserLogin, UserRegister
from app.helpers import calculate_positive_percentage

router = APIRouter()


# Auth endpoints
@router.post("/auth/register")
async def register(user_data: UserRegister, response: Response):
    email = user_data.email.lower()
    
    if not is_valid_bc_postal_code(user_data.postal_code):
        raise HTTPException(status_code=400, detail="Only British Columbia postal codes are accepted (starting with V)")
    
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "city": user_data.city,
        "postal_code": user_data.postal_code.upper().replace(" ", ""),
        "province": user_data.province,
        "role": "user",
        "verification_status": "unverified",
        "verification_badge": False,
        "is_suspended": False,
        "is_banned": False,
        # Seller stats
        "seller_rating": 0,
        "total_ratings": 0,
        "positive_ratings": 0,
        "neutral_ratings": 0,
        "negative_ratings": 0,
        "total_sales": 0,
        "total_sales_amount": 0,
        # Buyer stats
        "total_purchases": 0,
        "total_bids_placed": 0,
        "auctions_won": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    set_auth_cookies(response, access_token, refresh_token)
    
    return {
        "id": user_id,
        "email": email,
        "full_name": user_data.full_name,
        "city": user_data.city,
        "role": "user",
        "verification_status": "unverified"
    }

@router.post("/auth/login")
async def login(credentials: UserLogin, response: Response):
    email = credentials.email.lower()
    
    identifier = email  # Use email only for rate limiting (proxy IPs may vary)
    
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts and attempts.get("count", 0) >= 5:
        lockout_time = attempts.get("locked_until")
        if lockout_time and datetime.fromisoformat(lockout_time) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    
    user = await db.users.find_one({"email": email})
    if not user:
        new_count = await increment_login_attempts(identifier)
        if new_count >= 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user["password_hash"]):
        new_count = await increment_login_attempts(identifier)
        if new_count >= 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await db.login_attempts.delete_one({"identifier": identifier})

    # Only after the password checks out, so account state isn't revealed to guessers
    blocked = account_block_reason(user)
    if blocked:
        raise HTTPException(status_code=403, detail=blocked)
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    set_auth_cookies(response, access_token, refresh_token)
    
    return {
        "id": user_id,
        "email": user["email"],
        "full_name": user["full_name"],
        "city": user["city"],
        "role": user["role"],
        "verification_status": user["verification_status"],
        "verification_badge": user.get("verification_badge", False),
        "seller_rating": user.get("seller_rating", 0),
        "total_ratings": user.get("total_ratings", 0),
        "positive_percentage": calculate_positive_percentage(user)
    }

@router.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        blocked = account_block_reason(user)
        if blocked:
            raise HTTPException(status_code=403, detail=blocked)
        access_token = create_access_token(str(user["_id"]), user["email"])
        set_auth_cookies(response, access_token)
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
