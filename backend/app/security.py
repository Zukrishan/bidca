import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, Request, Response

from app.config import login_lockout
from app.db import db

# JWT Configuration
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

# Password hashing
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# JWT Token Management
def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=60), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

# Auth helper
def account_block_reason(user: dict) -> Optional[str]:
    """Why this account may not use the site, or None. Checked on login, every request and refresh."""
    if user.get("is_banned"):
        return "Account has been banned"
    if user.get("is_suspended"):
        return "Account has been suspended"
    return None

async def user_from_access_token(token: str) -> dict:
    """Resolve an access token to an active user (no password_hash). Raises HTTPException 401/403."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Bans and suspensions take effect immediately, not when the token expires (backlog B3)
    blocked = account_block_reason(user)
    if blocked:
        raise HTTPException(status_code=403, detail=blocked)
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return user

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await user_from_access_token(token)

async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_verified_email(request: Request) -> dict:
    """get_current_user, plus a confirmed email address (FR-04). A missing flag counts as unverified."""
    user = await get_current_user(request)
    if not user.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email address to continue")
    return user

async def increment_login_attempts(identifier: str) -> int:
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts:
        new_count = attempts.get("count", 0) + 1
        update = {"$set": {"count": new_count}}
        if new_count >= 5:
            update["$set"]["locked_until"] = (datetime.now(timezone.utc) + login_lockout()).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, update)
        return new_count
    else:
        await db.login_attempts.insert_one({"identifier": identifier, "count": 1})
        return 1

# Auth cookies (contract D5). Secure by default in production (backlog B10); COOKIE_SECURE=true|false overrides.
ACCESS_TOKEN_MAX_AGE = 3600
REFRESH_TOKEN_MAX_AGE = 604800

def cookies_secure() -> bool:
    # Empty counts as unset: docker compose passes COOKIE_SECURE="" when .env leaves it blank
    explicit = os.environ.get("COOKIE_SECURE", "").strip()
    if explicit:
        return explicit.lower() in ("1", "true", "yes")
    return os.environ.get("ENV", "").lower() == "production"

def set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None) -> None:
    secure = cookies_secure()
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=secure,
                        samesite="lax", max_age=ACCESS_TOKEN_MAX_AGE, path="/")
    if refresh_token:
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=secure,
                            samesite="lax", max_age=REFRESH_TOKEN_MAX_AGE, path="/")

def clear_auth_cookies(response: Response) -> None:
    secure = cookies_secure()
    for key in ("access_token", "refresh_token"):
        response.delete_cookie(key, path="/", secure=secure, httponly=True, samesite="lax")
