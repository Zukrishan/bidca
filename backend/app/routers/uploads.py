from fastapi import APIRouter, HTTPException, Depends, Query
import os
import time

import cloudinary
import cloudinary.utils

from app.security import get_current_user

router = APIRouter()

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


# Cloudinary signature
@router.get("/cloudinary/signature")
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
