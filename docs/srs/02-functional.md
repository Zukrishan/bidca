# 2. Functional requirements

Primary source: `docs/source/BIDCA.txt` (26 Oct 2026) — line numbers in brackets, e.g. [L17].
Status is the code on the newest branch, `feature/p8-backlog` (8 Oct 2026; nothing merged to `main` yet).
⚠️ = built, but the source changed it. ❌ = not built.
Where the source was unclear we chose a **provisional default** (26 Oct 2026) so work can continue;
each is written into the requirement below and its question file says "Decided — provisional
default". The client may change any of them.

### Settings (env vars, defaults from Q010/Q015)
| Setting | Default |
|---|---|
| Login lockout | 5 failures → 12 h |
| Inactivity logout | 30 min |
| Winner no-response window / lock | 24 h / 6 h |
| Open-transaction reminder | every 6 h, max 10, then admin alert |
| Seller cancel-with-bids suspension | 2 days → 7 days → until admin review (within 12 months) |
| Listing cap | 30 per user per calendar month (Pacific) |
| Free period | 3 months from launch date |

## Accounts
| ID | Requirement | Status |
|---|---|---|
| FR-01 | Register: email, full name, password, **city from a BC-city dropdown** [L7], BC postal code (`V…`), **phone number — verified, one account per phone** [L9], **age 19+** [L10], optional profile picture [L11], **accept Terms & Conditions** [L12], **CAPTCHA** [L19] | ⚠️ email/name/password/city/postal built; phone, 19+, picture, T&C, CAPTCHA ❌ |
| FR-02 | Login/logout/refresh, JWT httpOnly cookies; **5 failures → 12 h lockout** [L17]; CAPTCHA [L19]; **auto-logout after inactivity** [L21] | ⚠️ lockout is 15 min; CAPTCHA and inactivity timeout ❌ |
| FR-03 | Password reset by **email only, not phone** [L18], single-use expiring link | ✅ `feature/p0-backend` (1 h link) |
| FR-04 | Email verification on registration; **link expires** [L20] | ✅ `feature/p7-features` — single-use 24 h link; bidding/selling/buying need a verified email |
| FR-21 | After registering, explain the rules and how P2P auctions work [L14] | ❌ |

## Listings
| ID | Requirement | Status |
|---|---|---|
| FR-05 | Create listing, ≤10 images with **drag-and-drop reordering** [L60]; **no shipping cost** [L62]; **subcategory dropdown disabled until a category is chosen, then filled from it** [L63]; **Title, Category, Description, Condition, City required (`*`), Continue disabled until filled** [L65]; **save as draft** [L69]; **category-specific fields** (Vehicles: year/make/model/mileage; Electronics: brand/model) [L70]; types: auction, auction + BIN, fixed price, **private** (FR-31); goes to `pending` | ⚠️ create + `pending` built (images via Cloudinary mock); `shipping_cost` must go; rest ❌ |
| FR-06 | Admin approve/reject/delete listings | ✅ |
| FR-28 | **Price lock:** once an auction is open the seller cannot change the price or negotiate; setting a fair starting price is the seller's job [L107–108] | ⚠️ no edit endpoint exists (price already fixed), but Best Offer is allowed on auctions with `accepts_best_offer` — must be fixed-price only (contradiction 003) |
| FR-29 | Seller who cancels a listing while people are bidding is suspended for a period based on their history [L75] — **sellers may cancel**: no penalty without bids; with bids, confirm step stating the penalty, bidders notified, suspension per Settings (Q012) | ❌ there is no seller cancel today |
| FR-30 | **Vehicles only:** "📋 Download Vehicle Inspection Checklist" on the listing page and on the transaction page; printable PDF, same for every vehicle, no login needed; never shown on other categories; checklist content supplied by the client later [L143–161]. Vehicle disclosure questions (accident history, mechanical issues, owners, inspection/safety certificate upload, odometer, liens) [L163–170] — **both**: buyer checklist PDF (placeholder content) and these as **required seller fields** on Vehicles listings, shown on the listing page (Q008) | ❌ |
| FR-31 | **Private (invite-only) listings:** seller invites by BidCa username/email/phone or a private invite link; only invitees can view or bid; never in home, search, categories, Popular or Ending Soon; otherwise works like an auction (bidding, winning, transaction page, disputes) [L173–184]; **no ratings** [L186]; private deals do not count toward the badge or tiers; still need admin approval; invite links expire when the listing ends (Q007) | ❌ |
| FR-34 | Launch plan: first 3 months free, **30 listings per user per month** [L3] — counting rules and free period in Settings (Q015); nothing is charged after it (Q004) | ❌ |

