# API_CONTRACT.md — BidCa backend ⇄ frontend

Status: **v1 — frozen 8 Oct 2026**
Change rule: after freeze, any change needs a recorded decision in `docs/ASK-NOTES.md` and a `## Changelog` entry; additive optional fields are allowed, renames/removals are not.

Base path `/api`. Consumers: React CRA app and the Next.js public app. Source: `backend/app/routers/*.py` (mounted in `server.py`).

## Locked decisions
- D1 Ports: API :8100, web :3100.
- D2 IDs are strings; timestamps are ISO-8601 UTC strings.
- D3 Errors: `{"detail": "..."}` with the HTTP status (FastAPI default; 422 for body/query validation).
- D4 Listing status set: `pending | approved | rejected | active | ended | sold | unsold`. (`closing` is a transient internal value set by the closer; clients must tolerate it.)
- D5 Auth: httpOnly cookies `access_token` (1h) and `refresh_token` (7d), `SameSite=Lax`, path `/`. Clients send credentials (`credentials: "include"` / `withCredentials`). `Authorization: Bearer <access>` is also accepted. CORS allows only `FRONTEND_URL`.
- D6 Pagination for `GET /listings`: `{listings, total, page, pages}`; `page` is 1-based, `limit` default 24. Admin lists return `{<items>, total, page}` (no `pages`).
- D7 Money is CAD, JSON number (float).
- D8 Public visibility: listings with status `pending` or `rejected` are visible only to their seller and admins. Public set is `active | sold | unsold | ended`.
- D9 Secret proxy max: `highest_bidder_max_bid` is never returned to non-admins (listing detail, lists, related items, watchlist, dashboard). Bidders see their own max only in bid responses (`your_max_bid`).

Auth column: `public` = no login; `optional` = login changes the response; `user` = login required (401 `Not authenticated`/`Token expired`/`Invalid token`); `admin` = role `admin` (403 `Admin access required`).

## Auth
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/auth/register` | public | body: `email`, `password`, `full_name`, `city`, `postal_code` (req); `province` (opt, default British Columbia) | `{id,email,full_name,city,role,verification_status}` + sets cookies | 400 non-BC postal code (must start with V) / email taken |
| POST | `/auth/login` | public | body: `email`, `password` (req) | `{id,email,full_name,city,role,verification_status,verification_badge,seller_rating,total_ratings,positive_percentage}` + sets cookies | 401 invalid credentials; 403 banned/suspended; 429 after 5 failures (15 min lock, per email) |
| POST | `/auth/logout` | public | — | `{message}` | clears both cookies |
| GET | `/auth/me` | user | — | user document (no `password_hash`), `_id` string | 401 |
| POST | `/auth/refresh` | public | cookie `refresh_token` | `{message}` + new `access_token` cookie | 401 missing/invalid refresh token or user |

## Password reset
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/auth/forgot-password` | public | body: `email` (req) | `{message}` | always 200 (no user enumeration); emails link `FRONTEND_URL/reset-password?token=…` |
| POST | `/auth/reset-password` | public | body: `token`, `password` (req) | `{message}` | 400 `Invalid or expired reset token`; token single-use, 1h expiry, stored sha256-hashed |

## Uploads
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/cloudinary/signature` | user | query: `resource_type` (`image`\|`video`, default image), `folder` (default `bidca_uploads`) | `{signature,timestamp,cloud_name,api_key,folder,resource_type}` | 503 `Cloudinary is not configured` when env unset |

## Catalog / reference
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/categories` | public | — | `{categories: {name: [subcategory]}}` | |
| GET | `/cities` | public | — | `{cities: [string]}` | BC cities |
| GET | `/provinces` | public | — | `{provinces: [string]}` | |
| GET | `/popular-keywords` | public | — | `{keywords: [string]}` | static list |

