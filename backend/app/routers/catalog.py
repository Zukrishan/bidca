from fastapi import APIRouter

from app.constants import CATEGORIES, BC_CITIES, PROVINCES

router = APIRouter()


# Categories
@router.get("/categories")
async def get_categories():
    return {"categories": CATEGORIES}

@router.get("/cities")
async def get_cities():
    return {"cities": BC_CITIES}

@router.get("/provinces")
async def get_provinces():
    return {"provinces": PROVINCES}

# Popular search keywords
@router.get("/popular-keywords")
async def get_popular_keywords():
    # In production, this would be based on actual search analytics
    keywords = [
        "iPhone", "PS5", "MacBook", "Nintendo Switch", "AirPods",
        "Vintage Watch", "Hockey Cards", "Mountain Bike", "Camera",
        "Antique Furniture", "Gold Coins", "Electric Guitar"
    ]
    return {"keywords": keywords}
