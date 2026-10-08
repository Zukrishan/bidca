# REQUIREMENTS.md — acceptance checklist

Tick only when the named test passes. IDs map to `docs/srs/02-functional.md`.

## Launch-blocking (P0)
- [x] R1 (FR-10) Auction past `end_time` is closed within 60s; `sold` to highest bidder if reserve met, else `unsold`. Test: `test_auction_closes_sold`, `test_auction_closes_unsold_reserve_not_met`, `test_auction_closes_no_bids` — passing on feature/p0-backend (7 Oct 2026)
- [x] R2 (FR-10) Closing is idempotent — two closer passes produce one transaction and one notification set. Test: `test_close_idempotent` — passing on feature/p0-backend (7 Oct 2026)
- [x] R3 (FR-09) Due sniper bids execute before close, respecting max bid. Test: `test_sniper_bid_executes` — passing on feature/p0-backend (7 Oct 2026)
- [x] R4 (FR-11) Winner and seller get in-app notifications + email on close. Test: `test_close_notifies_winner_and_seller` — passing on feature/p0-backend (7 Oct 2026)
- [x] R5 (FR-19) Email goes through one `send_email()` that uses SendGrid when `SENDGRID_API_KEY` is set and logs otherwise. Test: `test_email_mock_fallback` — passing on feature/p0-backend (7 Oct 2026)
- [x] R6 (FR-05) Cloudinary signature endpoint returns 503 when unconfigured instead of signing with a mock secret. Test: `test_cloudinary_unconfigured` — passing on feature/p0-backend (7 Oct 2026)
- [x] R7 (FR-03) Forgot/reset password: no enumeration, single-use, expiring token. Test: `test_password_reset_flow`, `test_reset_token_single_use` — passing on feature/p0-backend (7 Oct 2026)
- [x] R8 (NFR-03) Server refuses to seed admin with default password when `ENV=production`. Test: `test_no_default_admin_in_prod` — passing on feature/p0-backend (7 Oct 2026)
- [x] R9 (NFR-03) `cookies.txt` removed from git and ignored. — done in commit 43a725d (still in git history)

## Already working (verify once against the contract)
- [ ] R10 FR-01, FR-02 auth · [ ] R11 FR-05–08 listings & bidding · [ ] R12 FR-12–18

## Later
- [x] R20 FR-04 email verification (`tests/test_email_verification.py`) · [x] R21 FR-20 messaging (`tests/test_messages.py`) · [x] R22 NFR-01 Next.js SEO port — `web/scripts/check-seo.mjs` all pass (dev + `next start`, 8 Oct 2026, `feature/p4-nextjs-public`)
- [x] R23 FR-13 saved-search alerts (`tests/test_search_alerts.py`)
