# Q010 — Durations the source leaves open
Status: **Decided — provisional default (26 Oct 2026)**, chosen by us so building can continue; the client may change it, and a change is just a new decision row in `docs/ASK-NOTES.md`.

Every value is a setting (env var), not hard-coded.

| Rule | Default |
|---|---|
| Lock after a winner ignores the chat for 24 h (L103 "a few hours") | **6 h** |
| Reminder emails while a transaction is open (L134 "every few hours") | **every 6 h**, at most 10 reminders, then admins are alerted |
| Seller cancels a listing that has bids (L75 "a couple days based on history") | 1st time: **2 days** suspended; 2nd within 12 months: **7 days**; 3rd within 12 months: suspended until an admin reviews |
| Inactivity auto-logout (L21) | **30 min** without activity |
| Auction durations (source silent) | keep what is built: **1, 3, 5, 7 or 10 days** (the old 24/48/72 h text was stale) |
