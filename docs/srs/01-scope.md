# 1. Scope

Source: `docs/source/BIDCA.txt` (26 Oct 2026), then earlier inputs where it is silent.

**Purpose.** A trusted, local, peer-to-peer auction and fixed-price marketplace for BC residents.
Buyer and seller meet and exchange directly; **BidCa never touches, holds, refunds or moves money**
(not a bank, escrow or payment processor). Trust comes from BC-only, phone-verified, 19+ accounts,
admin-approved listings, public ratings, and dispute moderation.

**Users.** Buyer, Seller (same account), Admin.

**In scope:**
- Accounts: BC city + postal code, email and phone verification (one account per phone), 19+,
  Terms acceptance, CAPTCHA, 12h lockout after 5 failed logins, inactivity logout, email-only reset.
- Listings: auction (1, 3, 5, 7 or 10 days), auction + Buy-It-Now, fixed price, and private
  (invite-only) listings; admin approval; drafts; category-specific fields; no shipping; price
  locked once bidding starts; sellers may cancel, with a suspension if there were bids.
- Bidding: proxy, sniper, bid confirmation, instant outbid alerts, clear won/lost messaging.
- After a win: a private transaction page (chat, order summary, two-sided Complete, Dispute with
  proof), reminder emails, 24h no-response penalty, then ratings (green / yellow / red) + comments.
- Public profiles with ratings, comments, tiers, verified badge and preferred exchange method.
- Vehicles: printable buyer inspection checklist.
- Watchlist, saved searches + alerts, notifications (in-app + email), reports, admin moderation,
  real-time bid updates, SEO-indexable public pages, Terms / Privacy / How It Works / About pages.
- Free launch period: first 3 months from launch, 30 listings per user per month (Q015).
- Hosting: DigitalOcean (Q006).

Unclear points in the source have provisional defaults (26 Oct 2026) — see the Settings table in
`02-functional.md` and the question files; the client may change them.

**Later (named in the source, not this build):** AI chat bot, paid featured listings, premium
members on top, smart (semantic) search, image search, scam-listing detection, prohibited-content
auto-check, description character counter, AI description help, AI category suggestion, duplicate
listing detection, cookie consent banner (only if tracking is added, with client approval).

**Out of scope:** any payment processing, escrow, refunds or holding funds (source: "never");
charging fees for featured/premium/listings until Q004 is answered; native mobile apps; bilingual
EN/FR (Q005).
