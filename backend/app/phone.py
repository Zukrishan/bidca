"""
phone.py — phone-number verification codes (FR-01; Q011).

Twilio Verify when TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID are all set
(plain HTTPS via `httpx`, no SDK). Without them dev/test send nothing and accept DEV_PHONE_CODE;
production refuses to start (`app.accounts.check_production_settings`) and, as a second line,
refuses the call here with 503.
"""

import logging
import os
import re
from typing import Optional

import httpx
from fastapi import HTTPException

from app.config import is_production

logger = logging.getLogger(__name__)

DEV_PHONE_CODE = "000000"
TWILIO_VERIFY_BASE = "https://verify.twilio.com/v2/Services"
TWILIO_ENV = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID")


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Canadian/US number → E.164 (`+1XXXXXXXXXX`), or None if it isn't one."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01":
        return None
    return f"+1{digits}"


def twilio_configured() -> bool:
    return all(os.getenv(k) for k in TWILIO_ENV)


def phone_mode() -> str:
    """'twilio' (real SMS), 'dev' (fixed test code) or 'off' (production without keys)."""
    if twilio_configured():
        return "twilio"
    return "off" if is_production() else "dev"


async def _twilio_post(path: str, data: dict) -> dict:
    sid, token, service = (os.environ[k] for k in TWILIO_ENV)
    async with httpx.AsyncClient(timeout=10, auth=(sid, token)) as client:
        resp = await client.post(f"{TWILIO_VERIFY_BASE}/{service}/{path}", data=data)
    body = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        # 404 on VerificationCheck means no pending code (expired or already used)
        body.setdefault("status", "not_found" if resp.status_code == 404 else "error")
        body["http_status"] = resp.status_code
    return body


def _require_mode() -> str:
    mode = phone_mode()
    if mode == "off":
        raise HTTPException(status_code=503, detail="Phone verification is not configured")
    return mode


async def send_code(phone: str) -> None:
    mode = _require_mode()
    if mode == "dev":
        logger.info("phone (dev): code for %s is %s — Twilio not configured", phone, DEV_PHONE_CODE)
        return
    try:
        result = await _twilio_post("Verifications", {"To": phone, "Channel": "sms"})
    except Exception as exc:
        logger.error("Twilio send failed: %s", exc)
        raise HTTPException(status_code=503, detail="Could not send the code, please try again")
    if result.get("http_status"):
        logger.error("Twilio send refused: %s", result)
        raise HTTPException(status_code=400, detail="Could not send a code to that number")


async def check_code(phone: str, code: str) -> bool:
    mode = _require_mode()
    code = (code or "").strip()
    if mode == "dev":
        return code == DEV_PHONE_CODE
    try:
        result = await _twilio_post("VerificationCheck", {"To": phone, "Code": code})
    except Exception as exc:
        logger.error("Twilio check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Could not check the code, please try again")
    return result.get("status") == "approved"
