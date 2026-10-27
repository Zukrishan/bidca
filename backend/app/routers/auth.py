from fastapi import APIRouter, HTTPException, Request, Response, Depends
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import jwt

from app.db import db
from app.security import (
    JWT_ALGORITHM, get_jwt_secret, hash_password, verify_password, create_access_token,
    create_refresh_token, increment_login_attempts, get_current_user,
    account_block_reason, set_auth_cookies, clear_auth_cookies,
)
from app.constants import is_valid_bc_postal_code, BC_CITIES
from app.models import UserLogin, UserRegister, PhoneSendCode, PhoneVerify
from app.helpers import calculate_positive_percentage
from app.email_verification import issue_verification_email
from app.accounts import (
    default_display_name, validate_display_name, validate_avatar_url, mark_active, check_session_activity,
    refresh_public_snapshots, phone_taken,
)
from app.captcha import require_captcha, captcha_site_key
from app.config import inactivity_logout
from app import phone as phone_codes

router = APIRouter()


def _client_ip(request: Request):
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else None)


# Public settings the sign-up/login pages and the idle timer need (contract D23)
@router.get("/auth/config")
async def auth_config():
    return {
        "captcha_site_key": captcha_site_key(),
        "inactivity_logout_minutes": inactivity_logout().total_seconds() / 60,
        "phone_verification": phone_codes.phone_mode(),
    }


# Auth endpoints
@router.post("/auth/register")
async def register(user_data: UserRegister, request: Request, response: Response):
    await require_captcha(user_data.captcha_token, _client_ip(request))
    email = user_data.email.lower()

    if not is_valid_bc_postal_code(user_data.postal_code):
        raise HTTPException(status_code=400, detail="Only British Columbia postal codes are accepted (starting with V)")
    if user_data.city not in BC_CITIES:
        raise HTTPException(status_code=400, detail="Choose your city from the list")
    if not user_data.age_confirmed_19_plus:
        raise HTTPException(status_code=400, detail="You must be 19 or older to use BidCa")
    if not user_data.terms_accepted:
        raise HTTPException(status_code=400, detail="Please accept the Terms and Conditions")
    phone = phone_codes.normalize_phone(user_data.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit phone number")
    display_name = (validate_display_name(user_data.display_name) if user_data.display_name
                    else default_display_name(user_data.full_name))
    avatar_url = validate_avatar_url(user_data.avatar_url) if user_data.avatar_url else None

    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if await phone_taken(phone):
        raise HTTPException(status_code=400, detail="This phone number is already used by another account")

    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "email": email,
        "password_hash": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "display_name": display_name,
        "city": user_data.city,
        "postal_code": user_data.postal_code.upper().replace(" ", ""),
        "province": user_data.province,
        "phone": phone,
        "phone_verified": False,
        "avatar_url": avatar_url,
        "age_confirmed_19_plus": True,
        "terms_accepted_at": now,
        "exchange_methods": [],
        "last_active_at": now,
        "role": "user",
        "email_verified": False,
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
        "created_at": now
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    set_auth_cookies(response, access_token, refresh_token)

    await issue_verification_email(user_id, email)
    
    return {
        "id": user_id,
        "email": email,
        "full_name": user_data.full_name,
        "display_name": display_name,
        "city": user_data.city,
        "phone": phone,
        "phone_verified": False,
        "avatar_url": avatar_url,
        "role": "user",
        "verification_status": "unverified",
        "email_verified": False,
    }

@router.post("/auth/login")
async def login(credentials: UserLogin, request: Request, response: Response):
    await require_captcha(credentials.captcha_token, _client_ip(request))
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
    await mark_active(user_id)  # a fresh session starts the inactivity clock again

    return {
        "id": user_id,
        "email": user["email"],
        "full_name": user["full_name"],
        "display_name": user.get("display_name") or default_display_name(user.get("full_name")),
        "city": user["city"],
        "phone": user.get("phone"),
        "phone_verified": user.get("phone_verified", False),
        "avatar_url": user.get("avatar_url"),
        "role": user["role"],
        "verification_status": user["verification_status"],
        "email_verified": user.get("email_verified", False),
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
        await check_session_activity(user)  # no refresh after INACTIVITY_LOGOUT_MINUTES idle (FR-02)
        access_token = create_access_token(str(user["_id"]), user["email"])
        set_auth_cookies(response, access_token)
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# Phone verification (FR-01): one account per verified phone number (contract D24)
PHONE_RESEND_AFTER = timedelta(seconds=60)
PHONE_MAX_SENDS_PER_HOUR = 5
PHONE_MAX_FAILS_PER_HOUR = 10


def _recent(times, window=timedelta(hours=1)):
    cutoff = (datetime.now(timezone.utc) - window).isoformat()
    return [t for t in (times or []) if t > cutoff]


@router.post("/auth/phone/send-code")
async def send_phone_code(body: PhoneSendCode, user: dict = Depends(get_current_user)):
    phone = phone_codes.normalize_phone(body.phone) if body.phone else user.get("phone")
    if body.phone and not phone:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit phone number")
    if not phone:
        raise HTTPException(status_code=400, detail="Add a phone number first")
    if phone == user.get("phone") and user.get("phone_verified"):
        raise HTTPException(status_code=400, detail="This phone number is already verified")
    if await phone_taken(phone, exclude_user_id=user["_id"]):
        raise HTTPException(status_code=400, detail="This phone number is already used by another account")

    state = await db.phone_verifications.find_one({"user_id": user["_id"]}) or {}
    sends = _recent(state.get("sends"))
    if sends and max(sends) > (datetime.now(timezone.utc) - PHONE_RESEND_AFTER).isoformat():
        raise HTTPException(status_code=429, detail="Please wait a minute before asking for another code")
    if len(sends) >= PHONE_MAX_SENDS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many codes requested. Try again later.")

    await phone_codes.send_code(phone)
    sends.append(datetime.now(timezone.utc).isoformat())
    await db.phone_verifications.update_one({"user_id": user["_id"]},
                                            {"$set": {"sends": sends, "phone": phone}}, upsert=True)
    if phone != user.get("phone"):
        # Changing the number drops any earlier verification
        await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {"phone": phone, "phone_verified": False}})
        await refresh_public_snapshots(user["_id"])
    return {"message": "Code sent", "phone": phone}


