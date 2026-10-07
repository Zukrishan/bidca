# 3. Non-functional requirements

- **NFR-01 SEO:** public routes (home, browse, listing detail, seller profile) server-rendered with
  real metadata and JSON-LD → Next.js port (Phase 4). Dashboard/admin may stay client-rendered.
- **NFR-02 Simplicity:** the UI must be very simple (client, 15 Sep 2026).
- **NFR-03 Security:** no default admin password in production (`admin123` fallback must fail
  closed); no committed secrets; CORS from env only.
- **NFR-04 Correctness under time:** auction close and sniper execution must be idempotent and
  survive restarts (driven by stored `end_time`, not in-memory timers).
- **NFR-05 Ports:** API :8100, web :3100.
