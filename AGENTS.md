# AGENTS.md — cross-tool process rules

Applies to any AI coding tool working in this repo (Claude Code, agy under maw, Codex, Cursor).
`CLAUDE.md` carries the architecture; this file carries the **process**.

## Source-of-truth hierarchy

When two sources disagree, the higher one wins. Do not silently reconcile — log it in
`docs/srs/contradictions/`.

0. **`docs/source/`** — the client's own documents (`BIDCA.txt`, 26 Oct 2026). Outranks everything.
   Never edit them; restate them in `docs/srs/`. Where a source is unclear, open a question in
   `docs/srs/open-questions/` — do not guess. A provisional default needs the user's OK and is logged in `docs/ASK-NOTES.md`.
1. **`docs/srs/`** — scope, restating `docs/source/` as numbered requirements; earlier inputs
   (`memory/PRD.md`, client direction) only where the source is silent. There is no signed SRS
   yet (`open-questions/Q001`).
2. **`docs/API_CONTRACT.md`** — the interface between `backend/` and `frontend/`. Freeze before the
   Next.js port begins.
3. **`docs/REQUIREMENTS.md`** — numbered acceptance checklist.
4. **`CLAUDE.md`** — architecture and conventions.
5. **`docs/project_phases.md`** — build plan with review gates.
6. Application code, `docs/USER_GUIDE.md`, `memory/PRD.md`, `test_result.md` (Emergent-era).
7. **`docs/design/`** — proposals only. Never built from directly.

## Hard boundaries

- **Ports: API :8100, web :3100.** Never :3000/:8000/:8001 — they collide with first-food, CLS RMS
  and cpos in this workspace.
- **BC only** — postal codes starting with `V`. Do not widen without a recorded decision.
- **No money, ever** (client source, NFR-07): BidCa never touches, holds, refunds or moves money,
  and no code, status name or copy may suggest payment, escrow or payment protection. Fees for
  platform features (featured, premium, listings) wait on `open-questions/Q004`. Do not scaffold
  Stripe "for later".
- **Every listing needs admin approval** before it is public.
- **Times shown to users are BC/Pacific** (`America/Vancouver`), labelled; storage stays UTC.
- **Never commit credentials or session files.** `cookies.txt` was untracked in 43a725d — see
  `docs/ACTION-PLAN.md` A1.
- Design is ours and **must be simple**; it goes through its own phase with a review gate
  (`open-questions/Q003`).

## Branch model

Work on `feature/*` or `docs/*` branches off `main`, PR into `main`. The `v1`/`v10`/`railway/*`/
`claude/*` remote branches are Emergent/Railway artefacts — read, don't build on them.

## Multi-agent (maw)

Builder/reviewer split: **acc1 builds** on a feature branch in its own worktree, **acc2 reviews and
tests** it, the Claude Code session integrates and owns the gate. Briefs must name the files owned,
the contract not to violate, and the named tests (see `docs/project_phases.md`).