@router.post("/auth/phone/verify")
async def verify_phone(body: PhoneVerify, user: dict = Depends(get_current_user)):
    phone = user.get("phone")
    if not phone:
        raise HTTPException(status_code=400, detail="Add a phone number first")
    if user.get("phone_verified"):
        return {"message": "Phone number verified", "phone": phone, "phone_verified": True}
    state = await db.phone_verifications.find_one({"user_id": user["_id"]}) or {}
    fails = _recent(state.get("fails"))
    if len(fails) >= PHONE_MAX_FAILS_PER_HOUR:
        raise HTTPException(status_code=429, detail="Too many wrong codes. Try again later.")

    if not await phone_codes.check_code(phone, body.code):
        fails.append(datetime.now(timezone.utc).isoformat())
        await db.phone_verifications.update_one({"user_id": user["_id"]}, {"$set": {"fails": fails}}, upsert=True)
        raise HTTPException(status_code=400, detail="That code is not right or has expired")
    if await phone_taken(phone, exclude_user_id=user["_id"]):
        raise HTTPException(status_code=409, detail="This phone number is already verified on another account")

    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$set": {
        "phone_verified": True, "phone_verified_at": datetime.now(timezone.utc).isoformat()}})
    await db.phone_verifications.delete_one({"user_id": user["_id"]})
    await refresh_public_snapshots(user["_id"])
    return {"message": "Phone number verified", "phone": phone, "phone_verified": True}
