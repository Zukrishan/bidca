# BidCa.ca

Local auction + marketplace for British Columbia residents. Read `AGENTS.md` first (process and
what outranks what), then `docs/ACTION-PLAN.md` for current status.

## Layout

| Path | What |
|---|---|
| `backend/server.py` | thin assembly: FastAPI app, startup/shutdown, CORS, Socket.IO ASGI wrapper (`app`) |
| `backend/app/routers/*.py` | all `/api` endpoints, one router per area, mounted in order in `server.py` (route order matters) |
| `backend/app/{db,security,constants,models,realtime,helpers,seed}.py` | shared backend code |
| `backend/app/closer.py`, `email.py` | 30s auction closer + sniper executor; `send_email()` (SendGrid or log) |
| `backend/tests/` | pytest with mongomock-motor (`conftest.py` shares one client); `test_bidca_features.py` + `backend_test.py` are Emergent-era and need a live server |
| `backend/scripts/seed_demo.py` | demo data through the API (dev only) |
| `web/` | Next.js 16 public pages (`/`, `/auctions`, `/auctions/[id]`, `/users/[id]`, sitemap, robots) on :3100; everything else falls back to CRA |
| `frontend/` | React 19 CRA via craco — the not-yet-ported routes (login, dashboard, sell, admin) on :3101 behind `web` |
| `docker-compose.yml`, `*/Dockerfile`, `.env.example` | container setup — see `docs/DEPLOY.md` |
| `memory/PRD.md` | Emergent PRD — rank 6, superseded by `docs/srs/` |
| `docs/` | governance set — see `AGENTS.md` |

## Run

```bash
cd backend && uvicorn server:app --port 8100 --reload   # needs MONGO_URL, DB_NAME, JWT_SECRET, FRONTEND_URL=http://localhost:3100
cd frontend && PORT=3101 WDS_SOCKET_PORT=3101 REACT_APP_BACKEND_URL=http://localhost:8100 npx craco start
cd web && npm run dev                                    # :3100; NEXT_PUBLIC_API_URL / CRA_ORIGIN default to :8100 / :3101
```

Open http://localhost:3100 — it serves the public pages and proxies the rest to CRA.
`app` is the Socket.IO ASGI wrapper (`/api/socket.io`); `fastapi_app` is the inner app.
Cloudinary and SendGrid read env vars and fall back to mocks when unset.
Whole stack in containers: `cp .env.example .env && docker compose up --build`.

## Test

The host Python has no venv/pip; backend tests run in Docker. Build the image once (slow mirror —
~20 min) from `backend/requirements.txt` + `mongomock-motor pytest-asyncio`, then:

```bash
docker run --rm -v "$PWD/backend:/src:ro" bidca-backend-test bash -c 'cp -r /src/. /app && python -m pytest tests -q --ignore=tests/test_bidca_features.py'
cd web && npm run check:seo        # crawler-view gate; needs API + seeded data (+ CRA for the fallback check)
```

## Conventions

- Mongo `_id` is stringified in responses; timestamps are ISO-8601 UTC strings.
- Auth is JWT in httpOnly cookies (`access_token`, `refresh_token`); `get_current_user` dependency.
- New endpoints go in a router under `backend/app/routers/`; keep `server.py` thin.
- Public listing data never includes `pending`/`rejected` listings or `highest_bidder_max_bid`
  (contract D8, D9). Search text is plain text (escaped), never a regex.
- Web: semantic design tokens only (`app/globals.css`, proposal 1 pending Q003); JSON-LD only via
  `components/JsonLd.jsx` (escapes user content); links to CRA routes are plain `<a>`, not `next/link`.
