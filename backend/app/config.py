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


def is_production() -> bool:
    return os.environ.get("ENV", "").lower() == "production"


def inactivity_logout() -> timedelta:
    """Sign a user out after this long without activity (FR-02; Q010 default: 30 min)."""
    return timedelta(minutes=float(os.environ.get("INACTIVITY_LOGOUT_MINUTES") or "30"))
