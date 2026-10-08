from fastapi import APIRouter, Depends
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.helpers import parse_object_id

router = APIRouter()



@router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user), limit: int = 50):
    cursor = db.notifications.find({"user_id": user["_id"]}).sort("created_at", -1).limit(limit)
    notifications = []
    async for n in cursor:
        n["_id"] = str(n["_id"])
        notifications.append(n)
    
    unread_count = await db.notifications.count_documents({"user_id": user["_id"], "read": False})
    
    return {"notifications": notifications, "unread_count": unread_count}

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"_id": parse_object_id(notification_id, "Notification not found"), "user_id": user["_id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}

@router.put("/notifications/read-all")
async def mark_all_notifications_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["_id"]}, {"$set": {"read": True}})
    return {"message": "All marked as read"}
