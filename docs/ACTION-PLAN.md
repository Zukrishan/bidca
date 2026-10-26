# ACTION-PLAN.md — current status (26 Oct 2026)

## Update 26 Oct 2026 — client source
The client's feature list `docs/source/BIDCA.txt` is now the top source (`AGENTS.md`). The SRS was
rewritten to match it (FR-21–FR-35, NFR-06/07), conflicts with what was built are logged and
resolved in its favour (`docs/srs/contradictions/003`), and unclear points are Q007–Q015 — all answered or given provisional defaults the same day (hosting: DigitalOcean). Built
code is unchanged; the work is planned as Phase 9 (`docs/project_phases.md`, R30–R53).
Nothing is merged yet: PRs #4–#15 are still open and stacked.

## Where it stood (8 Oct 2026)
Emergent-generated prototype on `main` @ `9ce8c71`. Most user-facing features exist (see
`docs/srs/02-functional.md`), but it is **not launchable**:

1. **Auctions never end.** No background closer; sniper bids are stored and never run (contradiction 002). **Fixed:** `feature/p0-backend` (closer).
2. **No email at all.** SendGrid is a dependency but unused; no password reset. **Fixed:** `feature/p0-backend` (`send_email()`, forgot/reset).
3. **Cloudinary is a mock** that signs with `mock_api_secret`. **Fixed:** `feature/p0-backend` (503 when unset).
4. **Default admin password** `admin123` is seeded if `ADMIN_PASSWORD` is unset. **Fixed:** `feature/p0-backend` (refused when `ENV=production`).
5. **`cookies.txt` is committed** (session cookie file). **Fixed:** untracked in 43a725d.
6. The 15 Sep 2026 docs set was never committed and was lost; rebuilt here.