## Listings
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/listings` | user | body: `title`,`category`,`description`,`city`,`starting_bid` (req); `subcategory`,`reserve_price`,`buy_it_now_price`,`province`(BC),`duration_days` (1\|3\|5\|7\|10, 7),`images` ([]),`condition` (new\|like_new\|good\|fair\|poor, good),`shipping_cost` (0),`shipping_from`,`accepts_best_offer` (false),`listing_type` (auction\|fixed_price\|auction_bin, auction) | listing object (see below, without computed fields), status `pending` | **201**; 400 reserve < starting bid / BIN <= starting bid |
| GET | `/listings` | public | query (all opt): `q`,`category`,`subcategory`,`condition`,`province`,`city`,`min_price`,`max_price` (on `current_bid`),`listing_type`,`seller_rating`,`free_shipping`,`status` (default `active`),`sort` (`ending_soonest`\|`newly_listed`\|`lowest_price`\|`highest_price`\|`most_bids`; unknown → ending_soonest),`page` (1),`limit` (24) | `{listings,total,page,pages}` | **changed in v1 (D8)**: `status` must be `active\|sold\|unsold\|ended`, otherwise 400 |
| GET | `/listings/featured` | public | — | `{listings}` (max 8, active auctions by bid_count) | |
| GET | `/listings/ending-soon` | public | — | `{listings}` (max 12, active auctions ending within 6h) | |
| GET | `/listings/{listing_id}` | optional | path: `listing_id` | listing object with computed fields (see below) | **changed in v1 (D8)**: 404 for `pending`/`rejected` unless caller is the seller or an admin; also 404 bad id; increments `views_count` |

### Listing object (`GET /listings/{id}`)
| Field | Type | Notes |
|---|---|---|
| `_id` | string | |
| `title`,`description`,`category`,`subcategory` | string / null | |
| `city`,`province` | string | |
| `images` | string[] | Cloudinary URLs |
| `condition` | string | new\|like_new\|good\|fair\|poor |
| `listing_type` | string | auction\|fixed_price\|auction_bin |
| `starting_bid`,`current_bid` | number | CAD |
| `reserve_price` | number / null | |
| `reserve_met` | bool | |
| `buy_it_now_price` | number / null | |
| `accepts_best_offer` | bool | |
| `shipping_cost`,`shipping_from` | number, string | |
| `duration_days`,`start_time`,`end_time` | int, ISO, ISO | |
| `seller_id` | string | |
| `seller_name`,`seller_city`,`seller_verified`,`seller_rating`,`seller_total_ratings`,`seller_positive_pct` | denormalised at creation | may be stale; prefer `seller_info` |
| `bid_count`,`bid_increment` | int, number | |
| `highest_bidder_id`,`highest_bidder_name` | string / null | `highest_bidder_max_bid` exists in the DB but is **admin-only** (D9) |
| `status` | string | D4 |
| `winner_id`,`sold_price` | string / null, number / null | |
| `sold_via` | string (opt) | `buy_it_now` \| `best_offer`; present only after sale |
| `closed_at` | ISO (opt) | set by closer on unsold/sold |
| `watchers_count`,`views_count` | int | |
| `created_at` | ISO | |
| `bid_history` | `[{amount,bidder_name,created_at,is_auto_bid}]` | last 50, newest first; `bidder_name` masked (`J***n`) unless caller is seller or that bidder |
| `is_watching` | bool | false when anonymous |
| `is_seller` | bool | false when anonymous |
| `related_items` | listing[] (max 6) | same category, active, excludes self (raw documents) |
| `seller_info` | `{full_name,city,seller_rating,total_ratings,positive_percentage,verification_badge,total_sales,member_since}` | omitted if seller missing |

## Bidding
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/listings/{listing_id}/bid` | user | body: `max_bid` (req, proxy max) | `{message,current_bid,your_max_bid,is_winning,reserve_met}`; raising own max → `{message,current_bid,your_max_bid}` | 400 not active / fixed-price / ended / own auction / below minimum / max not higher than current max; 404 |
| POST | `/listings/{listing_id}/sniper-bid` | user | body: `max_bid` (req), `minutes_before_end` (1\|2\|3\|5\|10, 5) | `{message}` | 400 listing not active/not found / own auction / time already passed; executed by closer |
| POST | `/listings/{listing_id}/buy-now` | user | — | `{message,price}` | 400 not active / no BIN price / own listing; 404; ends listing as `sold` |

