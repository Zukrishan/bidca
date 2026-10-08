from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId

from app.db import db
from app.security import get_current_user
from app.sales import complete_sale

router = APIRouter()


# Buy It Now
@router.post("/listings/{listing_id}/buy-now")
async def buy_it_now(listing_id: str, user: dict = Depends(get_current_user)):
    try:
        listing = await db.listings.find_one({"_id": ObjectId(listing_id)})
    except:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="This listing is not active")
    
    if not listing.get("buy_it_now_price"):
        raise HTTPException(status_code=400, detail="This listing does not have a Buy It Now option")
    
    if str(listing["seller_id"]) == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot buy your own listing")
    
    bin_price = listing["buy_it_now_price"]
    await complete_sale(listing, user["_id"], bin_price, "buy_it_now")
    return {"message": "Purchase successful!", "price": bin_price}
