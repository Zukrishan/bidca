from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.models import ReportCreate

router = APIRouter()


# Reporting
@router.post("/listings/{listing_id}/report")
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
