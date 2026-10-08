# ASK-NOTES.md — decisions asked and answered

| Date | Question | Answer |
|---|---|---|
| 15 Sep 2026 | Stack | Keep FastAPI + Mongo; port CRA → Next.js incrementally; ports 8100/3100 |
| 15 Sep 2026 | Design | Ours to choose, must be simple, Stitch + OpenDesign as design phases |
| 28 Sep 2026 | Missing docs set | Rebuild it |
| 28 Sep 2026 | Scope this round | P0 backend first; CRA stays for now |
| 28 Sep 2026 | maw split | acc1 builder, acc2 reviewer, Claude integrates |
| 28 Sep 2026 | Creds / branch | No creds — env-driven mocks; feature branch off main, PR |
| 28 Sep 2026 | maw runs | Launching `agy --dangerously-skip-permissions` under acc1/acc2 was blocked by the Claude Code permission classifier; needs explicit user allow |
| 8 Oct 2026 | Continue past Phase 3 gate? | User: "continue and complete the phases, I will check in the end" — Phase 4 started before client design sign-off (Q003); design tokens isolated so a different direction is a token swap |
| 8 Oct 2026 | Contract v1 | Frozen with two security fixes as decisions D8 (unapproved listings not public) and D9 (proxy max never exposed) |
| 8 Oct 2026 | Contract v1.1 | Search becomes plain text (was an unescaped regex — 500s and pattern injection); additive `seller_id` filter. Bug fixes, not a feature change |
| 8 Oct 2026 | Phase 5 | Prepared, not deployed: no hosting decision (Q006) or credentials; deploying is outward-facing and needs the user |
| 8 Oct 2026 | Next after Phase 5 | User: "continue" — security fixes, then FR-04/13/20 |
| 8 Oct 2026 | FR-04 gate (default, reversible) | Unverified accounts may browse, log in, watch and save searches; bidding, buying, offers, listing and relisting need a verified email. Accounts without the flag count as unverified (not launched; demo users verified by the seed script) |
| 8 Oct 2026 | FR-13 alerts | Trigger when a listing becomes active; plain-text match on title/description + category + price; once per user per listing; in-app + email; per-search on/off |
| 8 Oct 2026 | FR-20 messaging | One thread per transaction, buyer + seller only, plain text, rate-limited; one unread notification/email per thread |
| 8 Oct 2026 | Dev email bodies | Logged only with `EMAIL_LOG_BODIES=1` and never in production (bodies carry tokens) |
