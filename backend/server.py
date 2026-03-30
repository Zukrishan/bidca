from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Query, UploadFile, File, BackgroundTasks
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
import cloudinary
import cloudinary.utils
import time
from bson import ObjectId
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Cloudinary configuration (MOCK - Replace with real credentials)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "mock_cloud_name"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "mock_api_key"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "mock_api_secret"),
    secure=True
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

# BC Cities
BC_CITIES = [
    "Vancouver", "Victoria", "Surrey", "Burnaby", "Richmond", "Abbotsford",
    "Coquitlam", "Kelowna", "Langley", "Saanich", "Delta", "Kamloops",
    "Nanaimo", "North Vancouver", "Chilliwack", "Maple Ridge", "New Westminster",
    "Prince George", "Port Coquitlam", "Vernon", "Courtenay", "Penticton",
    "Campbell River", "Mission", "West Vancouver", "Langford", "White Rock"
]

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    city: str
    postal_code: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    city: str
    role: str
    verification_status: str
    created_at: str

class AuctionCreate(BaseModel):
    title: str
    category: str
    description: str
    city: str
    starting_bid: float
    bid_increment: float
    duration_hours: Literal[24, 48, 72]
    images: List[str] = []
    listing_type: Literal["auction", "marketplace"] = "auction"
    fixed_price: Optional[float] = None

class BidCreate(BaseModel):
    amount: float

class VerificationSubmit(BaseModel):
    government_id_url: str
    selfie_url: str

class ListingUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected", "active", "ended", "completed"]

class UserUpdate(BaseModel):
    verification_status: Optional[Literal["unverified", "pending", "verified"]] = None
    is_suspended: Optional[bool] = None
    is_banned: Optional[bool] = None

class MessageCreate(BaseModel):
    content: str

class ReportCreate(BaseModel):
    reason: str
    description: str

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI(title="BidCa.ca API")

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

async def broadcast_bid_update(auction_id: str, bid_data: dict):
    await sio.emit('bid_update', bid_data, room=f"auction_{auction_id}")

async def broadcast_auction_end(auction_id: str, data: dict):
    await sio.emit('auction_ended', data, room=f"auction_{auction_id}")

# Create API router
api_router = APIRouter(prefix="/api")

