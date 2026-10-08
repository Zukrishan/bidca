import os

# Ports: API :8100, web :3100 (AGENTS.md); never the :3000 default.
DEFAULT_FRONTEND_URL = "http://localhost:3100"


def frontend_origin() -> str:
    """The one browser origin allowed to call the API with credentials (HTTP CORS and Socket.IO)."""
    return os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL)