## Actions
| # | Action | Owner | Status |
|---|---|---|---|
| A1 | `git rm --cached cookies.txt`, add to `.gitignore`, rotate `JWT_SECRET` if it was real | integrator | **done** 43a725d; file still in git history, so rotating `JWT_SECRET` is the user's call |
| A2 | Phase 1 (R1–R8) | integrator → user | **built, 11/11 tests green** on `feature/p0-backend`; awaiting user manual test and PR review (no separate human review yet) |
| A3 | Client answers Q001–Q006 | user | open |
| A4 | Freeze API_CONTRACT v1 | integrator | **done** 8 Oct (docs/contract-v1), with D8/D9 fixes on `feature/p4-nextjs-public` |
| A5 | Merge docs PR, then Phase 1 PR | user | open |
| A6 | Frontend filters on `ended` (AdminPanel, SellerDashboard) but closed auctions are `sold`/`unsold` — tabs show nothing | Phase 9c (FR-23 replaces these tabs) | open |
| A7 | Phase 2 router split (`feature/p2-router-split`, PR #6, stacked on #5) | integrator → user | **built**; route table + OpenAPI identical, live API results identical, test_p0 11/11 |
| A8 | Phase 3 design proposal 1 (`docs/design/2026-10-07-stitch-simple/`) | client | awaiting sign-off (Q003); OpenDesign alternative pending (MCP not connecting) |
| A9 | Phase 4 Next.js port of public routes (`feature/p4-nextjs-public`, stacked on #6) | integrator → user | **built**, R22 green; started before Q003 sign-off at user request (ASK-NOTES 8 Oct) — design is a token swap |
| A10 | Phase 5 deploy | user | **ready, not deployed** — hosting is DigitalOcean (Q006, 26 Oct); `docs/DEPLOY.md` (on `feature/p4-nextjs-public`) still says "blocked on Q006" and gets a DigitalOcean section when deploy starts |
| A11 | Commit a `frontend/yarn.lock` (CRA has no lockfile; Docker builds are not reproducible) | integrator | open |
| A12 | Align docs to `docs/source/BIDCA.txt` (Phase 9a) | integrator | **done** 26 Oct on `docs/client-update` |
| A13 | Q004, Q006–Q015 | user | **answered / defaulted 26 Oct**: hosting DigitalOcean; team owns accounts + legal text; provisional defaults for the rest (ASK-NOTES). Show the defaults to the client; changes become new decisions |
| A16 | Team: SendGrid, Cloudinary, Twilio, Turnstile accounts; sender domain; DigitalOcean Droplet + Managed MongoDB | team | open |
| A17 | Team: Terms of Service, Privacy Policy, How It Works, About Us text; vehicle checklist content (client) | team / client | open |
| A14 | Phase 9b quick fixes (R30–R37) — none wait on questions | integrator | open |
| A15 | Hold the Phase 5 deploy until 9b–9d are built (the built app still says "Win & Pay" and has no transaction flow) | user | open |

## Backend backlog (found during the v1 contract freeze, 8 Oct 2026)
Not fixed yet; each needs its own PR with a test. Contract changes need a D-number.

| # | Issue | Priority |
|---|---|---|
| B1 | ~~Socket.IO rooms need no auth — anyone can `join_user_notifications` for any user id and receive their notifications~~ **fixed** on `feature/p6-security-hardening` — Socket.IO rooms bound to the authenticated user; origin locked | — |
| B2 | ~~`notification` socket emit fails~~ **fixed** (bid 500 on `feature/p4-nextjs-public`; closer pushes on `feature/p6-security-hardening`) | — |
| B3 | ~~Banned/suspended users keep access until token expiry (`get_current_user`, `/auth/refresh` don't check)~~ **fixed** on `feature/p6-security-hardening` — blocked on every request, refresh and socket; login no longer leaks ban state | — |
| B4 | ~~Best-offer accept marks the listing sold but creates no transaction/stats and emits nothing; doesn't check offer still pending / listing active~~ **fixed** on `feature/p6-security-hardening` — shared `complete_sale`: transaction, stats, notifications, atomic | — |
| B5 | ~~`auction_ended` has two payload shapes (buy-now vs closer)~~ **fixed** on `feature/p6-security-hardening` — one shape | — |
| B6 | ~~Several routes 500 on a malformed id (`ObjectId()` outside try): watch, report, saved-search delete, notification read, admin PUT/DELETE; watch doesn't check the listing exists~~ **fixed** on `feature/p8-backlog` — one `parse_object_id` helper; watch 404s for unknown listings | — |
| B7 | Bidding: ~~odd losing-bid record; best-offer on inactive listings; snipe max not validated~~ **fixed** on `feature/p8-backlog`. Still open: **anti-snipe end-time extension** — needs a product decision | decision |
| B8 | ~~`PUT /admin/listings/{id}` returns 404 when the status is unchanged (`modified_count == 0`)~~ **fixed** on `feature/p8-backlog` — `matched_count`; no re-notification | — |
| B9 | Auth responses differ in shape (register / login / me) | low |
| B10 | ~~Cookies `secure=False` — must be `True` behind HTTPS in production (Phase 5)~~ **fixed** on `feature/p6-security-hardening` — Secure when `ENV=production` | — |
| B11 | ~~CORS falls back to `http://localhost:3000` when `FRONTEND_URL` unset (should be :3100)~~ **fixed** on `feature/p6-security-hardening` — default :3100 | — |
| B12 | ~~Search `q` passed to Mongo `$regex` raw (`(` → 500, pattern injection)~~ **fixed** (escaped) | — |
| B13 | ~~Profile `active_listings` always 0; CRA profile's `seller_id` filter ignored by API~~ **fixed** (additive `seller_id` param) | — |
| B14 | ~~Price filters apply to `current_bid` only, so Buy-now listings don't match price ranges as expected~~ **fixed** on `feature/p8-backlog` — Buy-now price for fixed-price listings | — |
| B15 | ~~Saved searches can't store city or listing type (`SavedSearchCreate`)~~ **fixed** on `feature/p8-backlog` — `city` + `listing_type` stored and matched | — |
| B16 | ~~Detail page calls `/auth/me` from three client components; share one fetch~~ **fixed** on `feature/p8-backlog` — shared `getMe()` | — |
| B17 | ~~Buy now could sell the same item twice (no atomic status check) and never updated seller stats (looked up by string id)~~ **fixed** on `feature/p6-security-hardening` | — |
