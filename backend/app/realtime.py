import logging
from http.cookies import SimpleCookie

import socketio
from fastapi import HTTPException

from app.config import frontend_origin
from app.security import user_from_access_token

logger = logging.getLogger(__name__)

# Socket.IO setup — same single allowed origin as the HTTP API's CORS
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[frontend_origin()])

@sio.event
async def connect(sid, environ, auth=None):
    # Anyone may connect (public auction rooms); a valid access_token cookie identifies the user
    # for their private notification room (backlog B1).
    user_id = None
    cookie = SimpleCookie(environ.get("HTTP_COOKIE", ""))
    if "access_token" in cookie:
        try:
            user_id = (await user_from_access_token(cookie["access_token"].value))["_id"]
        except HTTPException:
            pass
    await sio.save_session(sid, {"user_id": user_id})
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def join_auction(sid, data):
    auction_id = data.get("auction_id")
    if auction_id:
        await sio.enter_room(sid, f"auction_{auction_id}")
        logger.info(f"Client {sid} joined auction room {auction_id}")

@sio.event
async def leave_auction(sid, data):
    auction_id = data.get("auction_id")
    if auction_id:
        await sio.leave_room(sid, f"auction_{auction_id}")

@sio.event
async def join_user_notifications(sid, data=None):
    """Join the caller's own notification room. The room comes from the authenticated session,
    never from the payload: a client can't subscribe to another user's notifications."""
    session = await sio.get_session(sid)
    user_id = session.get("user_id")
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}
    await sio.enter_room(sid, f"user_{user_id}")
    return {"ok": True}

async def broadcast_bid_update(auction_id: str, bid_data: dict):
    await sio.emit('bid_update', bid_data, room=f"auction_{auction_id}")

async def broadcast_auction_end(auction_id: str, data: dict):
    await sio.emit('auction_ended', data, room=f"auction_{auction_id}")

async def send_user_notification(user_id: str, notification: dict):
    await sio.emit('notification', notification, room=f"user_{user_id}")
