from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import socketio
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import secrets
import hashlib
import cloudinary
import cloudinary.utils
import time
from bson import ObjectId
import asyncio
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Cloudinary configuration — only configured when env vars are present
_cld_cloud = os.getenv("CLOUDINARY_CLOUD_NAME")
_cld_key = os.getenv("CLOUDINARY_API_KEY")
_cld_secret = os.getenv("CLOUDINARY_API_SECRET")
if _cld_cloud and _cld_key and _cld_secret:
    cloudinary.config(
        cloud_name=_cld_cloud,
        api_key=_cld_key,
        api_secret=_cld_secret,
        secure=True,
    )

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
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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

# BC Postal Code Validation
BC_POSTAL_PREFIXES = ['V']

def is_valid_bc_postal_code(postal_code: str) -> bool:
    if not postal_code:
        return False
    cleaned = postal_code.upper().replace(" ", "")
    if len(cleaned) != 6:
        return False
    return cleaned[0] in BC_POSTAL_PREFIXES

# Canadian Provinces
PROVINCES = [
    "British Columbia", "Alberta", "Saskatchewan", "Manitoba", "Ontario",
    "Quebec", "New Brunswick", "Nova Scotia", "Prince Edward Island",
    "Newfoundland and Labrador", "Yukon", "Northwest Territories", "Nunavut"
]

# BC Cities
BC_CITIES = [
    "Vancouver", "Victoria", "Surrey", "Burnaby", "Richmond", "Abbotsford",
    "Coquitlam", "Kelowna", "Langley", "Saanich", "Delta", "Kamloops",
    "Nanaimo", "North Vancouver", "Chilliwack", "Maple Ridge", "New Westminster",
    "Prince George", "Port Coquitlam", "Vernon", "Courtenay", "Penticton",
    "Campbell River", "Mission", "West Vancouver", "Langford", "White Rock"
]

# Categories with subcategories
CATEGORIES = {
    "Electronics": ["Computers", "Smartphones", "Tablets", "Cameras", "Audio", "Gaming", "Accessories"],
    "Vehicles": ["Cars", "Motorcycles", "Boats", "RVs", "Parts & Accessories"],
    "Collectibles & Art": ["Antiques", "Coins", "Stamps", "Trading Cards", "Art", "Memorabilia"],
    "Fashion": ["Men's Clothing", "Women's Clothing", "Shoes", "Bags", "Watches", "Jewelry"],
    "Home & Garden": ["Furniture", "Appliances", "Decor", "Tools", "Outdoor", "Kitchen"],
    "Sports & Outdoors": ["Fitness", "Cycling", "Camping", "Fishing", "Golf", "Winter Sports"],
    "Toys & Games": ["Action Figures", "Board Games", "Video Games", "Dolls", "LEGO"],
    "Books & Media": ["Books", "Music", "Movies", "Magazines"],
    "Jewelry & Watches": ["Fine Jewelry", "Fashion Jewelry", "Luxury Watches", "Vintage"],
    "Musical Instruments": ["Guitars", "Pianos", "Drums", "Wind", "DJ Equipment"],
    "Tools & Equipment": ["Power Tools", "Hand Tools", "Industrial", "Safety Equipment"],
    "Other": ["Miscellaneous"]
}

# Bid Increments based on current price
def get_bid_increment(current_price: float) -> float:
    if current_price < 25:
        return 1
    elif current_price < 100:
        return 5
    elif current_price < 250:
        return 10
    elif current_price < 500:
        return 25
    elif current_price < 1000:
        return 50
    elif current_price < 2500:
        return 100
    elif current_price < 5000:
        return 250
    else:
        return 500

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    city: str
    postal_code: str
    province: str = "British Columbia"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AuctionCreate(BaseModel):
    title: str
    category: str
    subcategory: Optional[str] = None
    description: str
    city: str
    province: str = "British Columbia"
    starting_bid: float
    reserve_price: Optional[float] = None
    buy_it_now_price: Optional[float] = None
    duration_days: Literal[1, 3, 5, 7, 10] = 7
    images: List[str] = []
    condition: Literal["new", "like_new", "good", "fair", "poor"] = "good"
    shipping_cost: float = 0
    shipping_from: str = "British Columbia"
    accepts_best_offer: bool = False
    listing_type: Literal["auction", "fixed_price", "auction_bin"] = "auction"

class BidCreate(BaseModel):
    max_bid: float  # Proxy bidding - user's maximum bid

class SniperBidCreate(BaseModel):
    max_bid: float
    minutes_before_end: Literal[1, 2, 3, 5, 10] = 5

class BestOfferCreate(BaseModel):
    offer_amount: float
    message: Optional[str] = None

class FeedbackCreate(BaseModel):
    rating: Literal["positive", "neutral", "negative"]
    comment: str

class SavedSearchCreate(BaseModel):
    name: str
    query: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

