const cad = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" });

export function formatCAD(amount) {
  return cad.format(Number(amount) || 0);
}

/** Milliseconds until end_time (negative once ended). */
export function msLeft(endTime, now = Date.now()) {
  return new Date(endTime).getTime() - now;
}

/** "2d 4h", "2h 14m", "38m", "45s", or "Ended". */
export function formatTimeLeft(endTime, now = Date.now()) {
  const ms = msLeft(endTime, now);
  if (ms <= 0) return "Ended";
  const s = Math.floor(ms / 1000);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${s}s`;
}

/** Urgency colour is reserved for auctions ending within the hour (design proposal 1). */
export function isUrgent(endTime, now = Date.now()) {
  const ms = msLeft(endTime, now);
  return ms > 0 && ms < 3600 * 1000;
}

export const CONDITION_LABELS = {
  new: "New",
  like_new: "Used – like new",
  good: "Used – good",
  fair: "Used – fair",
  poor: "For parts / poor",
};

export const LISTING_TYPE_LABELS = {
  auction: "Auction",
  fixed_price: "Buy now",
  auction_bin: "Auction + Buy now",
};

export function isAuction(listing) {
  return listing.listing_type === "auction" || listing.listing_type === "auction_bin";
}

/** The price a card should lead with: current bid for auctions, Buy-now price otherwise. */
export function headlinePrice(listing) {
  if (isAuction(listing)) return listing.current_bid ?? listing.starting_bid;
  return listing.buy_it_now_price ?? listing.current_bid ?? listing.starting_bid;
}

export function formatDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-CA", { year: "numeric", month: "short", day: "numeric" });
}
