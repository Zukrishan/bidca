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