class ListingUpdate(BaseModel):
    status: Optional[Literal["pending", "approved", "rejected", "active", "ended", "sold", "unsold"]] = None

class UserUpdate(BaseModel):
    verification_status: Optional[Literal["unverified", "pending", "verified"]] = None
    is_suspended: Optional[bool] = None
    is_banned: Optional[bool] = None

class VerificationSubmit(BaseModel):
    government_id_url: str
    selfie_url: str

class ReportCreate(BaseModel):
    reason: str
    description: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI(title="BidCa.ca API - Full Auction Platform")

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def join_auction(sid, data):
    auction_id = data.get("auction_id")
    if auction_id:
        await sio.enter_room(sid, f"auction_{auction_id}")
        logger.info(f"Client {sid} joined auction room {auction_id}")

@sio.event
async def leave_auction(sid, data):
    auction_id = data.get("auction_id")
    if auction_id:
        await sio.leave_room(sid, f"auction_{auction_id}")

@sio.event
async def join_user_notifications(sid, data):
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, f"user_{user_id}")

async def broadcast_bid_update(auction_id: str, bid_data: dict):
    await sio.emit('bid_update', bid_data, room=f"auction_{auction_id}")

async def broadcast_auction_end(auction_id: str, data: dict):
    await sio.emit('auction_ended', data, room=f"auction_{auction_id}")

async def send_user_notification(user_id: str, notification: dict):
    await sio.emit('notification', notification, room=f"user_{user_id}")

# Create API router
api_router = APIRouter(prefix="/api")

# Health check
@api_router.get("/")
async def root():
    return {"message": "BidCa.ca API - Full Auction Platform", "status": "running"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# Auth endpoints
@api_router.post("/auth/register")
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
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "full_name": user_data.full_name,
        "city": user_data.city,
        "role": "user",
        "verification_status": "unverified"
    }

@api_router.post("/auth/login")
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
    
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Account has been banned")
    
    if user.get("is_suspended"):
        raise HTTPException(status_code=403, detail="Account has been suspended")
    
    if not verify_password(credentials.password, user["password_hash"]):
        new_count = await increment_login_attempts(identifier)
        if new_count >= 5:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    await db.login_attempts.delete_one({"identifier": identifier})
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
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

def calculate_positive_percentage(user: dict) -> float:
    total = user.get("total_ratings", 0)
    if total == 0:
        return 100.0
    positive = user.get("positive_ratings", 0)
    return round((positive / total) * 100, 1)

