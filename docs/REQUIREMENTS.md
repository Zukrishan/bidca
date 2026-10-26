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

## Client source update (`docs/source/BIDCA.txt`, 26 Oct 2026) — Phase 9
R30–R37: `tests/test_client_9b.py` passing on `feature/p9b-quick-fixes` (26 Oct 2026, 86/86); web parts (R33, R34, R35 "You won!") build but are not yet browser-tested.
Tests are named when each item is built. Q-numbers point to the provisional default each item uses.
- [x] R30 (FR-14, NFR-07) No money anywhere: no `pending_payment` status, no shipping fields/filter, no "pay"/escrow copy; `check-seo` copy check extended to the CRA pages
- [x] R31 (FR-02) 5 failed logins → 12 h lockout
- [x] R32 (FR-07) One search bar on the home page; "newly added" section shows all new active listings; bid-count "Featured" renamed "Popular" (Q004)
- [x] R33 (FR-08) Bid confirmation step before a bid is sent
- [x] R34 (NFR-06) All user-facing times in Pacific time and labelled
- [x] R35 (FR-11) Every bidder told "You won!" / "you didn't win" at close; winner and seller emailed immediately (R4 covers the winner/seller part)
- [x] R36 (FR-32) Outbid alert by email as well as in-app (SMS/push: Q011)
- [x] R37 (FR-12, FR-28) Best Offer refused on auctions; no way to change price once bidding started
- [ ] R38 (FR-23) User page tabs Selling / Current Bids / Successfully Completed; won items in Current Bids with Message (closes A6)
- [ ] R39 (FR-24) Transaction page: buyer + seller only; order summary; Complete only when both press it
- [ ] R40 (FR-24) Dispute needs proof upload, blocks Complete; only the opener can cancel; admin dispute queue
- [ ] R41 (FR-25) Rating prompt after completion only; green/yellow/red; one per user per transaction; public
- [ ] R42 (FR-26) 24 h no-response job: lock + rating effect, idempotent (Q010, Q013)
- [ ] R43 (FR-27) Reminder emails while open, stop on Completed/Cancelled/Disputed (Q010)
- [ ] R44 (FR-01) Signup: city dropdown, phone verification (one account per phone), 19+, T&C, CAPTCHA (Q011, Q014)
- [ ] R45 (FR-02, NFR-03) CAPTCHA on login; inactivity logout (Q010)
- [ ] R46 (FR-21) Rules / how P2P works screen after signup
- [ ] R47 (FR-22) Public profile fields, phone-verified badge after 2 completed transactions, tiers, exchange method, delete account (Q009, Q013)
- [ ] R48 (FR-05) Listing form: required fields, dependent subcategory, drag-and-drop images, drafts, category-specific fields
- [ ] R49 (FR-29) Seller cancel during bidding → suspension (Q010, Q012)
- [ ] R50 (FR-30) Vehicles-only inspection checklist download, no login (Q008)
- [ ] R51 (FR-31) Private listings: invitees only, hidden everywhere public, not in sitemap (Q007)
- [ ] R52 (FR-33) Terms, Privacy, How It Works, About pages linked in the footer (Q014)
- [ ] R53 (FR-34) 30 listings per user per month (Q015)
