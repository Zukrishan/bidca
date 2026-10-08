from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal

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

class SavedSearchUpdate(BaseModel):
    alerts_enabled: bool

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


class VerifyEmailRequest(BaseModel):
    token: str
