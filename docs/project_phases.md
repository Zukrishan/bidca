# project_phases.md — BidCa build plan

Generated **28 Sep 2026**. Scope `docs/srs/`, interface `docs/API_CONTRACT.md`, scoreboard
`docs/REQUIREMENTS.md`. Nothing advances past an unverified gate.

| Phase | What | Mode | Gate |
|---|---|---|---|
| 0 | Docs rebuild, status audit | done (this commit) | human reads ACTION-PLAN |
| 1 | P0 backend: closer + sniper, notifications, email/Cloudinary env wiring, password reset, prod-safe admin seed | **maw builder/reviewer** — acc1 builds `feature/p0-backend`, acc2 reviews + runs tests | R1–R9 green, PR reviewed |
| 2 | Split `server.py` into routers (no behaviour change) | sequential | full suite green, contract unchanged |
| 3 | Design phase — simple UI via Stitch + OpenDesign, proposals in `docs/design/` | parallel with 2 | client sign-off (Q003) |
| 4 | Next.js port of public routes on :3100 (SSR/ISR, metadata, JSON-LD); contract frozen first | sequential | R22 |
| 5 | Deploy (Q006) | sequential | smoke test on target |

## Phase 1 brief (for acc1)
Owns: `backend/` only (new code in `backend/app/closer.py`, `backend/app/email.py`, auth additions).
Must not change existing endpoint shapes in `API_CONTRACT.md`; may add the "Planned additions".
Closer: asyncio task started on startup, 30s loop, selects `listing_type=auction, status=active,
end_time<=now` with an atomic `find_one_and_update` status transition so it is idempotent.
Tests: the R1–R8 names above, in `backend/tests/test_p0.py`, using mongomock-motor or a test DB.

## Phase 1 brief (for acc2)
Read-only on code. Review the diff against R1–R9 and `AGENTS.md`, run the suite, report findings
to the integrator. Do not push.
