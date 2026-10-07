# 002 — PRD marks "Auto-close at auction end time" as implemented; code has no closer

`memory/PRD.md` §Bidding ✅ "Auto-close at auction end time". `server.py` has no background task,
scheduler or query on `end_time < now`; bids are only refused after end. Sniper bids are likewise stored and never run.
**Resolution:** code is the truth about behaviour; FR-09/FR-10 marked ❌ and scheduled in Phase 1.