async def increment_login_attempts(identifier: str) -> int:
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts:
        new_count = attempts.get("count", 0) + 1
        update = {"$set": {"count": new_count}}
        if new_count >= 5:
            update["$set"]["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, update)
        return new_count
    else:
        await db.login_attempts.insert_one({"identifier": identifier, "count": 1})
        return 1

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@api_router.post("/auth/refresh")
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
        access_token = create_access_token(str(user["_id"]), user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# Forgot / reset password
@api_router.post("/auth/forgot-password")
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

@api_router.post("/auth/reset-password")
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

# Cloudinary signature
@api_router.get("/cloudinary/signature")
async def get_cloudinary_signature(
    resource_type: str = Query("image", enum=["image", "video"]),
    folder: str = "bidca_uploads",
    user: dict = Depends(get_current_user)
):
    cld_cloud = os.getenv("CLOUDINARY_CLOUD_NAME")
    cld_key = os.getenv("CLOUDINARY_API_KEY")
    cld_secret = os.getenv("CLOUDINARY_API_SECRET")
    if not (cld_cloud and cld_key and cld_secret):
        raise HTTPException(status_code=503, detail="Cloudinary is not configured")
    timestamp = int(time.time())
    params = {"timestamp": timestamp, "folder": folder, "resource_type": resource_type}
    signature = cloudinary.utils.api_sign_request(params, cld_secret)
    return {
        "signature": signature,
        "timestamp": timestamp,
        "cloud_name": cld_cloud,
        "api_key": cld_key,
        "folder": folder,
        "resource_type": resource_type
    }

# Categories
@api_router.get("/categories")
async def get_categories():
    return {"categories": CATEGORIES}

@api_router.get("/cities")
async def get_cities():
    return {"cities": BC_CITIES}

@api_router.get("/provinces")
async def get_provinces():
    return {"provinces": PROVINCES}

# Popular search keywords
@api_router.get("/popular-keywords")
async def get_popular_keywords():
    # In production, this would be based on actual search analytics
    keywords = [
        "iPhone", "PS5", "MacBook", "Nintendo Switch", "AirPods",
        "Vintage Watch", "Hockey Cards", "Mountain Bike", "Camera",
        "Antique Furniture", "Gold Coins", "Electric Guitar"
    ]
    return {"keywords": keywords}

# Listings/Auctions
@api_router.post("/listings", status_code=201)
async def create_listing(listing: AuctionCreate, user: dict = Depends(get_current_user)):
    # Validate reserve price
    if listing.reserve_price and listing.reserve_price < listing.starting_bid:
        raise HTTPException(status_code=400, detail="Reserve price must be higher than starting bid")
    
    # Validate BIN price
    if listing.buy_it_now_price and listing.buy_it_now_price <= listing.starting_bid:
        raise HTTPException(status_code=400, detail="Buy It Now price must be higher than starting bid")
    
    end_time = datetime.now(timezone.utc) + timedelta(days=listing.duration_days)
    
    listing_doc = {
        "title": listing.title,
        "category": listing.category,
        "subcategory": listing.subcategory,
        "description": listing.description,
        "city": listing.city,
        "province": listing.province,
        "images": listing.images,
        "condition": listing.condition,
        "listing_type": listing.listing_type,
        # Pricing
        "starting_bid": listing.starting_bid,
        "current_bid": listing.starting_bid,
        "reserve_price": listing.reserve_price,
        "reserve_met": False if listing.reserve_price else True,
        "buy_it_now_price": listing.buy_it_now_price,
        "accepts_best_offer": listing.accepts_best_offer,
        # Shipping
        "shipping_cost": listing.shipping_cost,
        "shipping_from": listing.shipping_from,
        # Timing
        "duration_days": listing.duration_days,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": end_time.isoformat(),
        # Seller info
        "seller_id": user["_id"],
        "seller_name": user["full_name"],
        "seller_city": user["city"],
        "seller_verified": user.get("verification_badge", False),
        "seller_rating": user.get("seller_rating", 0),
        "seller_total_ratings": user.get("total_ratings", 0),
        "seller_positive_pct": calculate_positive_percentage(user),
        # Bidding
        "bid_count": 0,
        "bid_increment": get_bid_increment(listing.starting_bid),
        "highest_bidder_id": None,
        "highest_bidder_name": None,
        "highest_bidder_max_bid": None,  # For proxy bidding
        # Status
        "status": "pending",
        "winner_id": None,
        "sold_price": None,
        "watchers_count": 0,
        "views_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.listings.insert_one(listing_doc)
    listing_doc["_id"] = str(result.inserted_id)
    listing_doc["seller_id"] = str(listing_doc["seller_id"])
    
    return listing_doc

@api_router.get("/listings")
async def get_listings(
    q: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    condition: Optional[str] = None,
    province: Optional[str] = None,
    city: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    listing_type: Optional[str] = None,
    seller_rating: Optional[float] = None,
    free_shipping: Optional[bool] = None,
    status: str = "active",
    sort: str = "ending_soonest",
    page: int = 1,
    limit: int = 24
):
    query = {"status": status}
    
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}}
        ]
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    if condition:
        query["condition"] = condition
    if province:
        query["province"] = province
    if city:
        query["city"] = city
    if min_price is not None:
        query["current_bid"] = {"$gte": min_price}
    if max_price is not None:
        query["current_bid"] = {**query.get("current_bid", {}), "$lte": max_price}
    if listing_type:
        query["listing_type"] = listing_type
    if seller_rating:
        query["seller_rating"] = {"$gte": seller_rating}
    if free_shipping:
        query["shipping_cost"] = 0
    
    # Sorting
    sort_options = {
        "ending_soonest": [("end_time", 1)],
        "newly_listed": [("created_at", -1)],
        "lowest_price": [("current_bid", 1)],
        "highest_price": [("current_bid", -1)],
        "most_bids": [("bid_count", -1)]
    }
    sort_order = sort_options.get(sort, [("end_time", 1)])
    
    skip = (page - 1) * limit
    cursor = db.listings.find(query).sort(sort_order).skip(skip).limit(limit)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        listings.append(doc)
    
    total = await db.listings.count_documents(query)
    
    return {
        "listings": listings,
        "total": total,
        "page": page,
        "pages": math.ceil(total / limit) if total > 0 else 1
    }

@api_router.get("/listings/featured")
async def get_featured_listings():
    # Get popular auctions (most bids, ending soon)
    cursor = db.listings.find(
        {"status": "active", "listing_type": {"$in": ["auction", "auction_bin"]}}
    ).sort([("bid_count", -1), ("end_time", 1)]).limit(8)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        listings.append(doc)
    
    return {"listings": listings}

@api_router.get("/listings/ending-soon")
async def get_ending_soon():
    # Auctions ending in next 6 hours
    cutoff = datetime.now(timezone.utc) + timedelta(hours=6)
    cursor = db.listings.find(
        {
            "status": "active",
            "listing_type": {"$in": ["auction", "auction_bin"]},
            "end_time": {"$lte": cutoff.isoformat()}
        }
    ).sort("end_time", 1).limit(12)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        listings.append(doc)
    
    return {"listings": listings}

