"""
email.py — transactional email via SendGrid, with a log fallback.

Usage:
    from app.email import send_email
    await send_email(to="user@example.com", subject="...", html="<p>...</p>")

When SENDGRID_API_KEY is set the message is delivered via SendGrid.
When the key is absent (dev/test) the call is a no-op that logs the payload.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> None:
    """Send a transactional email.

    Uses SendGrid when SENDGRID_API_KEY is set; otherwise logs and returns.
    Never raises — failures are logged so the caller is never interrupted.
    """
    api_key = os.getenv("SENDGRID_API_KEY")

    if not api_key:
        logger.info(
            "send_email (mock): to=%s subject=%r — SENDGRID_API_KEY not set",
            to,
            subject,
        )
        # Dev convenience, opt-in only: bodies carry verification/reset tokens, so logging them must
        # never happen by accident (e.g. a server that forgot ENV). Never in production, even if set.
        if os.getenv("EMAIL_LOG_BODIES", "").lower() in ("1", "true") and os.getenv("ENV", "").lower() != "production":
            logger.info("send_email (mock) body: %s", html)
        return

    try:
        # Import lazily so the package is optional in dev/test
        from sendgrid import SendGridAPIClient  # type: ignore
        from sendgrid.helpers.mail import Mail  # type: ignore

        from_email = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@bidca.ca")
        message = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
            html_content=html,
        )
        sg = SendGridAPIClient(api_key)
        # SendGrid's client is blocking; keep it off the event loop
        response = await asyncio.to_thread(sg.send, message)
        logger.info(
            "send_email: to=%s subject=%r status=%s",
            to,
            subject,
            response.status_code,
        )
    except Exception as exc:  # pragma: no cover
        logger.error("send_email failed: to=%s error=%s", to, exc)