## Offers
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/listings/{listing_id}/best-offer` | user | body: `offer_amount` (req), `message` (opt) | `{message,offer_id}` | 400 offers not accepted / own listing / listing not found |
| PUT | `/offers/{offer_id}/respond` | user (seller) | query: `action` (`accept`\|`decline`\|`counter`, req), `counter_amount` (req for counter) | `{message}` | 403 not seller; 404; 400 counter without amount |

## Watchlist
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/listings/{listing_id}/watch` | user | — | `{watching,message}` | toggle |
| GET | `/users/me/watchlist` | user | — | `{watchlist: listing[]}` | |

## Saved searches
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/saved-searches` | user | body: `name`,`query` (req); `category`,`min_price`,`max_price` (opt) | `{message,id}` | |
| GET | `/saved-searches` | user | — | `{saved_searches: [{_id,user_id,name,query,category,min_price,max_price,notify,created_at}]}` | |
| DELETE | `/saved-searches/{search_id}` | user | — | `{message}` | own only; always 200 |

## Feedback
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/transactions/{transaction_id}/feedback` | user | body: `rating` (positive\|neutral\|negative), `comment` (req) | `{message}` | 403 not a party; 400 already left; 404 |
| GET | `/users/{user_id}/feedback` | public | query: `page` (1), `limit` (20) | `{feedback: [...], total}` | feedback received by the user |

## User dashboard
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/users/me/bids` | user | — | `{bids: listing[]}` each + `my_max_bid`,`is_winning` | one entry per listing |
| GET | `/users/me/listings` | user | query: `status` (opt, any value) | `{listings}` | includes `pending`/`rejected` (own) |
| GET | `/users/me/purchases` | user | — | `{purchases: [transaction + listing]}` | |
| GET | `/users/me/sales` | user | — | `{sales: [transaction + listing + buyer_name]}` | |
| GET | `/users/me/seller-stats` | user | — | `{active_listings,pending_listings,sold_listings,unsold_listings,total_watchers,total_views,total_sales,total_revenue,seller_rating,total_ratings,positive_percentage}` | |
| POST | `/listings/{listing_id}/relist` | user (seller) | query: `duration_days` (int, 7) | `{message}` | 403 not seller; 400 status not ended/unsold; 404; goes back to `pending` |

## Notifications
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/notifications` | user | query: `limit` (50) | `{notifications: [{_id,user_id,type,message,listing_id,read,created_at}], unread_count}` | newest first |
| PUT | `/notifications/{notification_id}/read` | user | — | `{message}` | own only |
| PUT | `/notifications/read-all` | user | — | `{message}` | |

## Verification
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/verification/submit` | user | body: `government_id_url`, `selfie_url` (req) | `{message}` | 400 already verified |
| GET | `/verification/status` | user | — | `{verification_status,verification_badge,submission}` | `submission` latest or null |

## Reports
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| POST | `/listings/{listing_id}/report` | user | body: `reason`,`description` (req) | `{message}` | 404 |

## Admin
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/admin/stats` | admin | — | `{total_users,total_listings,active_auctions,pending_listings,pending_verifications,total_bids,total_transactions,pending_reports,total_gmv,platform_revenue}` | |
| GET | `/admin/listings` | admin | query: `status`, `page` (1), `limit` (20) | `{listings,total,page}` | sees all statuses |
| PUT | `/admin/listings/{listing_id}` | admin | body: `status` (D4 set, opt) | `{message}` | 400 no updates; 404; notifies seller |
| DELETE | `/admin/listings/{listing_id}` | admin | — | `{message}` | 404; also deletes bids |
| GET | `/admin/users` | admin | query: `search`, `page` (1), `limit` (20) | `{users,total,page}` | no `password_hash` |
| PUT | `/admin/users/{user_id}` | admin | body (opt): `verification_status` (unverified\|pending\|verified), `is_suspended`, `is_banned` | `{message}` | 400 no updates; 404 |
| GET | `/admin/verifications` | admin | query: `status` (pending), `page`, `limit` | `{verifications,total,page}` | |
| PUT | `/admin/verifications/{verification_id}` | admin | query: `status` (`approved`\|`rejected`, req) | `{message}` | 404; notifies user |
| GET | `/admin/reports` | admin | query: `status` (pending), `page`, `limit` | `{reports,total,page}` | |

