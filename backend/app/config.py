import os
from datetime import timedelta

# Ports: API :8100, web :3100 (AGENTS.md); never the :3000 default.
DEFAULT_FRONTEND_URL = "http://localhost:3100"


def frontend_origin() -> str:
    """The one browser origin allowed to call the API with credentials (HTTP CORS and Socket.IO)."""
    return os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL)


# Rule durations are settings (docs/srs/02-functional.md "Settings"); defaults are the
# provisional client decisions of 26 Oct 2026.
def login_lockout() -> timedelta:
    """How long 5 failed logins lock an account (FR-02; source: 12 h)."""
    return timedelta(hours=float(os.environ.get("LOGIN_LOCKOUT_HOURS") or "12"))


# After a win (FR-26/FR-27; Q010). The buyer must answer the transaction chat within the window or
# the sale is cancelled and their account is locked; open transactions get periodic reminders.
def no_response_window() -> timedelta:
    """How long a buyer has to send a first message before the sale is cancelled (FR-26; source: 24 h)."""
    return timedelta(hours=float(os.environ.get("NO_RESPONSE_HOURS") or "24"))


def no_response_lock() -> timedelta:
    """How long a buyer who never answered is locked out (FR-26; Q010: 6 h)."""
    return timedelta(hours=float(os.environ.get("NO_RESPONSE_LOCK_HOURS") or "6"))


def reminder_interval() -> timedelta:
    """Gap between 'still open' reminder emails (FR-27; Q010: 6 h)."""
    return timedelta(hours=float(os.environ.get("REMINDER_INTERVAL_HOURS") or "6"))


def reminder_max() -> int:
    """Reminders per transaction before admins are alerted instead (FR-27; Q010: 10)."""
    return int(os.environ.get("REMINDER_MAX") or "10")
