# BidCa.ca

Local auction + marketplace for British Columbia residents. Read `AGENTS.md` first (process and
what outranks what), then `docs/ACTION-PLAN.md` for current status.

## Layout

| Path | What |
|---|---|
| `backend/server.py` | FastAPI + Motor (MongoDB) + python-socketio, single 1.7k-line module, all routes under `/api` |
| `backend/tests/`, `backend_test.py` | pytest API tests (Emergent-era, run against a live server) |
| `frontend/` | React 19 CRA via craco, Tailwind + shadcn/Radix, socket.io-client. To be ported to Next.js (Phase 4) |
| `memory/PRD.md` | Emergent PRD — rank 6, superseded by `docs/srs/` |
| `docs/` | governance set — see `AGENTS.md` |

## Run

```bash
cd backend && uvicorn server:app --port 8100 --reload   # needs MONGO_URL, DB_NAME, JWT_SECRET, FRONTEND_URL=http://localhost:3100
cd frontend && PORT=3100 REACT_APP_BACKEND_URL=http://localhost:8100 yarn start
```

`app` is the Socket.IO ASGI wrapper (`/api/socket.io`); `fastapi_app` is the inner app.
Cloudinary and SendGrid read env vars and fall back to mocks when unset.

## Conventions

- Mongo `_id` is stringified in responses; timestamps are ISO-8601 UTC strings.
- Auth is JWT in httpOnly cookies (`access_token`, `refresh_token`); `get_current_user` dependency.
- New backend work should go in routers under `backend/app/` rather than growing `server.py`
  (Phase 2 splits it).
