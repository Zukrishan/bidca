import logging
import socketio

logger = logging.getLogger(__name__)

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
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
async def join_user_notifications(sid, data):
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, f"user_{user_id}")

async def broadcast_bid_update(auction_id: str, bid_data: dict):
    await sio.emit('bid_update', bid_data, room=f"auction_{auction_id}")

async def broadcast_auction_end(auction_id: str, data: dict):
    await sio.emit('auction_ended', data, room=f"auction_{auction_id}")

async def send_user_notification(user_id: str, notification: dict):
    await sio.emit('notification', notification, room=f"user_{user_id}")
