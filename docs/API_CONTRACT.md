# API_CONTRACT.md — BidCa backend ⇄ frontend

Status: **draft, generated from `backend/server.py` @ 9ce8c71 (28 Sep 2026)**. Freeze (and bump to v1)
before Phase 4 starts. Base path `/api`; auth via httpOnly cookies; Socket.IO at `/api/socket.io`.

## Locked decisions
- D1 Ports: API :8100, web :3100.
- D2 IDs are strings; timestamps ISO-8601 UTC.
- D3 Errors: `{"detail": "..."}` with the HTTP status (FastAPI default).
- D4 Listing status set: `pending | approved | rejected | active | ended | sold | unsold`.

## Endpoints (as implemented)
| Method | Path |
|---|---|
| GET | `/` |
| GET | `/health` |
| POST | `/auth/register` |
| POST | `/auth/login` |
| POST | `/auth/logout` |
| GET | `/auth/me` |
| POST | `/auth/refresh` |
| GET | `/cloudinary/signature` (503 `Cloudinary is not configured` when env unset — `feature/p0-backend`) |
| GET | `/categories` |
| GET | `/cities` |
| GET | `/provinces` |
| GET | `/popular-keywords` |
| POST | `/listings` |
| GET | `/listings` |
| GET | `/listings/featured` |
| GET | `/listings/ending-soon` |
| GET | `/listings/{listing_id}` |
| POST | `/listings/{listing_id}/bid` |
| POST | `/listings/{listing_id}/sniper-bid` |
| POST | `/listings/{listing_id}/buy-now` |
| POST | `/listings/{listing_id}/best-offer` |
| PUT | `/offers/{offer_id}/respond` |
| POST | `/listings/{listing_id}/watch` |
| GET | `/users/me/watchlist` |
| POST | `/saved-searches` |
| GET | `/saved-searches` |
| DELETE | `/saved-searches/{search_id}` |
| POST | `/transactions/{transaction_id}/feedback` |
| GET | `/users/{user_id}/feedback` |
| GET | `/users/me/bids` |
| GET | `/users/me/listings` |
| GET | `/users/me/purchases` |
| GET | `/users/me/sales` |
| GET | `/users/me/seller-stats` |
| POST | `/listings/{listing_id}/relist` |
| GET | `/notifications` |
| PUT | `/notifications/{notification_id}/read` |
| PUT | `/notifications/read-all` |
| POST | `/verification/submit` |
| GET | `/verification/status` |
| POST | `/listings/{listing_id}/report` |
| GET | `/admin/stats` |
| GET | `/admin/listings` |
| PUT | `/admin/listings/{listing_id}` |
| DELETE | `/admin/listings/{listing_id}` |
| GET | `/admin/users` |
| PUT | `/admin/users/{user_id}` |
| GET | `/admin/verifications` |
| PUT | `/admin/verifications/{verification_id}` |
| GET | `/admin/reports` |
| GET | `/users/{user_id}/profile` |

## Socket.IO events (server)
See `@sio.event` handlers at `server.py:237-258` (connect, disconnect, join/leave listing rooms). Bid
updates are emitted to the listing room.

## Phase 1 additions (implemented on `feature/p0-backend`, not yet frozen)
| Method | Path | Notes |
|---|---|---|
| POST | `/auth/forgot-password` | `{email}` → always 200 `{message}` (no user enumeration); emails reset link |
| POST | `/auth/reset-password` | `{token, password}` → 200 `{message}`; 400 `Invalid or expired reset token`; token single-use, 1h expiry, stored sha256-hashed |
| GET | `/cloudinary/signature` | now 503 `{"detail": "Cloudinary is not configured"}` when Cloudinary env vars unset |
| — | background closer | every 30s: run due sniper bids, close due auctions (idempotent), notify winner+seller, emit `auction_ended` `{listing_id, status, sold_price?, winner_id?}` to room `auction_{listing_id}` |
