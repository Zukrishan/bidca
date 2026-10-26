from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import socketio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.config import frontend_origin
from app.db import client, db  # MongoDB connection (created at import time)
from app.security import get_current_user, get_optional_user, require_admin  # noqa: F401 — re-exported for tests/dependency_overrides
from app.realtime import sio
from app.seed import _seed_admin
from app.routers import (
    health, auth, email_verification, password_reset, uploads, catalog, listings, bidding, sniper, buy_now, offers,
    watchlist, saved_searches, feedback, dashboard, seller_stats, relist, notifications,
    verification, reports, admin, profile, messages, transactions,
)

fastapi_app = FastAPI(title="BidCa.ca API - Full Auction Platform")

# Startup event
@fastapi_app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.listings.create_index([("status", 1), ("end_time", 1)])
    await db.listings.create_index([("category", 1), ("status", 1)])
    await db.listings.create_index([("seller_id", 1)])
    await db.listings.create_index([("title", "text"), ("description", "text")])
    await db.bids.create_index([("listing_id", 1), ("created_at", -1)])
    await db.bids.create_index([("bidder_id", 1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.watchlist.create_index([("user_id", 1), ("listing_id", 1)], unique=True)
    await db.feedback.create_index([("to_user_id", 1), ("created_at", -1)])
    await db.transactions.create_index([("buyer_id", 1)])
    await db.transactions.create_index([("seller_id", 1)])
    await db.transactions.create_index([("status", 1), ("created_at", 1)])  # no-response + reminder jobs
    await db.login_attempts.create_index("identifier")
    await db.messages.create_index([("transaction_id", 1), ("created_at", 1)])
    await db.messages.create_index([("recipient_id", 1), ("read_at", 1)])
    
    await _seed_admin()

    # Start background auction closer
    from app.closer import start_closer
    start_closer(db, sio)

    logger.info("BidCa.ca Full Auction Platform API started")

@fastapi_app.on_event("shutdown")
async def shutdown():
    from app.closer import stop_closer
    stop_closer()
    client.close()

# Include routers (order matches the original route table), all under /api
for _r in (
    health, auth, email_verification, password_reset, uploads, catalog, listings, bidding, sniper,
    buy_now, offers, watchlist, saved_searches, feedback, dashboard, seller_stats,
    relist, notifications, verification, reports, admin, profile, messages, transactions,
):
    fastapi_app.include_router(_r.router, prefix="/api")

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wrap with Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path='/api/socket.io')
app = socket_app
