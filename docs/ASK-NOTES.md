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
