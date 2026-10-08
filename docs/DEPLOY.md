# Deploying BidCa (container setup)

> **Not deployed. Blocked on Q006 (hosting target) and B10 (cookies are `secure=False`).**
> This document describes a host-agnostic Docker setup only.

## Architecture

```
browser --> web (Next.js :3100) --+--> api (FastAPI + Socket.IO :8100) --> mongo (internal)
   |                              +--> cra (nginx :80, internal; Next fallback rewrite for non-public paths)
   +-----> api (direct, NEXT_PUBLIC_API_URL: XHR + Socket.IO + cookies)
```

- `web` serves the public SEO pages and proxies every other path to `cra` (the not-yet-ported React app).
- `web` talks to the API server-side via `API_URL` (internal); the browser uses `NEXT_PUBLIC_API_URL`.
- `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `REACT_APP_BACKEND_URL` and the `CRA_ORIGIN` rewrite
  destination are all **baked at build time**. Changing them requires `docker compose build`, not just a restart.
  (Next evaluates `rewrites()` during `next build` and stores the result in `routes-manifest.json`.)

## Build and run

```bash
cp .env.example .env        # edit: JWT_SECRET, ADMIN_PASSWORD, FRONTEND_URL, NEXT_PUBLIC_*
docker compose build
docker compose up -d
docker compose ps           # api should become healthy
```

Only `api` (8100) and `web` (3100) publish ports; `mongo` and `cra` are internal. Override the host ports
with `API_PORT` / `WEB_PORT` in `.env` (e.g. to run next to a dev setup); `NEXT_PUBLIC_API_URL` and
`FRONTEND_URL` must then use the same ports.

The `web` image uses Next's `output: "standalone"` (server bundle without the full `node_modules`).

## Environment

| Variable | Used by | Notes |
|---|---|---|
| `DB_NAME` | api | Mongo database name (compose sets `MONGO_URL=mongodb://mongo:27017`) |
| `JWT_SECRET` | api | Required. >= 32 random bytes (`openssl rand -hex 32`) |
| `FRONTEND_URL` | api | CORS origin. Must equal the public site origin exactly |
| `ENV` | api | `production` refuses the default admin password |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | api | Seed admin. Strong password required in production. Use a real domain: login validates the address and rejects reserved TLDs (`.test`, `.local`, `.localhost`), so such an admin is seeded but can never sign in |
| `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` | api | Optional; mock email if unset |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | api | Optional; mock uploads if unset |
| `NEXT_PUBLIC_API_URL` | web, cra (build) | Public API URL the browser calls. Also passed as `REACT_APP_BACKEND_URL` |
| `NEXT_PUBLIC_SITE_URL` | web (build) | Canonical public URL |
| `API_URL` | web (runtime) | Internal API URL (`http://api:8100`) |
| `CRA_ORIGIN` | web (build) | Rewrite target (`http://cra`) |

## Production checklist

- [ ] Terminate HTTPS in front (reverse proxy / platform edge). The api runs with `--proxy-headers`.
- [ ] **Fix B10**: auth cookies are currently `secure=False`. Must be `secure=True` (and a sensible `samesite`) before going live.
- [ ] `FRONTEND_URL` equals the public site origin (e.g. `https://bidca.ca`).
- [ ] Use same-site domains so cookies work: site `bidca.ca`, API `api.bidca.ca`.
- [ ] `ENV=production`, strong `ADMIN_PASSWORD`, fresh `JWT_SECRET`.
- [ ] Rotate `JWT_SECRET` if the session in `cookies.txt` was a real one (the file is untracked now, but it was committed earlier).
- [ ] MongoDB backups (volume snapshots or `mongodump` on a schedule; test a restore).
- [ ] Do not publish mongo; do not publish `cra`.
- [ ] `frontend/yarn.lock` is missing from the repo; commit one so builds are reproducible (the Dockerfile falls back to plain `yarn install`).

## Hosting options for Q006

- **Single VPS + docker compose + Caddy/nginx for TLS**: cheapest, simplest, you own backups and updates.
- **Railway / Render / Fly (containers) + MongoDB Atlas**: the Emergent prototype already deployed via Railway
  (`railway/*` branches), so an account may exist; managed TLS, deploys and DB backups; costs more, three or four services to wire, WebSockets and build-time args need checking per platform.

## Smoke test

Demo data for a non-production stack: `backend/scripts/seed_demo.py` (logs in as the seeded admin).

```bash
curl -fsS $API/api/health
SITE=https://bidca.ca API=https://api.bidca.ca node web/scripts/check-seo.mjs
```

### Last local run (8 Oct 2026)
Full stack built from this repo (`api` 250 MB, `web` 313 MB, `cra` 98 MB), `ENV=production`, seeded with
`seed_demo.py`: api healthy, default `admin123` login refused (401), `check-seo.mjs` 36/36 including
the CRA fallback. Right after a fresh start the home page can show cached empty sections for up to 30s.
