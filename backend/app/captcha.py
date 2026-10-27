"""
captcha.py — Cloudflare Turnstile check on signup and login (FR-01, FR-02, NFR-03; Q011).

With TURNSTILE_SECRET_KEY set every register/login must carry a valid token. Without it, dev and
test skip the check; production refuses to start (`app.accounts.check_production_settings`).
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def captcha_configured() -> bool:
    return bool(os.getenv("TURNSTILE_SECRET_KEY"))


def captcha_site_key() -> Optional[str]:
    """Public site key for the widget, or None when CAPTCHA is off (dev)."""
    if not captcha_configured():
        return None
    return os.getenv("TURNSTILE_SITE_KEY") or None


async def _siteverify(secret: str, token: str, remote_ip: Optional[str]) -> dict:
    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(TURNSTILE_VERIFY_URL, data=data)
    return resp.json()


async def require_captcha(token: Optional[str], remote_ip: Optional[str] = None) -> None:
    """Raise 400 unless `token` passes Turnstile. No-op when CAPTCHA is not configured.

    Production cannot run unconfigured: the API refuses to start without the keys.
    """
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        return
    if not token:
        raise HTTPException(status_code=400, detail="Please complete the CAPTCHA")
    try:
        result = await _siteverify(secret, token, remote_ip)
    except Exception as exc:
        logger.error("Turnstile verify failed: %s", exc)
        raise HTTPException(status_code=503, detail="CAPTCHA check is unavailable, please try again")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail="CAPTCHA check failed, please try again")