## Browse and home
| ID | Requirement | Status |
|---|---|---|
| FR-07 | Browse/search/filter; **one search bar on the home page** (there are two) [L25]; home shows **newly added items — all of them, not a selection** [L52] plus **Popular** (today's bid-count "Featured", renamed so "Featured" can later mean paid — Q004) and ending soon; fixed-price items with no bids at the bottom (lowest priority) [L56]; private listings never shown (FR-31) | ⚠️ browse/search built; two search bars; no "newly added" section |
| FR-33 | Real **Terms of Service, Privacy Policy, How It Works** (accurate about the no-payment P2P model) and **About Us** pages, linked prominently in the footer [L48, L194, L198] | ❌ only a "How It Works" footer link (CRA) — text needed from the client (Q014) |

## Bidding and closing
| ID | Requirement | Status |
|---|---|---|
| FR-08 | Place bid ≥ current + increment; proxy (max) bids; **"Are you sure you want to bid $X?" confirmation** [L74] | ⚠️ bidding built; confirmation ❌ |
| FR-09 | Sniper bids execute N minutes before end | ✅ `feature/p0-backend` |
| FR-10 | Auctions close automatically at `end_time`: winner set, reserve checked, `sold`/`unsold` | ✅ `feature/p0-backend` |
| FR-11 | On close: **winner and seller emailed immediately** ("You won the bid for [item]" / "Your item [item] has a winning bidder") [L95–99]; clear **"You won!" / "Auction ended, you didn't win"** for every bidder [L203]; won item appears in the winner's Current Bids with a **Message** button [L92–93] | ⚠️ winner + seller in-app + email built; losing bidders and Current Bids/Message ❌ |
| FR-12 | Buy It Now; Best Offer on **fixed-price listings only** (FR-28) + seller respond | ⚠️ Best Offer also allowed on auctions |
| FR-32 | **Outbid alert is instant** by email as well as in-app [L190]; SMS via Twilio once the team sets it up, no push for launch (Q011) | ⚠️ in-app + live only |
| FR-13 | Watchlist, saved searches + alerts | ✅ `feature/p7-features` |
| FR-15 | Relist ended/unsold | ✅ |

## After a win — transaction page
| ID | Requirement | Status |
|---|---|---|
| FR-14 | Every sale (auction win, Buy It Now, accepted offer) creates a transaction, handled by FR-24–FR-27. **No money is involved**: no `pending_payment` state, no "pay" wording | ⚠️ transactions built, status is `pending_payment` |
| FR-24 | **Transaction page**, created when a bid is won, visible to buyer and seller only [L110–113]: chat about this deal only; order summary (item, photo, agreed price, exchange method from the seller's profile) [L115–116]; **Complete Transaction** — completed only when **both** press it [L117–120]; **Dispute** — either side, anytime, **proof upload required**, marks it Disputed and disables Complete [L121–124]; **Cancel Dispute** — only the opener; returns it to open [L125–128]; admins review disputes and decide (rating, warning, ban) — never money [L129–131] | ⚠️ per-transaction chat built (FR-20); rest ❌ |
| FR-20 | Buyer–seller messaging per transaction | ✅ `feature/p7-features` — becomes the FR-24 chat |
| FR-25 | **Ratings:** when both press Complete, prompt both to rate and comment on the other [L136–137]; 👍 green = good, 🟡 yellow = problem sorted / dispute, 👎 red = deal fell through [L36, L138]; one rating per user per transaction [L37, L139]; ratings and comments are public [L36, L38] | ⚠️ positive/neutral/negative, one per transaction, public — but allowed before completion |
| FR-26 | **No response:** winner who does not open/answer the chat within 24 h of winning is locked for a few hours and their rating is hurt; a background job enforces it [L101–105]; the transaction is then **cancelled** and the buyer gets an automatic red rating "No response within 24 hours" (Q013); seller may relist | ❌ |
| FR-27 | **Reminder email** to both every few hours while the transaction is open; stops the moment it is Completed, Cancelled or Disputed [L133–135]; interval in Settings | ❌ |

## Profiles and the user page
| ID | Requirement | Status |
|---|---|---|
| FR-22 | **Public profile** [L27–42]: picture or default avatar; **display name** (default first name + last initial; full name private); BC city; member since; **verified badge = phone verified ✓, shown only after two successful transactions**; saved bids = the watchlist, owner only; completed bids as buyer and as seller; ratings (FR-25) and buyer comments; active listings; bid history **private** to the owner; auto-awarded tiers ("Top Seller", "Power Bidder") from transaction count + rating ratio — Top Seller: 10+ completed sales and 95%+ green; Power Bidder: 10+ completed purchases and 95%+ green (Q013); **preferred exchange method** (cash on pickup, e-transfer, meet in a public place). **Private to the owner:** account settings incl. delete account [L43–44] | ⚠️ basic profile + ratings built; rest ❌ |
| FR-23 | **User page tabs** [L78–89]: **Selling**; **Current Bids** (active auctions, plus won items awaiting completion with a Message button); **Successfully Completed** (buy and sell side) | ❌ dashboard shows only Bids + Notifications (also fixes ACTION-PLAN A6) |
| FR-16 | ID verification (government ID + selfie) and admin review | ⚠️ built; **hidden from users for launch** — phone badge is the only badge (FR-22); admin queue and code kept (Q009) |
| FR-17 | Reports on listings, admin queue | ✅ |
| FR-18 | In-app notifications, read/read-all | ✅ |
| FR-19 | Transactional email (outbid, won, sold, approved, reset, verification, reminders) | ⚠️ `send_email()` built; outbid (FR-32) and reminders (FR-27) ❌ |

## Later — named in the source, not this build
FR-35: AI chat bot [L49]; paid featured listings [L50] and premium members on top [L53] (both need
Q004); smart search [L51]; image search [L54]; scam-listing detection [L55]; prohibited-content
auto-check [L61]; description character counter [L64]; AI description help and category
suggestion [L66–67]; duplicate listing detection [L68]; cookie consent banner [L196].
Also later (Q013 default): listing/photo matching [L71], unethical
product detection [L72], price suggestion [L73].
