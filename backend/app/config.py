import os
from datetime import timedelta

# Ports: API :8100, web :3100 (AGENTS.md); never the :3000 default.
DEFAULT_FRONTEND_URL = "http://localhost:3100"


def frontend_origin() -> str:
    """The one browser origin allowed to call the API with credentials (HTTP CORS and Socket.IO)."""
    return os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL)


# Listing rules (Phase 9e) — settings too; defaults are the provisional decisions Q010, Q015.
def seller_cancel_suspension_days() -> list:
    """Suspension in days for the 1st, 2nd, ... cancellation of a listing that had bids within
    `seller_cancel_window()` (FR-29, Q010: 2 days, then 7). Past the end of the list the seller is
    suspended until an admin reviews the account. SELLER_CANCEL_SUSPENSION_DAYS is e.g. "2,7"."""
    raw = os.environ.get("SELLER_CANCEL_SUSPENSION_DAYS") or "2,7"
    return [float(x) for x in raw.split(",") if x.strip()]


def seller_cancel_window() -> timedelta:
    """How far back earlier cancellations count toward the next suspension (Q010: 12 months)."""
    return timedelta(days=float(os.environ.get("SELLER_CANCEL_WINDOW_DAYS") or "365"))


def listing_cap_per_month() -> int:
    """Listings a user may submit for approval per calendar month, Pacific time (FR-34, Q015)."""
    return int(os.environ.get("LISTING_CAP_PER_MONTH") or "30")


def free_period_start():
    """Public launch date (YYYY-MM-DD) the free period starts on, or None while unset (Q015).
    Informational only: nothing is ever charged (NFR-07, Q004)."""
    from datetime import date
    raw = (os.environ.get("FREE_PERIOD_START") or "").strip()
    return date.fromisoformat(raw) if raw else None


def free_period_months() -> int:
    """Length of the free period in months (Q015: 3)."""
    return int(os.environ.get("FREE_PERIOD_MONTHS") or "3")


# Rule durations are settings (docs/srs/02-functional.md "Settings"); defaults are the
# provisional client decisions of 26 Oct 2026.
def login_lockout() -> timedelta:
    """How long 5 failed logins lock an account (FR-02; source: 12 h)."""
    return timedelta(hours=float(os.environ.get("LOGIN_LOCKOUT_HOURS") or "12"))