@api_router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, request: Request):
    user = await get_optional_user(request)
    
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Increment view count
    await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"views_count": 1}})
    
    listing["_id"] = str(listing["_id"])
    listing["seller_id"] = str(listing["seller_id"])
    
    # Get bid history (masked usernames for non-sellers)
    bids_cursor = db.bids.find({"listing_id": listing_id}).sort("created_at", -1).limit(50)
    bids = []
    async for bid in bids_cursor:
        bidder_name = bid["bidder_name"]
        # Mask username unless user is the seller or the bidder
        if user and (listing["seller_id"] == user["_id"] or bid["bidder_id"] == user["_id"]):
            masked_name = bidder_name
        else:
            masked_name = bidder_name[:1] + "***" + bidder_name[-1:] if len(bidder_name) > 2 else "***"
        bids.append({
            "amount": bid["amount"],
            "bidder_name": masked_name,
            "created_at": bid["created_at"],
            "is_auto_bid": bid.get("is_auto_bid", False)
        })
    
    listing["bid_history"] = bids
    
    # Check if user is watching
    if user:
        watching = await db.watchlist.find_one({"user_id": user["_id"], "listing_id": listing_id})
        listing["is_watching"] = watching is not None
        listing["is_seller"] = listing["seller_id"] == user["_id"]
    else:
        listing["is_watching"] = False
        listing["is_seller"] = False
    
    # Get related items
    related_cursor = db.listings.find(
        {"category": listing["category"], "status": "active", "_id": {"$ne": ObjectId(listing_id)}}
    ).limit(6)
    related = []
    async for doc in related_cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        related.append(doc)
    listing["related_items"] = related
    
    # Get seller info
    seller = await db.users.find_one({"_id": ObjectId(listing["seller_id"])})
    if seller:
        listing["seller_info"] = {
            "full_name": seller["full_name"],
            "city": seller["city"],
            "seller_rating": seller.get("seller_rating", 0),
            "total_ratings": seller.get("total_ratings", 0),
            "positive_percentage": calculate_positive_percentage(seller),
            "verification_badge": seller.get("verification_badge", False),
            "total_sales": seller.get("total_sales", 0),
            "member_since": seller.get("created_at")
        }
    
    return listing

# Proxy Bidding System
@api_router.post("/listings/{listing_id}/bid")
async def place_bid(listing_id: str, bid: BidCreate, user: dict = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This auction is not active")
    
    if listing["listing_type"] == "fixed_price":
        raise HTTPException(status_code=400, detail="This is a fixed-price listing")
    
    # Check if auction has ended
    end_time = datetime.fromisoformat(listing["end_time"])
    if datetime.now(timezone.utc) > end_time:
        raise HTTPException(status_code=400, detail="This auction has ended")
    
    # Check seller can't bid on own auction
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
    current_bid = listing["current_bid"]
    bid_increment = get_bid_increment(current_bid)
    min_bid = current_bid + bid_increment if listing["bid_count"] > 0 else current_bid
    
    if bid.max_bid < min_bid:
        raise HTTPException(status_code=400, detail=f"Minimum bid is ${min_bid:.2f}")
    
    # Proxy bidding logic
    current_max_bid = listing.get("highest_bidder_max_bid", 0) or 0
    current_highest_bidder = listing.get("highest_bidder_id")
    
    if current_highest_bidder and str(current_highest_bidder) == user["_id"]:
        # User is already highest bidder, just update their max
        if bid.max_bid <= current_max_bid:
            raise HTTPException(status_code=400, detail="Your new maximum must be higher than your current maximum bid")
        
        await db.listings.update_one(
            {"_id": ObjectId(listing_id)},
            {"$set": {"highest_bidder_max_bid": bid.max_bid}}
        )
        return {"message": "Maximum bid updated", "current_bid": current_bid, "your_max_bid": bid.max_bid}
    
    # Calculate new current bid
    if current_max_bid > 0:
        if bid.max_bid > current_max_bid:
            # New bidder wins, set price to previous max + increment
            new_current_bid = min(current_max_bid + bid_increment, bid.max_bid)
            new_highest_bidder = user["_id"]
            new_max_bid = bid.max_bid
            
            # Notify outbid user
            if current_highest_bidder:
                await create_notification(
                    str(current_highest_bidder),
                    "outbid",
                    f"You've been outbid on '{listing['title']}'! Current bid: ${new_current_bid:.2f}",
                    listing_id
                )
        else:
            # Current bidder stays, auto-bid up to new bid
            new_current_bid = min(bid.max_bid + bid_increment, current_max_bid)
            new_highest_bidder = current_highest_bidder
            new_max_bid = current_max_bid
            
            # Notify the new bidder they were outbid immediately
            await create_notification(
                user["_id"],
                "outbid",
                f"You were outbid on '{listing['title']}'. Current bid: ${new_current_bid:.2f}",
                listing_id
            )
    else:
        new_current_bid = listing["starting_bid"]
        new_highest_bidder = user["_id"]
        new_max_bid = bid.max_bid
    
    # Check reserve price
    reserve_met = True
    if listing.get("reserve_price"):
        reserve_met = new_current_bid >= listing["reserve_price"]
    
    # Create bid record
    bid_doc = {
        "listing_id": listing_id,
        "bidder_id": user["_id"],
        "bidder_name": user["full_name"],
        "amount": new_current_bid,
        "max_bid": bid.max_bid,
        "is_auto_bid": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bids.insert_one(bid_doc)
    
    # Update listing
    new_bid_increment = get_bid_increment(new_current_bid)
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "current_bid": new_current_bid,
                "bid_increment": new_bid_increment,
                "highest_bidder_id": new_highest_bidder,
                "highest_bidder_name": user["full_name"] if str(new_highest_bidder) == user["_id"] else listing.get("highest_bidder_name"),
                "highest_bidder_max_bid": new_max_bid,
                "reserve_met": reserve_met
            },
            "$inc": {"bid_count": 1}
        }
    )
    
    # Update user stats
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$inc": {"total_bids_placed": 1}})
    
    # Broadcast bid update
    await broadcast_bid_update(listing_id, {
        "listing_id": listing_id,
        "current_bid": new_current_bid,
        "bid_count": listing["bid_count"] + 1,
        "bid_increment": new_bid_increment,
        "reserve_met": reserve_met,
        "bidder_name": user["full_name"][:1] + "***"
    })
    
    return {
        "message": "Bid placed successfully",
        "current_bid": new_current_bid,
        "your_max_bid": bid.max_bid,
        "is_winning": str(new_highest_bidder) == user["_id"],
        "reserve_met": reserve_met
    }

