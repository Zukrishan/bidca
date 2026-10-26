from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional, Literal

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

class VehicleDisclosure(BaseModel):
    """Seller's answers for a Vehicles listing (FR-30, Q008). All required on submit, not on a draft."""
    accident_history: Optional[bool] = None
    accident_description: Optional[str] = None  # required when accident_history is true
    mechanical_issues: Optional[bool] = None
    mechanical_description: Optional[str] = None  # required when mechanical_issues is true
    previous_owners: Optional[int] = Field(default=None, ge=0, le=99)
    safety_certificate: Optional[bool] = None
    safety_certificate_url: Optional[str] = None  # optional upload
    odometer_km: Optional[int] = Field(default=None, ge=0, le=5_000_000)
    liens: Optional[bool] = None


class AuctionCreate(BaseModel):
    # Optional so a draft can be saved half-filled; a listing submitted for approval must have
    # title, category, description, condition, city and a starting bid (checked in app/listing_rules.py).
    title: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    province: str = "British Columbia"
    starting_bid: Optional[float] = None
    reserve_price: Optional[float] = None
    buy_it_now_price: Optional[float] = None
    duration_days: Literal[1, 3, 5, 7, 10] = 7
    images: List[str] = []
    condition: Literal["new", "like_new", "good", "fair", "poor"] = "good"
    # No shipping: buyer and seller exchange in person (FR-05). Old clients' shipping fields are ignored.
    accepts_best_offer: bool = False  # fixed-price only (FR-28); ignored for auctions
    listing_type: Literal["auction", "fixed_price", "auction_bin", "private"] = "auction"
    draft: bool = False  # true: saved as a seller-only draft, not submitted (FR-05)
    category_fields: Optional[Dict[str, Any]] = None  # see constants.CATEGORY_FIELDS
    vehicle_disclosure: Optional[VehicleDisclosure] = None  # required for Vehicles (Q008)
    # Private listings (FR-31): BidCa user ids, emails or phone numbers of people invited to bid
    invitees: List[str] = []


class CancelListingRequest(BaseModel):
    confirm_penalty: bool = False  # must be true to cancel a listing that has bids (FR-29)


class InviteCreate(BaseModel):
    identifier: str  # a BidCa user id, email or phone number

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
    city: Optional[str] = None
    listing_type: Optional[Literal["auction", "fixed_price", "auction_bin"]] = None
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
