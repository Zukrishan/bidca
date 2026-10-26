"""
sales.py — finishing a sale outside the auction closer (Buy It Now, accepted best offer).

One path so both ways of selling end the same: the listing is marked sold atomically (only if
it is still active, so two buyers can't both win), a transaction is recorded, both users' stats
move, both sides are notified, and the auction room gets the same `auction_ended` shape as the
closer emits (backlog B4/B5).
"""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException

from app.db import db
from app.helpers import create_notification, email_user, notify_losing_bidders
from app.realtime import broadcast_auction_end


async def complete_sale(listing: dict, buyer_id: str, price: float, sold_via: str,
                        offer_id: Optional[str] = None) -> None:
    """Mark `listing` sold to `buyer_id` for `price`. Raises 409 if it is no longer active."""
    listing_id = str(listing["_id"])
    seller_id = str(listing["seller_id"])
    now = datetime.now(timezone.utc).isoformat()

    sold = await db.listings.find_one_and_update(
        {"_id": ObjectId(listing_id), "status": "active"},
        {"$set": {"status": "sold", "winner_id": buyer_id, "sold_price": price,
                  "sold_via": sold_via, "end_time": now, "closed_at": now}},
    )
    if sold is None:
        raise HTTPException(status_code=409, detail="This listing has already ended")

    transaction = {
        "listing_id": listing_id,
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "amount": price,
        "type": sold_via,
        "status": "open",  # no money involved (NFR-07); open until both sides complete
        "created_at": now,
    }
    if offer_id:
        transaction["offer_id"] = offer_id
    await db.transactions.insert_one(transaction)

    # users are keyed by ObjectId; listings and transactions store the stringified id
    await db.users.update_one({"_id": ObjectId(buyer_id)}, {"$inc": {"total_purchases": 1}})
    await db.users.update_one({"_id": ObjectId(seller_id)},
                              {"$inc": {"total_sales": 1, "total_sales_amount": price}})

    how = "via Buy It Now" if sold_via == "buy_it_now" else "by accepting an offer"
    seller_msg = f"Your item '{listing['title']}' sold {how} for ${price:.2f}. Message the buyer to arrange the exchange."
    buyer_msg = f"You bought '{listing['title']}' for ${price:.2f}. Message the seller to arrange the exchange."
    await create_notification(seller_id, "item_sold", seller_msg, listing_id)
    await create_notification(buyer_id, "purchase_complete", buyer_msg, listing_id)
    # Both sides are emailed immediately, as for an auction win (FR-11)
    await email_user(seller_id, f"Your item {listing['title']} has a buyer", seller_msg, "/messages")
    await email_user(buyer_id, f"You bought {listing['title']}", buyer_msg, "/messages")
    if listing.get("listing_type") == "auction_bin":
        await notify_losing_bidders(listing_id, listing["title"], buyer_id)

    await broadcast_auction_end(listing_id, {
        "listing_id": listing_id, "status": "sold", "sold_price": price, "winner_id": buyer_id,
        "sold_via": sold_via,
        "price": price,  # contract v1 field for buy-now; kept for existing clients
    })
