# 3. Non-functional requirements

- **NFR-01 SEO:** public routes (home, browse, listing detail, seller profile) server-rendered with
  real metadata and JSON-LD → Next.js port (Phase 4). Dashboard/admin may stay client-rendered.
  Private listings (FR-31) are never in the sitemap or indexable.
- **NFR-02 Simplicity:** the UI must be very simple (client, 15 Sep 2026).
- **NFR-03 Security:** no default admin password in production (`admin123` fallback must fail
  closed); no committed secrets; CORS from env only; CAPTCHA on signup and login; 12 h lockout
  after 5 failed logins; logout after inactivity; every emailed link expires (source L17–21).
- **NFR-04 Correctness under time:** auction close, sniper execution, the 24 h no-response check
  and reminder emails must be idempotent and survive restarts (driven by stored timestamps, not
  in-memory timers).
- **NFR-05 Ports:** API :8100, web :3100.
- **NFR-06 Time zone:** every time and countdown is shown in BC/Pacific time (`America/Vancouver`)
  and labelled as such (source L200).
- **NFR-07 No money:** BidCa never touches, holds, refunds or moves money. No feature, status
  name, copy or UI may suggest payment, escrow or payment protection; disputes are moderation only
  (source L129–131).
