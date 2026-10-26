# project_phases.md — BidCa build plan

Generated **28 Sep 2026**. Scope `docs/srs/`, interface `docs/API_CONTRACT.md`, scoreboard
`docs/REQUIREMENTS.md`. Nothing advances past an unverified gate.

| Phase | What | Mode | Gate | Status (8 Oct 2026) |
|---|---|---|---|---|
| 0 | Docs rebuild, status audit | done (this commit) | human reads ACTION-PLAN | done (PR #4) |
| 1 | P0 backend: closer + sniper, notifications, email/Cloudinary env wiring, password reset, prod-safe admin seed | **maw builder/reviewer** — acc1 builds `feature/p0-backend`, acc2 reviews + runs tests | R1–R9 green, PR reviewed | built by the integrator (not maw), 11/11 green — PR #5, awaiting review |
| 2 | Split `server.py` into routers (no behaviour change) | sequential | full suite green, contract unchanged | built, contract + live results identical — PR #6 |
| 3 | Design phase — simple UI via Stitch + OpenDesign, proposals in `docs/design/` | parallel with 2 | client sign-off (Q003) | proposal 1 (Stitch) — PR #7, **awaiting client sign-off (Q003)**; OpenDesign not connected |
| 4 | Next.js port of public routes on :3100 (SSR/ISR, metadata, JSON-LD); contract frozen first | sequential | R22 | built ahead of Q003 at user request — `feature/p4-nextjs-public`, R22 green; contract v1 frozen (PR #8) |
| 5 | Deploy — **DigitalOcean** (Q006, 26 Oct 2026) | sequential | smoke test on target | **ready, not deployed**: compose + Dockerfiles + `docs/DEPLOY.md`; deploy after Phase 9b–9d; B10 fixed on `feature/p6-security-hardening` |
| 9 | Client source update (`docs/source/BIDCA.txt`) — see below | sequential, one PR per step | R30–R53 for its step | 9a done; 9b built — PR #17 (26 Oct 2026) |

## Phase 9 — client source update (added 26 Oct 2026)
Each step is its own branch + PR with tests; contract changes get a D-number. Deploy (Phase 5)
should wait for 9b–9d at least: launching with "pay" wording or no transaction flow would
contradict the source.

All open questions have an answer or a provisional default (26 Oct 2026), so **no step waits to
start**. "Live needs" is what must exist before that step works in production.

| Step | What | Requirements | Live needs |
|---|---|---|---|
| 9a | Docs aligned to the source; defaults decided | — | done (`docs/client-update`) |
| 9b | Quick fixes: no-money cleanup (shipping, `pending_payment`, copy), 12 h lockout, one search bar, newly added, Featured → Popular, bid confirmation, Pacific time, won/lost messages, outbid email, Best Offer fixed-price only | R30–R37 | SendGrid keys (team) |
| 9c | Transaction lifecycle: user page tabs, transaction page, Complete/Dispute, ratings after completion, no-response job, reminders | R38–R43 | Cloudinary keys for dispute proof (team) |
| 9d | Accounts and profiles: signup fields, phone verification, CAPTCHA, inactivity logout, rules screen, public profile, hide ID verification | R44–R47 | Twilio + Turnstile keys (team), Terms text (team) |
| 9e | Listings: form rules, drafts, category fields, vehicle disclosure + checklist, seller cancel penalty, listing cap | R48–R50, R53 | real checklist content (client) |
| 9f | Private listings | R51 | — |
| 9g | Terms / Privacy / How It Works / About pages | R52 | text (team) |
| 5 | Deploy to DigitalOcean (Q006) after 9b–9d | — | Droplet + Managed MongoDB, domain, all keys |
| later | FR-35 items (AI, paid featured/premium, image search, etc.) | — | client, Q004 |

## Phase 1 brief (for acc1)
Owns: `backend/` only (new code in `backend/app/closer.py`, `backend/app/email.py`, auth additions).
Must not change existing endpoint shapes in `API_CONTRACT.md`; may add the "Planned additions".
Closer: asyncio task started on startup, 30s loop, selects `listing_type=auction, status=active,
end_time<=now` with an atomic `find_one_and_update` status transition so it is idempotent.
Tests: the R1–R8 names above, in `backend/tests/test_p0.py`, using mongomock-motor or a test DB.

## Phase 1 brief (for acc2)
Read-only on code. Review the diff against R1–R9 and `AGENTS.md`, run the suite, report findings
to the integrator. Do not push.
