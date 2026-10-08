"""FR-04 email verification: token issue helper (token pattern copied from password_reset)."""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

from app.config import frontend_origin
from app.db import db

TOKEN_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(seconds=60)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_verification_email(user_id: str, email: str) -> None:
    """Invalidate the user's earlier unused tokens, store a fresh hashed one and email the link."""
    # Imported at call time so tests can patch app.email.send_email
    from app.email import send_email
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.email_verifications.delete_many({"user_id": user_id, "used": False})
    await db.email_verifications.insert_one({
        "user_id": user_id,
        "token_hash": hash_token(token),
        "expires_at": (now + TOKEN_TTL).isoformat(),
        "used": False,
        "created_at": now.isoformat(),
    })
    url = f"{frontend_origin()}/verify-email?token={quote(token)}"
    await send_email(
        to=email,
        subject="Confirm your BidCa email",
        html=f"<p>Welcome to BidCa. Confirm your email address to start bidding and selling (valid 24 hours):</p>"
             f"<p><a href='{url}'>{url}</a></p>",
    )
