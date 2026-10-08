from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import SavedSearchCreate, SavedSearchUpdate

router = APIRouter()


# Saved Searches
@router.post("/saved-searches")
async def create_saved_search(search: SavedSearchCreate, user: dict = Depends(get_current_user)):
    search_doc = {
        "user_id": user["_id"],
        "name": search.name,
        "query": search.query,
        "category": search.category,
        "city": search.city,
        "listing_type": search.listing_type,
        "min_price": search.min_price,
        "max_price": search.max_price,
        "notify": True,
        "alerts_enabled": True,
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
        s.setdefault("alerts_enabled", True)
        searches.append(s)
    return {"saved_searches": searches}

@router.put("/saved-searches/{search_id}")
async def update_saved_search(search_id: str, body: SavedSearchUpdate, user: dict = Depends(get_current_user)):
    """Turn new-match alerts on or off for one of the caller's saved searches."""
    if not ObjectId.is_valid(search_id):
        raise HTTPException(status_code=400, detail="Invalid saved search id")
    result = await db.saved_searches.update_one(
        {"_id": ObjectId(search_id), "user_id": user["_id"]}, {"$set": {"alerts_enabled": body.alerts_enabled}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Saved search updated", "alerts_enabled": body.alerts_enabled}

@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(search_id: str, user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(search_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
    await db.saved_searches.delete_one({"_id": ObjectId(search_id), "user_id": user["_id"]})
    return {"message": "Search deleted"}
