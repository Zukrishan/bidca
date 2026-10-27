# ACTION-PLAN.md — current status (28 Sep 2026)

## Where it stands
Emergent-generated prototype on `main` @ `9ce8c71`. Most user-facing features exist (see
`docs/srs/02-functional.md`), but it is **not launchable**:

1. **Auctions never end.** No background closer; sniper bids are stored and never run (contradiction 002).
2. **No email at all.** SendGrid is a dependency but unused; no password reset.
3. **Cloudinary is a mock** that signs with `mock_api_secret`.
4. **Default admin password** `admin123` is seeded if `ADMIN_PASSWORD` is unset.
5. **`cookies.txt` is committed** (session cookie file).
6. The 15 Sep 2026 docs set was never committed and was lost; rebuilt here.

## Actions
| # | Action | Owner | Status |
|---|---|---|---|
| A1 | `git rm --cached cookies.txt`, add to `.gitignore`, rotate `JWT_SECRET` if it was real | integrator | open |
| A2 | Phase 1 (R1–R8) | acc1 build / acc2 review | **blocked** — agent launch needs user permission (see ASK-NOTES) |
| A3 | Client answers Q001–Q006 | user | open |
| A4 | Freeze API_CONTRACT v1 | integrator | after Phase 2 |
