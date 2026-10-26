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

# Listing statuses anyone may see; pending/rejected are seller- and admin-only (contract D8).
# draft and cancelled (Phase 9e) are never public either.
PUBLIC_LISTING_STATUSES = {"active", "ended", "sold", "unsold"}

# Listing types that run as auctions; "private" is an invite-only auction (FR-31)
AUCTION_LISTING_TYPES = ["auction", "auction_bin", "private"]

# Extra fields some categories ask for (FR-05): name → type. Stored as listing["category_fields"].
CATEGORY_FIELDS = {
    "Vehicles": {"year": int, "make": str, "model": str, "mileage": int},
    "Electronics": {"brand": str, "model": str},
}

# The category whose listings need the seller's vehicle disclosure and show the checklist (FR-30)
VEHICLES_CATEGORY = "Vehicles"