# Sniper Bid
@api_router.post("/listings/{listing_id}/sniper-bid")
async def create_sniper_bid(listing_id: str, sniper: SniperBidCreate, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing or listing["status"] != "active":
        raise HTTPException(status_code=400, detail="Listing not available")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
    end_time = datetime.fromisoformat(listing["end_time"])
    execute_time = end_time - timedelta(minutes=sniper.minutes_before_end)
    
    if execute_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Sniper bid time has already passed")
    
    sniper_doc = {
        "listing_id": listing_id,
        "user_id": user["_id"],
        "max_bid": sniper.max_bid,
        "minutes_before_end": sniper.minutes_before_end,
        "execute_at": execute_time.isoformat(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sniper_bids.insert_one(sniper_doc)
    
    return {"message": f"Sniper bid scheduled for {sniper.minutes_before_end} minutes before auction end"}

# Buy It Now
@api_router.post("/listings/{listing_id}/buy-now")
async def buy_it_now(listing_id: str, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This listing is not active")
    
    if not listing.get("buy_it_now_price"):
        raise HTTPException(status_code=400, detail="This listing does not have a Buy It Now option")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot buy your own listing")
    
    bin_price = listing["buy_it_now_price"]
    
    # End auction immediately
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "status": "sold",
                "winner_id": user["_id"],
                "sold_price": bin_price,
                "end_time": datetime.now(timezone.utc).isoformat(),
                "sold_via": "buy_it_now"
            }
        }
    )
    
    # Create transaction record
    transaction = {
        "listing_id": listing_id,
        "seller_id": str(listing["seller_id"]),
        "buyer_id": user["_id"],
        "amount": bin_price,
        "type": "buy_it_now",
        "status": "pending_payment",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(transaction)
    
    # Notify seller
    await create_notification(
        str(listing["seller_id"]),
        "item_sold",
        f"Your item '{listing['title']}' was sold via Buy It Now for ${bin_price:.2f}!",
        listing_id
    )
    
    # Update stats
    await db.users.update_one({"_id": ObjectId(user["_id"])}, {"$inc": {"total_purchases": 1, "auctions_won": 1}})
    await db.users.update_one(
        {"_id": listing["seller_id"]},
        {"$inc": {"total_sales": 1, "total_sales_amount": bin_price}}
    )
    
    # Broadcast auction end
    await broadcast_auction_end(listing_id, {"listing_id": listing_id, "sold_via": "buy_it_now", "price": bin_price})
    
    return {"message": "Purchase successful!", "price": bin_price}

# Best Offer
@api_router.post("/listings/{listing_id}/best-offer")
async def submit_best_offer(listing_id: str, offer: BestOfferCreate, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing or not listing.get("accepts_best_offer"):
        raise HTTPException(status_code=400, detail="This listing does not accept offers")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot make an offer on your own listing")
    
    offer_doc = {
        "listing_id": listing_id,
        "buyer_id": user["_id"],
        "buyer_name": user["full_name"],
        "amount": offer.offer_amount,
        "message": offer.message,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.offers.insert_one(offer_doc)
    
    # Notify seller
    await create_notification(
        str(listing["seller_id"]),
        "new_offer",
        f"New offer of ${offer.offer_amount:.2f} on '{listing['title']}'",
        listing_id
    )
    
    return {"message": "Offer submitted", "offer_id": str(result.inserted_id)}

@api_router.put("/offers/{offer_id}/respond")
async def respond_to_offer(
    offer_id: str,
    action: Literal["accept", "decline", "counter"],
    counter_amount: Optional[float] = None,
    user: dict = Depends(get_current_user)
):
    try:
        offer = await db.offers.find_one({"_id": ObjectId(offer_id)})
    except:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    listing = await db.listings.find_one({"_id": ObjectId(offer["listing_id"])})
    if str(listing["seller_id"]) != user["_id"]:
        raise HTTPException(status_code=403, detail="Only the seller can respond to offers")
    
    if action == "accept":
        # Accept offer and end listing
        await db.offers.update_one({"_id": ObjectId(offer_id)}, {"$set": {"status": "accepted"}})
        await db.listings.update_one(
            {"_id": ObjectId(offer["listing_id"])},
            {
                "$set": {
                    "status": "sold",
                    "winner_id": offer["buyer_id"],
                    "sold_price": offer["amount"],
                    "sold_via": "best_offer"
                }
            }
        )
        
        await create_notification(
            offer["buyer_id"],
            "offer_accepted",
            f"Your offer of ${offer['amount']:.2f} was accepted!",
            offer["listing_id"]
        )
        
    elif action == "decline":
        await db.offers.update_one({"_id": ObjectId(offer_id)}, {"$set": {"status": "declined"}})
        await create_notification(
            offer["buyer_id"],
            "offer_declined",
            f"Your offer of ${offer['amount']:.2f} was declined",
            offer["listing_id"]
        )
        
    elif action == "counter":
        if not counter_amount:
            raise HTTPException(status_code=400, detail="Counter amount required")
        await db.offers.update_one(
            {"_id": ObjectId(offer_id)},
            {"$set": {"status": "countered", "counter_amount": counter_amount}}
        )
        await create_notification(
            offer["buyer_id"],
            "counter_offer",
            f"Seller countered with ${counter_amount:.2f}",
            offer["listing_id"]
        )
    
    return {"message": f"Offer {action}ed"}

# Watchlist
@api_router.post("/listings/{listing_id}/watch")
async def watch_listing(listing_id: str, user: dict = Depends(get_current_user)):
    existing = await db.watchlist.find_one({"user_id": user["_id"], "listing_id": listing_id})
    
    if existing:
        # Remove from watchlist
        await db.watchlist.delete_one({"_id": existing["_id"]})
        await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"watchers_count": -1}})
        return {"watching": False, "message": "Removed from watchlist"}
    else:
        # Add to watchlist
        await db.watchlist.insert_one({
            "user_id": user["_id"],
            "listing_id": listing_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        await db.listings.update_one({"_id": ObjectId(listing_id)}, {"$inc": {"watchers_count": 1}})
        return {"watching": True, "message": "Added to watchlist"}

@api_router.get("/users/me/watchlist")
async def get_watchlist(user: dict = Depends(get_current_user)):
    cursor = db.watchlist.find({"user_id": user["_id"]}).sort("created_at", -1)
    
    items = []
    async for watch in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(watch["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            items.append(listing)
    
    return {"watchlist": items}

# Saved Searches
@api_router.post("/saved-searches")
async def create_saved_search(search: SavedSearchCreate, user: dict = Depends(get_current_user)):
    search_doc = {
        "user_id": user["_id"],
        "name": search.name,
        "query": search.query,
        "category": search.category,
        "min_price": search.min_price,
        "max_price": search.max_price,
        "notify": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.saved_searches.insert_one(search_doc)
    return {"message": "Search saved", "id": str(result.inserted_id)}

@api_router.get("/saved-searches")
async def get_saved_searches(user: dict = Depends(get_current_user)):
    cursor = db.saved_searches.find({"user_id": user["_id"]})
    searches = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        searches.append(s)
    return {"saved_searches": searches}

@api_router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str, user: dict = Depends(get_current_user)):
    await db.saved_searches.delete_one({"_id": ObjectId(search_id), "user_id": user["_id"]})
    return {"message": "Search deleted"}

# Feedback System
@api_router.post("/transactions/{transaction_id}/feedback")
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

@api_router.get("/users/{user_id}/feedback")
async def get_user_feedback(user_id: str, page: int = 1, limit: int = 20):
    skip = (page - 1) * limit
    cursor = db.feedback.find({"to_user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    
    feedbacks = []
    async for f in cursor:
        f["_id"] = str(f["_id"])
        feedbacks.append(f)
    
    total = await db.feedback.count_documents({"to_user_id": user_id})
    
    return {"feedback": feedbacks, "total": total}

# User Dashboard
@api_router.get("/users/me/bids")
async def get_my_bids(user: dict = Depends(get_current_user)):
    cursor = db.bids.find({"bidder_id": user["_id"]}).sort("created_at", -1)
    
    bids_by_listing = {}
    async for bid in cursor:
        if bid["listing_id"] not in bids_by_listing:
            listing = await db.listings.find_one({"_id": ObjectId(bid["listing_id"])})
            if listing:
                listing["_id"] = str(listing["_id"])
                listing["seller_id"] = str(listing["seller_id"])
                listing["my_max_bid"] = bid.get("max_bid", bid.get("amount", 0))
                listing["is_winning"] = str(listing.get("highest_bidder_id")) == user["_id"]
                bids_by_listing[bid["listing_id"]] = listing
    
    return {"bids": list(bids_by_listing.values())}

@api_router.get("/users/me/listings")
async def get_my_listings(user: dict = Depends(get_current_user), status: Optional[str] = None):
    query = {"seller_id": user["_id"]}
    if status:
        query["status"] = status
    
    cursor = db.listings.find(query).sort("created_at", -1)
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["seller_id"] = str(doc["seller_id"])
        listings.append(doc)
    
    return {"listings": listings}

@api_router.get("/users/me/purchases")
async def get_my_purchases(user: dict = Depends(get_current_user)):
    cursor = db.transactions.find({"buyer_id": user["_id"]}).sort("created_at", -1)
    
    purchases = []
    async for t in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(t["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            t["listing"] = listing
            t["_id"] = str(t["_id"])
            purchases.append(t)
    
    return {"purchases": purchases}

@api_router.get("/users/me/sales")
async def get_my_sales(user: dict = Depends(get_current_user)):
    cursor = db.transactions.find({"seller_id": user["_id"]}).sort("created_at", -1)
    
    sales = []
    async for t in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(t["listing_id"])})
        if listing:
            listing["_id"] = str(listing["_id"])
            listing["seller_id"] = str(listing["seller_id"])
            t["listing"] = listing
            t["_id"] = str(t["_id"])
            
            # Get buyer info
            buyer = await db.users.find_one({"_id": ObjectId(t["buyer_id"])})
            if buyer:
                t["buyer_name"] = buyer["full_name"]
            sales.append(t)
    
    return {"sales": sales}

# Seller Dashboard Stats
@api_router.get("/users/me/seller-stats")
async def get_seller_stats(user: dict = Depends(get_current_user)):
    active_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "active"})
    pending_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "pending"})
    sold_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "sold"})
    unsold_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "unsold"})
    
    # Total watchers on active listings
    pipeline = [
        {"$match": {"seller_id": user["_id"], "status": "active"}},
        {"$group": {"_id": None, "total_watchers": {"$sum": "$watchers_count"}, "total_views": {"$sum": "$views_count"}}}
    ]
    result = await db.listings.aggregate(pipeline).to_list(1)
    watchers = result[0]["total_watchers"] if result else 0
    views = result[0]["total_views"] if result else 0
    
    # Active bids
    active_bids = await db.bids.count_documents({
        "listing_id": {"$in": [str(l["_id"]) async for l in db.listings.find({"seller_id": user["_id"], "status": "active"})]}
    })
    
    return {
        "active_listings": active_listings,
        "pending_listings": pending_listings,
        "sold_listings": sold_listings,
        "unsold_listings": unsold_listings,
        "total_watchers": watchers,
        "total_views": views,
        "total_sales": user.get("total_sales", 0),
        "total_revenue": user.get("total_sales_amount", 0),
        "seller_rating": user.get("seller_rating", 0),
        "total_ratings": user.get("total_ratings", 0),
        "positive_percentage": calculate_positive_percentage(user)
    }

