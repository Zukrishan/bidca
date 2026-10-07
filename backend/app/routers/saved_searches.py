from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import SavedSearchCreate

router = APIRouter()


# Saved Searches
@router.post("/saved-searches")
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

@router.get("/saved-searches")
async def get_saved_searches(user: dict = Depends(get_current_user)):
    cursor = db.saved_searches.find({"user_id": user["_id"]})
    searches = []
    async for s in cursor:
        s["_id"] = str(s["_id"])
        searches.append(s)
    return {"saved_searches": searches}

@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str, user: dict = Depends(get_current_user)):
    await db.saved_searches.delete_one({"_id": ObjectId(search_id), "user_id": user["_id"]})
    return {"message": "Search deleted"}