# Health check
@api_router.get("/")
async def root():
    return {"message": "BidCa.ca API", "status": "running"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# Auth endpoints
@api_router.post("/auth/register")
async def register(user_data: UserRegister, response: Response):
    email = user_data.email.lower()
    
    # Validate BC postal code
    if not is_valid_bc_postal_code(user_data.postal_code):
        raise HTTPException(status_code=400, detail="Only British Columbia postal codes are accepted (starting with V)")
    
    # Check if email exists
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_doc = {
        "email": email,
        "password_hash": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "city": user_data.city,
        "postal_code": user_data.postal_code.upper().replace(" ", ""),
        "role": "user",
        "verification_status": "unverified",
        "verification_badge": False,
        "successful_sales": 0,
        "failed_purchases": 0,
        "is_suspended": False,
        "is_banned": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Create tokens
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
async def login(credentials: UserLogin, response: Response, request: Request):
    email = credentials.email.lower()
    
    # Brute force check
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"
    
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts and attempts.get("count", 0) >= 5:
        lockout_time = attempts.get("locked_until")
        if lockout_time and datetime.fromisoformat(lockout_time) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    
    # Find user
    user = await db.users.find_one({"email": email})
    if not user:
        await increment_login_attempts(identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Account has been banned")
    
    if user.get("is_suspended"):
        raise HTTPException(status_code=403, detail="Account has been suspended")
    
    if not verify_password(credentials.password, user["password_hash"]):
        await increment_login_attempts(identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Clear login attempts on success
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
        "verification_badge": user.get("verification_badge", False)
    }

async def increment_login_attempts(identifier: str):
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts:
        new_count = attempts.get("count", 0) + 1
        update = {"$set": {"count": new_count}}
        if new_count >= 5:
            update["$set"]["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": identifier}, update)
    else:
        await db.login_attempts.insert_one({"identifier": identifier, "count": 1})

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

# Cloudinary signature endpoint
@api_router.get("/cloudinary/signature")
async def get_cloudinary_signature(
    resource_type: str = Query("image", enum=["image", "video"]),
    folder: str = "bidca_uploads",
    user: dict = Depends(get_current_user)
):
    ALLOWED_FOLDERS = ("bidca_uploads/", "users/", "listings/", "verifications/")
    if not any(folder.startswith(f) or folder == f.rstrip('/') for f in ALLOWED_FOLDERS):
        folder = "bidca_uploads"
    
    timestamp = int(time.time())
    params = {
        "timestamp": timestamp,
        "folder": folder,
        "resource_type": resource_type
    }
    
    signature = cloudinary.utils.api_sign_request(params, os.getenv("CLOUDINARY_API_SECRET"))
    
    return {
        "signature": signature,
        "timestamp": timestamp,
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "api_key": os.getenv("CLOUDINARY_API_KEY"),
        "folder": folder,
        "resource_type": resource_type
    }

# Categories
CATEGORIES = [
    "Electronics", "Vehicles", "Furniture", "Clothing & Accessories",
    "Sports & Outdoors", "Home & Garden", "Collectibles & Art",
    "Jewelry & Watches", "Tools & Equipment", "Musical Instruments",
    "Books & Media", "Toys & Games", "Other"
]

@api_router.get("/categories")
async def get_categories():
    return {"categories": CATEGORIES}

@api_router.get("/cities")
async def get_cities():
    return {"cities": BC_CITIES}

# Listings/Auctions
@api_router.post("/listings")
async def create_listing(listing: AuctionCreate, user: dict = Depends(get_current_user)):
    # Check for active auctions (only one allowed)
    if listing.listing_type == "auction":
        active_auction = await db.listings.find_one({
            "seller_id": user["_id"],
            "listing_type": "auction",
            "status": {"$in": ["pending", "active"]}
        })
        if active_auction:
            raise HTTPException(status_code=400, detail="You can only have one active auction at a time")
    
    end_time = datetime.now(timezone.utc) + timedelta(hours=listing.duration_hours)
    
    listing_doc = {
        "title": listing.title,
        "category": listing.category,
        "description": listing.description,
        "city": listing.city,
        "images": listing.images,
        "listing_type": listing.listing_type,
        "starting_bid": listing.starting_bid,
        "current_bid": listing.starting_bid,
        "bid_increment": listing.bid_increment,
        "fixed_price": listing.fixed_price,
        "duration_hours": listing.duration_hours,
        "end_time": end_time.isoformat(),
        "seller_id": user["_id"],
        "seller_name": user["full_name"],
        "seller_city": user["city"],
        "seller_verified": user.get("verification_badge", False),
        "status": "pending",  # Requires admin approval
        "bid_count": 0,
        "highest_bidder_id": None,
        "highest_bidder_name": None,
        "winner_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.listings.insert_one(listing_doc)
    listing_doc["_id"] = str(result.inserted_id)
    listing_doc.pop("seller_id", None)
    
    return listing_doc

@api_router.get("/listings")
async def get_listings(
    category: Optional[str] = None,
    city: Optional[str] = None,
    listing_type: Optional[str] = None,
    status: str = "active",
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    query = {"status": status}
    if category:
        query["category"] = category
    if city:
        query["city"] = city
    if listing_type:
        query["listing_type"] = listing_type
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    skip = (page - 1) * limit
    cursor = db.listings.find(query, {"_id": 1, "title": 1, "category": 1, "city": 1, "images": 1,
                                       "current_bid": 1, "starting_bid": 1, "fixed_price": 1,
                                       "listing_type": 1, "end_time": 1, "bid_count": 1,
                                       "seller_name": 1, "seller_verified": 1, "status": 1})
    cursor.skip(skip).limit(limit).sort("created_at", -1)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        listings.append(doc)
    
    total = await db.listings.count_documents(query)
    
    return {"listings": listings, "total": total, "page": page, "pages": (total + limit - 1) // limit}

@api_router.get("/listings/featured")
async def get_featured_listings():
    cursor = db.listings.find(
        {"status": "active", "listing_type": "auction"},
        {"_id": 1, "title": 1, "category": 1, "city": 1, "images": 1,
         "current_bid": 1, "end_time": 1, "bid_count": 1, "seller_verified": 1}
    ).sort("bid_count", -1).limit(6)
    
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
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
    
    listing["_id"] = str(listing["_id"])
    listing["seller_id"] = str(listing["seller_id"])
    
    # Get bid history (masked usernames)
    bids_cursor = db.bids.find({"listing_id": listing_id}).sort("created_at", -1).limit(20)
    bids = []
    async for bid in bids_cursor:
        masked_name = bid["bidder_name"][:2] + "***" if len(bid["bidder_name"]) > 2 else "***"
        bids.append({
            "amount": bid["amount"],
            "bidder_name": masked_name,
            "created_at": bid["created_at"]
        })
    
    listing["bid_history"] = bids
    
    # Check if user is the seller
    if user and listing["seller_id"] == user["_id"]:
        listing["is_seller"] = True
    
    return listing

@api_router.post("/listings/{listing_id}/bid")
async def place_bid(listing_id: str, bid: BidCreate, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This auction is not active")
    
    if listing["listing_type"] != "auction":
        raise HTTPException(status_code=400, detail="This is not an auction listing")
    
    # Check if auction has ended
    end_time = datetime.fromisoformat(listing["end_time"])
    if datetime.now(timezone.utc) > end_time:
        raise HTTPException(status_code=400, detail="This auction has ended")
    
    # Check seller can't bid on own auction
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot bid on your own auction")
    
    min_bid = listing["current_bid"] + listing["bid_increment"]
    if bid.amount < min_bid:
        raise HTTPException(status_code=400, detail=f"Minimum bid is ${min_bid:.2f}")
    
    # Create bid record
    bid_doc = {
        "listing_id": listing_id,
        "bidder_id": user["_id"],
        "bidder_name": user["full_name"],
        "amount": bid.amount,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bids.insert_one(bid_doc)
    
    # Update listing
    await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {
            "$set": {
                "current_bid": bid.amount,
                "highest_bidder_id": user["_id"],
                "highest_bidder_name": user["full_name"]
            },
            "$inc": {"bid_count": 1}
        }
    )
    
    # Create notification for outbid user
    if listing.get("highest_bidder_id") and str(listing["highest_bidder_id"]) != user["_id"]:
        await create_notification(
            str(listing["highest_bidder_id"]),
            "outbid",
            f"You've been outbid on {listing['title']}",
            listing_id
        )
    
    # Broadcast bid update via WebSocket
    await broadcast_bid_update(listing_id, {
        "listing_id": listing_id,
        "current_bid": bid.amount,
        "bid_count": listing["bid_count"] + 1,
        "bidder_name": user["full_name"][:2] + "***"
    })
    
    return {"message": "Bid placed successfully", "current_bid": bid.amount}

# User Dashboard
@api_router.get("/users/me/bids")
async def get_my_bids(user: dict = Depends(get_current_user)):
    cursor = db.bids.find({"bidder_id": user["_id"]}).sort("created_at", -1)
    bids = []
    async for bid in cursor:
        listing = await db.listings.find_one({"_id": ObjectId(bid["listing_id"])})
        if listing:
            bids.append({
                "bid_id": str(bid["_id"]),
                "listing_id": bid["listing_id"],
                "listing_title": listing["title"],
                "listing_image": listing["images"][0] if listing["images"] else None,
                "amount": bid["amount"],
                "current_bid": listing["current_bid"],
                "is_winning": str(listing.get("highest_bidder_id")) == user["_id"],
                "status": listing["status"],
                "end_time": listing["end_time"],
                "created_at": bid["created_at"]
            })
    return {"bids": bids}

@api_router.get("/users/me/listings")
async def get_my_listings(user: dict = Depends(get_current_user)):
    cursor = db.listings.find({"seller_id": user["_id"]}).sort("created_at", -1)
    listings = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc.pop("seller_id", None)
        listings.append(doc)
    return {"listings": listings}

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
    
    return {"message": "Verification submitted successfully"}

@api_router.get("/verification/status")
async def get_verification_status(user: dict = Depends(get_current_user)):
    verification = await db.verifications.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    return {
        "verification_status": user["verification_status"],
        "verification_badge": user.get("verification_badge", False),
        "submission": verification if verification else None
    }

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

@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("created_at", -1).limit(50)
    notifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)
    return {"notifications": notifications}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user["_id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["_id"]}, {"$set": {"read": True}})
    return {"message": "All notifications marked as read"}

# Messaging (for auction winners)
@api_router.post("/listings/{listing_id}/messages")
async def send_message(listing_id: str, message: MessageCreate, user: dict = Depends(get_current_user)):
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Only seller and winner can message
    is_seller = str(listing["seller_id"]) == user["_id"]
    is_winner = str(listing.get("winner_id")) == user["_id"]
    
    if not (is_seller or is_winner):
        raise HTTPException(status_code=403, detail="Only seller and winner can message")
    
    msg_doc = {
        "listing_id": listing_id,
        "sender_id": user["_id"],
        "sender_name": user["full_name"],
        "content": message.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.messages.insert_one(msg_doc)
    
    # Notify recipient
    recipient_id = str(listing["winner_id"]) if is_seller else str(listing["seller_id"])
    await create_notification(recipient_id, "message", f"New message about {listing['title']}", listing_id)
    
    return {"message": "Message sent"}

@api_router.get("/listings/{listing_id}/messages")
async def get_messages(listing_id: str, user: dict = Depends(get_current_user)):
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    is_seller = str(listing["seller_id"]) == user["_id"]
    is_winner = str(listing.get("winner_id")) == user["_id"]
    
    if not (is_seller or is_winner):
        raise HTTPException(status_code=403, detail="Access denied")
    
    cursor = db.messages.find({"listing_id": listing_id}).sort("created_at", 1)
    messages = []
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])
        messages.append(msg)
    
    return {"messages": messages}

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
    result = await db.listings.update_one(
        {"_id": ObjectId(listing_id)},
        {"$set": {"status": update.status}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    # Notify seller
    listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    if listing:
        await create_notification(
            str(listing["seller_id"]),
            "listing_status",
            f"Your listing '{listing['title']}' has been {update.status}",
            listing_id
        )
    
    return {"message": f"Listing {update.status}"}

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
    
    await create_notification(
        verification["user_id"],
        "verification",
        f"Your verification has been {status}"
    )
    
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

@api_router.get("/admin/stats")
async def admin_get_stats(admin: dict = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    total_listings = await db.listings.count_documents({})
    active_auctions = await db.listings.count_documents({"status": "active", "listing_type": "auction"})
    pending_listings = await db.listings.count_documents({"status": "pending"})
    pending_verifications = await db.verifications.count_documents({"status": "pending"})
    total_bids = await db.bids.count_documents({})
    
    return {
        "total_users": total_users,
        "total_listings": total_listings,
        "active_auctions": active_auctions,
        "pending_listings": pending_listings,
        "pending_verifications": pending_verifications,
        "total_bids": total_bids
    }

# Email notifications (MOCK - Replace SENDGRID_API_KEY with real key)
async def send_email_notification(to_email: str, subject: str, content: str):
    """Send email via SendGrid - MOCK implementation"""
    try:
        api_key = os.getenv("SENDGRID_API_KEY")
        if api_key == "mock_sendgrid_key":
            logger.info(f"MOCK EMAIL: To={to_email}, Subject={subject}")
            return True
        
        message = Mail(
            from_email=os.getenv("SENDER_EMAIL"),
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False

# Startup event - seed admin and create indexes
@fastapi_app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.listings.create_index([("status", 1), ("created_at", -1)])
    await db.listings.create_index([("category", 1), ("status", 1)])
    await db.listings.create_index([("seller_id", 1)])
    await db.bids.create_index([("listing_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.login_attempts.create_index("identifier")
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@bidca.ca")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "full_name": "Admin",
            "city": "Vancouver",
            "postal_code": "V6B1A1",
            "role": "admin",
            "verification_status": "verified",
            "verification_badge": True,
            "is_suspended": False,
            "is_banned": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Admin user seeded")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
        logger.info("Admin password updated")
    
    logger.info("BidCa.ca API started")

@fastapi_app.on_event("shutdown")
async def shutdown():
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
