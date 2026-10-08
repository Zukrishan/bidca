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
| 5 | Deploy (Q006) | sequential | smoke test on target | **ready, not deployed**: compose + Dockerfiles + `docs/DEPLOY.md`; blocked on Q006 (hosting) and B10 (secure cookies) |

## Phase 1 brief (for acc1)
Owns: `backend/` only (new code in `backend/app/closer.py`, `backend/app/email.py`, auth additions).
Must not change existing endpoint shapes in `API_CONTRACT.md`; may add the "Planned additions".
Closer: asyncio task started on startup, 30s loop, selects `listing_type=auction, status=active,
end_time<=now` with an atomic `find_one_and_update` status transition so it is idempotent.
Tests: the R1–R8 names above, in `backend/tests/test_p0.py`, using mongomock-motor or a test DB.

## Phase 1 brief (for acc2)
Read-only on code. Review the diff against R1–R9 and `AGENTS.md`, run the suite, report findings
to the integrator. Do not push.
