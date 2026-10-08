# 2. Functional requirements

| ID | Requirement | Code status (main @ 9ce8c71) |
|---|---|---|
| FR-01 | Register with email, name, password, city, BC postal code (`V…`) | ✅ |
| FR-02 | Login/logout/refresh, JWT httpOnly cookies; 5 failures → 15 min lockout | ✅ |
| FR-03 | Password reset via emailed single-use link | ❌ missing |
| FR-04 | Email address verification on registration | ✅ `feature/p7-features` — single-use 24h link; bidding/selling/buying need a verified email |
| FR-05 | Create auction / fixed-price listing, ≤10 images, goes to `pending` | ✅ (images via Cloudinary **mock**) |
| FR-06 | Admin approve/reject/delete listings | ✅ |
| FR-07 | Browse/search/filter; featured, ending-soon | ✅ |
| FR-08 | Place bid ≥ current + increment table; proxy (max) bids | ✅ |
| FR-09 | Sniper bids execute N minutes before end | ⚠️ stored in `sniper_bids`, **never executed** |
| FR-10 | Auctions close automatically at `end_time`: winner set, reserve checked, status `sold`/`unsold` | ❌ **no background task** — auctions never end |
| FR-11 | Winner + seller notified (in-app + email) on close | ❌ depends on FR-10 |
| FR-12 | Buy It Now, Best Offer + seller respond | ✅ |
| FR-13 | Watchlist, saved searches | ✅ incl. alerts (in-app + email when a matching listing goes live) — `feature/p7-features` |
| FR-14 | Transactions + feedback/ratings | ✅ |
| FR-15 | Relist ended/unsold | ✅ |
| FR-16 | ID verification submit + admin review, badge | ✅ |
| FR-17 | Reports on listings, admin queue | ✅ |
| FR-18 | In-app notifications, read/read-all | ✅ |
| FR-19 | Transactional email (outbid, won, sold, approved, reset) | ❌ SendGrid in requirements, not wired |
| FR-20 | Buyer–seller messaging after sale | ✅ `feature/p7-features` — per-transaction threads, live, `/messages` |