## Profile
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/users/{user_id}/profile` | public | — | `{id,full_name,city,province,verification_badge,seller_rating,total_ratings,positive_percentage,total_sales,active_listings,member_since}` | 404 |

## Health
| Method | Path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| GET | `/` | public | — | `{message,status}` | |
| GET | `/health` | public | — | `{status: "healthy"}` | |

## Socket.IO
Path `/api/socket.io`. CORS open (`*`). No authentication on connect or room join.

| Direction | Event | Payload | Notes |
|---|---|---|---|
| client → server | `join_auction` | `{auction_id}` | joins room `auction_{auction_id}` |
| client → server | `leave_auction` | `{auction_id}` | leaves that room |
| client → server | `join_user_notifications` | `{user_id}` | joins room `user_{user_id}` |
| server → client | `bid_update` | `{listing_id,current_bid,bid_count,bid_increment,reserve_met,bidder_name}` | room `auction_{id}`; `bidder_name` is first letter + `***` |
| server → client | `auction_ended` | closer: `{listing_id,status:"sold",sold_price,winner_id}` or `{listing_id,status:"unsold"}`; buy-now: `{listing_id,sold_via:"buy_it_now",price}` | room `auction_{id}` |
| server → client | `notification` | `{user_id,type,message,listing_id,read,created_at}` | room `user_{user_id}`; same shape as `GET /notifications` items |

## Background closer
Runs every 30s in the API process (idempotent):
- Executes due sniper bids (`execute_at <= now`, status `pending` → `executed`) as proxy bids.
- Closes due auctions (`auction`/`auction_bin`, status `active`, `end_time <= now`) via transient `closing` → `sold` (reserve met, has winner) or `unsold`.
- On close: creates the transaction (`pending_payment`) for sold items, notifies winner and seller, emails both, emits `auction_ended`.

## Planned changes — client source (26 Oct 2026, not built)
`docs/source/BIDCA.txt` changes parts of this contract. Everything above still describes the built
API; each change below gets a D-number and a changelog entry when it is built (Phase 9).
- **Removals/renames (breaking):** `shipping_cost`, `shipping_from` and the `free_shipping` filter go (FR-05); transaction status `pending_payment` is replaced by a lifecycle `open → completed | disputed | cancelled` (FR-14, FR-24); Best Offer 400 on auctions (FR-12).
- **Changed:** login lockout 15 min → 12 h (FR-02); `POST /transactions/{id}/feedback` only after `completed`, ratings shown as green/yellow/red (FR-25); `listing_type` gains `private` (FR-31) — private listings never appear in public lists, search, featured, ending-soon or the sitemap.
- **New:** register fields (phone, age 19+ confirmation, Terms acceptance, CAPTCHA token, optional picture); phone verification; transaction complete / dispute (with proof) / cancel-dispute and an admin dispute queue; listing drafts and category-specific fields; private-listing invites (user or link); seller cancel; profile fields (display name, exchange method, tiers) and delete account; outbid email.

## Changelog
- **v1.4 (8 Oct 2026)** — bug fixes / additive (`feature/p8-backlog`): malformed ids → 404 on watch, report, notification read and admin updates; `POST /listings/{id}/watch` 404 for unknown listings; best offer 400 when the listing isn't active or doesn't accept offers; snipe 400 below the minimum next bid; `PUT /admin/listings/{id}` and `/admin/users/{id}` 200 when unchanged; `min_price`/`max_price` use `buy_it_now_price` for `fixed_price`; saved searches accept optional `city`, `listing_type`.
- **v1.3 (8 Oct 2026)** — FR-04 / FR-13 / FR-20, additive (`feature/p7-features`):
  - D10 Email verification: users have `email_verified` (missing = false). `POST /auth/verify-email` `{token}` (public) → 200 `{message}` / 400 `Invalid or expired verification link` (single use, 24h). `POST /auth/resend-verification` (user) → 200 / 400 `Email already verified` / 429 (60s). `/auth/me`, login and register return `email_verified`.
  - D11 Verified-email gate: `POST /listings`, `/listings/{id}/bid`, `/sniper-bid`, `/buy-now`, `/best-offer`, `/relist` → **403** `Verify your email address to continue` for unverified users.
  - Saved searches: `alerts_enabled` (default true; missing = true); `PUT /saved-searches/{id}` `{alerts_enabled}` (owner; 400 bad id, 404). New notification type `saved_search_match` when a listing becomes active and matches (once per user per listing).
  - D12 Messaging (one conversation per transaction, buyer + seller only; anyone else 404): `GET /conversations` → `{conversations:[{transaction_id, listing_id, listing_title, listing_image, other_party{id,full_name}, role, last_message, unread_count, amount}]}`; `GET /transactions/{id}/messages` → `{transaction_id, listing, other_party, messages[]}` (marks received read); `POST /transactions/{id}/messages` `{body}` (1–2000 chars plain text; 422; 429 after 20 per 10 min) → 201 message; `GET /messages/unread-count` → `{unread}`. Socket.IO server event `message` `{transaction_id, message}` to the recipient's own room. Notification type `new_message` (one unread per conversation).
  - Notification type `purchase_complete` (buyer, after Buy It Now / accepted offer).
- **v1.2 (8 Oct 2026)** — security fixes (`feature/p6-security-hardening`):
  - Any `user`/`admin` endpoint and `/auth/refresh`: **403** `Account has been banned` / `…suspended` for blocked accounts (was: access until token expiry). `/auth/login` answers 401 for a wrong password before revealing a ban.
  - Socket.IO: the connection is identified by the `access_token` cookie (browsers must send credentials). `join_user_notifications` joins **only the caller's own** `user_{id}` room — the payload's `user_id` is ignored — and acks `{ok, error?}`; visitors get `{ok:false}`. Allowed origin = `FRONTEND_URL` (was `*`).
  - `auction_ended` has one shape everywhere: `{listing_id, status, sold_price?, winner_id?, sold_via?}`; buy-now/offer events keep the v1 `price` key.
  - `POST /listings/{id}/buy-now` → 400 when the listing already ended (no double sale). `PUT /offers/{id}/respond` → 400 if the offer isn't pending, 404 if the listing is gone, 409 if it ended; accepting creates a `best_offer` transaction and declines the other pending offers.
  - Cookies are `Secure` when `ENV=production` (`COOKIE_SECURE` overrides).
- **v1.1 (8 Oct 2026)** — additive / bug-fix only:
  - `GET /listings` accepts optional `seller_id` (the CRA profile page already sent it).
  - `q` (listings) and `search` (admin users) are plain text, escaped before matching — no regex semantics.
  - Socket.IO `notification` payload `_id` is a string (it previously failed to serialise).
- **v1 (8 Oct 2026)** — contract frozen.
  - D9: `highest_bidder_max_bid` removed from all non-admin listing responses (it leaked the leading proxy max).
  - D8 visibility fix: `GET /listings` rejects non-public `status` (400); `GET /listings/{id}` returns 404 for `pending`/`rejected` unless seller or admin.
  - Added D5–D8; documented request/response shapes, listing object and Socket.IO payloads.
  - Phase 1 additions folded in: `POST /auth/forgot-password`, `POST /auth/reset-password`, `/cloudinary/signature` 503 when unconfigured, 30s background closer with `auction_ended` emit.
- Draft (28 Sep 2026) — route list generated from `server.py` @ 9ce8c71.