# Relist Item
@api_router.post("/listings/{listing_id}/relist")
async def relist_item(listing_id: str, duration_days: int = 7, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if str(listing["seller_id"]) != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if listing["status"] not in ["ended", "unsold"]:
        raise HTTPException(status_code=400, detail="Can only relist ended or unsold items")
    
    end_time = datetime.now(timezone.utc) + timedelta(days=duration_days)
    
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "status": "pending",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": end_time.isoformat(),
                "current_bid": listing["starting_bid"],
                "bid_count": 0,
                "highest_bidder_id": None,
                "highest_bidder_name": None,
                "highest_bidder_max_bid": None,
                "reserve_met": False if listing.get("reserve_price") else True,
                "winner_id": None,
                "sold_price": None
            }
        }
    )
    
    return {"message": "Item relisted for approval"}

# Notifications
async def create_notification(user_id: str, type: str, message: str, listing_id: Optional[str] = None):
    notification = {
        "user_id": user_id,
        "type": type,
        "message": message,
        "listing_id": listing_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Send real-time notification
    await send_user_notification(user_id, notification)

@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user), limit: int = 50):
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("created_at", -1).limit(limit)
    notifications = []
    async for n in cursor:
        n["_id"] = str(n["_id"])
        notifications.append(n)
    
    unread_count = await db.notifications.count_documents({"user_id": user["_id"], "read": False})
    
    return {"notifications": notifications, "unread_count": unread_count}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user["_id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["_id"]}, {"$set": {"read": True}})
    return {"message": "All marked as read"}

# Verification
@api_router.post("/verification/submit")
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

@api_router.get("/verification/status")
async def get_verification_status(user: dict = Depends(get_current_user)):
    verification = await db.verifications.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    return {
        "verification_status": user["verification_status"],
        "verification_badge": user.get("verification_badge", False),
        "submission": verification if verification else None
    }

# Reporting
@api_router.post("/listings/{listing_id}/report")
async def report_listing(listing_id: str, report: ReportCreate, user: dict = Depends(get_current_user)):
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    report_doc = {
        "listing_id": listing_id,
        "listing_title": listing["title"],
        "reporter_id": user["_id"],
        "reporter_email": user["email"],
        "reason": report.reason,
        "description": report.description,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.reports.insert_one(report_doc)
    
    return {"message": "Report submitted"}

# Admin endpoints
@api_router.get("/admin/stats")
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

@api_router.get("/admin/listings")
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

@api_router.put("/admin/listings/{listing_id}")
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

@api_router.delete("/admin/listings/{listing_id}")
async def admin_delete_listing(listing_id: str, admin: dict = Depends(require_admin)):
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    await db.listings.delete_one({"_id": ObjectId(listing_id)})
    await db.bids.delete_many({"listing_id": listing_id})
    
    return {"message": "Listing deleted"}

@api_router.get("/admin/users")
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

@api_router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, update: UserUpdate, admin: dict = Depends(require_admin)):
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated"}

@api_router.get("/admin/verifications")
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

@api_router.put("/admin/verifications/{verification_id}")
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

@api_router.get("/admin/reports")
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

# User Profile (public)
@api_router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get active listings
    active_listings = await db.listings.count_documents({"seller_id": user["_id"], "status": "active"})
    
    return {
        "id": str(user["_id"]),
        "full_name": user["full_name"],
        "city": user["city"],
        "province": user.get("province", "British Columbia"),
        "verification_badge": user.get("verification_badge", False),
        "seller_rating": user.get("seller_rating", 0),
        "total_ratings": user.get("total_ratings", 0),
        "positive_percentage": calculate_positive_percentage(user),
        "total_sales": user.get("total_sales", 0),
        "active_listings": active_listings,
        "member_since": user.get("created_at")
    }

async def _seed_admin():
    """Create or update the admin user. Refuses default/unset password in production (R8)."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@bidca.ca")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    is_production = os.environ.get("ENV", "").lower() == "production"

    if is_production and (not os.environ.get("ADMIN_PASSWORD") or admin_password == "admin123"):
        logger.error(
            "FATAL: ENV=production but ADMIN_PASSWORD is unset or still 'admin123'. "
            "Admin seed skipped — set a strong ADMIN_PASSWORD before deploying."
        )
    else:
        existing = await db.users.find_one({"email": admin_email})
        if existing is None:
            hashed = hash_password(admin_password)
            await db.users.insert_one({
                "email": admin_email,
                "password_hash": hashed,
                "full_name": "Admin",
                "city": "Vancouver",
                "postal_code": "V6B1A1",
                "province": "British Columbia",
                "role": "admin",
                "verification_status": "verified",
                "verification_badge": True,
                "is_suspended": False,
                "is_banned": False,
                "seller_rating": 5.0,
                "total_ratings": 0,
                "positive_ratings": 0,
                "neutral_ratings": 0,
                "negative_ratings": 0,
                "total_sales": 0,
                "total_sales_amount": 0,
                "total_purchases": 0,
                "total_bids_placed": 0,
                "auctions_won": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info("Admin user seeded")
        elif not verify_password(admin_password, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
            logger.info("Admin password updated")

# Startup event
@fastapi_app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.listings.create_index([("status", 1), ("end_time", 1)])
    await db.listings.create_index([("category", 1), ("status", 1)])
    await db.listings.create_index([("seller_id", 1)])
    await db.listings.create_index([("title", "text"), ("description", "text")])
    await db.bids.create_index([("listing_id", 1), ("created_at", -1)])
    await db.bids.create_index([("bidder_id", 1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.watchlist.create_index([("user_id", 1), ("listing_id", 1)], unique=True)
    await db.feedback.create_index([("to_user_id", 1), ("created_at", -1)])
    await db.transactions.create_index([("buyer_id", 1)])
    await db.transactions.create_index([("seller_id", 1)])
    await db.login_attempts.create_index("identifier")
    
    await _seed_admin()

    # Start background auction closer
    from app.closer import start_closer
    start_closer(db, sio)

    logger.info("BidCa.ca Full Auction Platform API started")

@fastapi_app.on_event("shutdown")
async def shutdown():
    from app.closer import stop_closer
    stop_closer()
    client.close()


# Include router
fastapi_app.include_router(api_router)

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wrap with Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/api/socket.io')
app = socket_app
