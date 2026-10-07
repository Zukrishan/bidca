# ACTION-PLAN.md — current status (7 Oct 2026)

## Where it stands
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
| A4 | Freeze API_CONTRACT v1 | integrator | after Phase 2 |
| A5 | Merge docs PR, then Phase 1 PR | user | open |
| A6 | Frontend filters on `ended` (AdminPanel, SellerDashboard) but closed auctions are `sold`/`unsold` — tabs show nothing | Phase 4 | open |
