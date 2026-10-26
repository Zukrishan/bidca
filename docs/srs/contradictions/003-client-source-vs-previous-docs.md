# 003 — Client source (26 Oct 2026) vs the previous SRS and the built code

`docs/source/BIDCA.txt` changes several things the earlier SRS, `API_CONTRACT.md` v1.4 and the code
already did differently.
**Resolution (26 Oct 2026, user):** "source docs is the main" — the source wins on every point below.
The code is unchanged until each item is built; contract changes need a D-number then.

| # | Previous (SRS / contract / code) | Source | Now |
|---|---|---|---|
| a | 5 failed logins → 15 min lock (FR-02, contract `/auth/login`) | 12 h [L17] | FR-02: 12 h |
| b | Verified badge = admin-approved government ID + selfie (FR-16) | Phone verified ✓, shown only after two successful transactions [L33] | FR-22 badge; fate of ID verification is Q009 |
| c | Listings carry `shipping_cost`, `shipping_from`; `free_shipping` filter; home copy "local pickup or ship" | Remove shipping cost [L62]; P2P exchange only | FR-05 removes shipping |
| d | Transaction status `pending_payment`; CRA home "Win & Pay — Secure payment" | "We do not touch, hold, refund, or move any money, ever … do not build anything that suggests otherwise" [L129–131] | FR-14, NFR-07 |
| e | Feedback can be left as soon as the sale happens (FR-14) | Only after both press Complete [L136–139] | FR-25 |
| f | Best Offer on any listing with `accepts_best_offer`, including auctions (FR-12) | Price locked, no negotiation once an auction is open [L107–108] | FR-12/FR-28: Best Offer on fixed-price only |
| g | Ratings: positive / neutral / negative, weighted 5/3/1 score | 👍 green / 🟡 yellow / 👎 red with fixed meanings [L36, L138] | FR-25 (same three values, new meaning and display) |
| h | Seller dashboard + buyer dashboard (Bids, Notifications) | One user page: Selling / Current Bids / Successfully Completed [L83–89] | FR-23 |
| i | Out of scope: AI fraud detection; scope said "payment / escrow until Q004" | AI items are "later"; money is out of scope **permanently** for transactions | 01-scope |

Not contradictions, kept as they were: BC postal code (`V…`) at signup stays alongside the new
city dropdown (the source adds the dropdown, does not remove the postal code); every listing still
needs admin approval (source is silent).
