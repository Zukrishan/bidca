import logging
import os
from datetime import datetime, timezone

from app.db import db
from app.security import hash_password, verify_password

logger = logging.getLogger(__name__)

async def _seed_admin():
    """Create or update the admin user. Refuses default/unset password in production (R8)."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@bidca.ca")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    is_production = os.environ.get("ENV", "").lower() == "production"

    if is_production and (not os.environ.get("ADMIN_PASSWORD") or admin_password == "admin123"):
        logger.error(
            "FATAL: ENV=production but ADMIN_PASSWORD is unset or still 'admin123'. "
            "Admin seed skipped — set a strong ADMIN_PASSWORD before deploying."
        )
    else:
        existing = await db.users.find_one({"email": admin_email})
        if existing is None:
            hashed = hash_password(admin_password)
            await db.users.insert_one({
                "email": admin_email,
                "password_hash": hashed,
                "full_name": "Admin",
                "city": "Vancouver",
                "postal_code": "V6B1A1",
                "province": "British Columbia",
                "role": "admin",
                "email_verified": True,
                "verification_status": "verified",
                "verification_badge": True,
                "is_suspended": False,
                "is_banned": False,
                "seller_rating": 5.0,
                "total_ratings": 0,
                "positive_ratings": 0,
                "neutral_ratings": 0,
                "negative_ratings": 0,
                "total_sales": 0,
                "total_sales_amount": 0,
                "total_purchases": 0,
                "total_bids_placed": 0,
                "auctions_won": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info("Admin user seeded")
        elif not existing.get("email_verified"):
            await db.users.update_one({"email": admin_email}, {"$set": {"email_verified": True}})
        if existing is not None and not verify_password(admin_password, existing["password_hash"]):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
            logger.info("Admin password updated")
