# Proposal 1 — "BidCa Simple" (Stitch, 7 Oct 2026)

Rank 7 in `AGENTS.md`: a **proposal only**. Nothing here is built until the client signs off
(`docs/srs/open-questions/Q003`) and the chosen direction is folded into the frontend skill.

Stitch project: "BidCa — simple design proposal (Phase 3)" (`projects/9649148460922646710`),
design system `BidCa Simple` (`assets/7988412144151374560`).

## Direction
The client asked for a site that is **very simple**, so simplicity is the whole idea:

- Item photos, prices and time left are the only visual interest. Everything else is white
  surfaces, 1px hairlines, no shadows, no banners, carousels, gradients or illustration.
- One accent for action: deep forest green `#1F5C46` (buttons, links, selected states).
- One accent for urgency: burnt orange `#C2410C`, **only** for countdowns under 1 hour,
  "Ending soon" and "You've been outbid".
- Public Sans throughout; prices and countdowns semibold with tabular numerals. Body 16px.
- Plain labels: "Place bid", "Ends in 2h 14m", "Pickup in Kelowna". No marketing copy.
- Cards show exactly: photo, title, current bid or Buy-now price, bid count, time left, city.
- Mobile-first; every screen has a sticky primary action at 390px.

## Screens
| # | Screen | File |
|---|---|---|
| 1 | Home | `01-home.png` |
| 2 | Auction detail (desktop, top of page) | `02-auction-detail.png` |
| 3 | Search results ("bike") | `03-search-results.png` |

Not captured this round: mobile auction detail and the Sell-an-item form generated in Stitch but
the API returned no screen IDs to export; open them in the Stitch project or regenerate.
OpenDesign (the second tool in the plan) failed to connect this session, so there is no
OpenDesign alternative yet.

## Not for build — generator deviations
Stitch added things that contradict scope or the direction above. Ignore them when reviewing:

- **Escrow/payment copy** on auction detail ("In-Person Guarantee … before releasing funds") —
  there are no payments until Q004; not shown in the exported crop but present in the Stitch screen.
- "Verified BC residents only" filter and "pickup verification" copy (search) — verification is
  for **sellers** (FR-16); there is no resident or pickup verification.
- Search filter drops the "Auction + Buy now" listing type (it exists: `auction_bin`).
- Orange countdown on a 1h 05m item (home) — orange is for under 1 hour only.
- Monospace price font (auction detail) — should be Public Sans tabular.
- Several search-result photos are screenshots of UIs, not items — placeholder artefacts.
- Footer "© 2025 BidCa Simple" — wrong year and name.
- Top-nav items on auction detail (Browse / Sell / My Bids / Saved) differ from home's single
  search bar; pick one pattern.

## Decisions needed from the client
1. Is this level of plainness right, or is it too bare?
2. Green + orange, or a different primary colour?
3. One top-bar pattern: search-only (home) or search + nav links (auction detail)?
4. Who signs off, and is sign-off on these screens enough to start Phase 4 (Q003)?
