"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { io } from "socket.io-client";
import { Eye } from "lucide-react";

import { Countdown } from "@/components/Countdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PUBLIC_API_URL } from "@/lib/config";
import { clientApi, getMe } from "@/lib/client-api";
import { formatCAD, formatDateTime, isAuction, isUrgent, headlinePrice } from "@/lib/format";
import { cn } from "@/lib/utils";

// Mirrors backend/app/constants.py get_bid_increment (used only if the API omits bid_increment).
function fallbackIncrement(p) {
  if (p < 25) return 1;
  if (p < 100) return 5;
  if (p < 250) return 10;
  if (p < 500) return 25;
  if (p < 1000) return 50;
  if (p < 2500) return 100;
  if (p < 5000) return 250;
  return 500;
}

function minNextBid(l) {
  const current = l.current_bid ?? l.starting_bid ?? 0;
  if (!l.bid_count) return current;
  return current + (l.bid_increment || fallbackIncrement(current));
}

const money = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

export function BidPanel({ listing }) {
  const router = useRouter();
  const id = listing._id;
  const [user, setUser] = useState(undefined); // undefined = loading, null = visitor
  const [mine, setMine] = useState({ is_watching: false, is_seller: false });
  const auction = isAuction(listing);
  const live = listing.status === "active" && (!listing.end_time || new Date(listing.end_time).getTime() > Date.now() || !auction);
  const canBuyNow = !!listing.buy_it_now_price && (listing.listing_type === "fixed_price" || listing.listing_type === "auction_bin");
  const min = minNextBid(listing);

  const [amount, setAmount] = useState(String(money(min)));
  const [amountTouched, setAmountTouched] = useState(false);
  const [busy, setBusy] = useState(null);
  const [notice, setNotice] = useState(null); // { kind: ok|error|outbid, text }
  const [confirmBuy, setConfirmBuy] = useState(false);
  const [confirmBid, setConfirmBid] = useState(null); // amount awaiting "Are you sure?" (FR-08)
  const [snipe, setSnipe] = useState({ open: false, max: "", minutes: "5" });
  const [offer, setOffer] = useState({ open: false, amount: "", message: "" });

  // Keep the prefilled amount in step with live updates unless the user is typing.
  useEffect(() => {
    if (!amountTouched) setAmount(String(money(min)));
  }, [min, amountTouched]);

  const loadMine = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
      // Derived without re-fetching the listing, which would count a second view.
      const { watchlist = [] } = await clientApi("/users/me/watchlist");
      setMine({
        is_watching: watchlist.some((w) => w._id === id),
        is_seller: String(listing.seller_id) === String(me._id),
      });
    } catch {
      setUser((u) => (u === undefined ? null : u));
    }
  }, [id, listing.seller_id]);

  useEffect(() => {
    loadMine();
  }, [loadMine]);

  useEffect(() => {
    if (!auction) return;
    const socket = io(PUBLIC_API_URL, { path: "/api/socket.io", withCredentials: true, transports: ["websocket", "polling"] });
    socket.on("connect", () => socket.emit("join_auction", { auction_id: id }));
    const refresh = () => router.refresh();
    socket.on("bid_update", refresh);
    socket.on("auction_ended", refresh);
    return () => {
      socket.emit("leave_auction", { auction_id: id });
      socket.off("bid_update", refresh);
      socket.off("auction_ended", refresh);
      socket.disconnect();
    };
  }, [auction, id, router]);

  async function act(name, path, body, onOk) {
    setBusy(name);
    setNotice(null);
    try {
      const r = await clientApi(`/listings/${id}${path}`, { method: "POST", body });
      onOk?.(r);
      router.refresh();
      return r;
    } catch (err) {
      setNotice({ kind: err.status === 401 ? "error" : "error", text: err.status === 401 ? "Please sign in again to continue." : err.message });
    } finally {
      setBusy(null);
    }
  }

  // Bids can't be undone and no payment layer catches mistakes, so every bid is confirmed first.
  function placeBid(e) {
    e.preventDefault();
    const max_bid = parseFloat(amount);
    if (!(max_bid > 0)) return setNotice({ kind: "error", text: "Enter a bid amount." });
    setNotice(null);
    setConfirmBid(max_bid);
  }

  function submitBid() {
    const max_bid = confirmBid;
    setConfirmBid(null);
    act("bid", "/bid", { max_bid }, (r) => {
      const winning = r.is_winning ?? true;
      setAmountTouched(false);
      setNotice({
        kind: winning ? "ok" : "outbid",
        text: `${r.message}. ${winning ? "You are the high bidder." : "You were outbid by an earlier maximum."} Your maximum: ${formatCAD(r.your_max_bid)}.`,
      });
    });
  }

  function scheduleSnipe(e) {
    e.preventDefault();
    const max_bid = parseFloat(snipe.max);
    if (!(max_bid > 0)) return setNotice({ kind: "error", text: "Enter your maximum for the snipe bid." });
    act("snipe", "/sniper-bid", { max_bid, minutes_before_end: Number(snipe.minutes) }, (r) => {
      setNotice({ kind: "ok", text: r.message });
      setSnipe({ open: false, max: "", minutes: "5" });
    });
  }

  function buyNow() {
    act("buy", "/buy-now", undefined, (r) => {
      setConfirmBuy(false);
      setNotice({ kind: "ok", text: r.message || "Purchase recorded." });
    });
  }

  function sendOffer(e) {
    e.preventDefault();
    const offer_amount = parseFloat(offer.amount);
    if (!(offer_amount > 0)) return setNotice({ kind: "error", text: "Enter an offer amount." });
    act("offer", "/best-offer", { offer_amount, message: offer.message || undefined }, (r) => {
      setNotice({ kind: "ok", text: r.message || "Offer submitted" });
      setOffer({ open: false, amount: "", message: "" });
    });
  }

  async function resendVerification() {
    setBusy("resend");
    setNotice(null);
    try {
      const r = await clientApi("/auth/resend-verification", { method: "POST" });
      setNotice({ kind: "ok", text: r.message || "Verification email sent" });
    } catch (err) {
      setNotice({ kind: "error", text: err.message });
    } finally {
      setBusy(null);
    }
  }

  async function toggleWatch() {
    setBusy("watch");
    setNotice(null);
    try {
      const r = await clientApi(`/listings/${id}/watch`, { method: "POST" });
      setMine((m) => ({ ...m, is_watching: !!r.watching }));
      router.refresh();
    } catch (err) {
      setNotice({ kind: "error", text: err.message });
    } finally {
      setBusy(null);
    }
  }

  const noticeEl = notice && (
    <p
      role={notice.kind === "ok" ? "status" : "alert"}
      className={cn("text-sm", notice.kind === "ok" && "text-success", notice.kind === "outbid" && "font-medium text-urgent", notice.kind === "error" && "text-urgent")}
    >
      {notice.text}
    </p>
  );

  const price = headlinePrice(listing);
  const urgent = auction && listing.end_time && isUrgent(listing.end_time);

  const watchButton = (
    <Button variant="outline" onClick={toggleWatch} disabled={busy === "watch"} aria-pressed={mine.is_watching}>
      <Eye aria-hidden /> {mine.is_watching ? "Watching" : "Watch this listing"}
    </Button>
  );

  return (
    <div className="flex flex-col gap-4 pb-24 lg:pb-0">
      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">{auction ? (listing.bid_count ? "Current bid" : "Starting bid") : "Buy now price"}</p>
        <p className="tabular text-3xl font-bold">{formatCAD(price)}</p>
        <p className="text-sm text-muted-foreground">
          {auction && (
            <>
              {listing.bid_count || 0} {listing.bid_count === 1 ? "bid" : "bids"}
              {listing.reserve_price ? (listing.reserve_met ? " · Reserve met" : " · Reserve not met") : ""}
            </>
          )}
        </p>
        {auction && listing.end_time && (
          <p className={cn("text-sm", urgent ? "text-urgent" : "text-muted-foreground")}>
            {listing.status === "active" ? <Countdown endTime={listing.end_time} /> : "Ended"}
          </p>
        )}
        {auction && listing.end_time && listing.status === "active" && (
          <p className="text-xs text-muted-foreground">Ends {formatDateTime(listing.end_time)}</p>
        )}
        {listing.buy_it_now_price && auction && <p className="text-sm text-muted-foreground">Buy now: {formatCAD(listing.buy_it_now_price)}</p>}
      </div>

      {!live ? (
        user && listing.status === "sold" && String(listing.winner_id) === String(user._id) ? (
          <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
            <p className="font-semibold text-success">You won!</p>
            <p className="text-sm">You won this for {formatCAD(listing.sold_price)}. Message the seller to arrange the exchange.</p>
            <Link href="/messages" className="text-sm font-medium text-primary hover:underline">Go to messages</Link>
          </div>
        ) : (
          <p className="rounded-lg border border-border p-3 text-sm text-muted-foreground">
            {listing.status === "sold" ? `Sold${listing.sold_price ? ` for ${formatCAD(listing.sold_price)}` : ""}.` : "This listing is no longer open for bids."}
          </p>
        )
      ) : user === undefined ? (
        <div className="h-11" aria-hidden />
      ) : !user ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface p-3 lg:static lg:z-auto lg:border-0 lg:bg-transparent lg:p-0">
          <a href="/login" className="flex h-12 items-center justify-center rounded-lg bg-primary px-6 text-base font-semibold text-primary-foreground hover:bg-primary-hover">
            Sign in to bid
          </a>
        </div>
      ) : mine.is_seller ? (
        <p className="rounded-lg border border-border p-3 text-sm">This is your listing.</p>
      ) : !user.email_verified ? (
        <>
        <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
          <p className="text-sm font-medium">Confirm your email to bid</p>
          <p className="text-xs text-muted-foreground">We sent a link to {user.email}. Open it, then come back.</p>
          <Button variant="outline" onClick={resendVerification} disabled={busy === "resend"}>
            {busy === "resend" ? "Sending…" : "Resend email"}
          </Button>
          {noticeEl}
        </div>
        {/* Watching doesn't need a verified email; bidding, buying and offers do */}
        {watchButton}
        </>
      ) : (
        <>
          {auction && (
            <form
              onSubmit={placeBid}
              className="fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 border-t border-border bg-surface p-3 lg:static lg:z-auto lg:border-0 lg:bg-transparent lg:p-0"
            >
              <label htmlFor="bid-amount" className="hidden text-sm font-medium lg:block">Your maximum bid</label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <Input
                    id="bid-amount"
                    inputMode="decimal"
                    type="number"
                    min={min}
                    step="0.01"
                    value={amount}
                    onChange={(e) => {
                      setAmount(e.target.value);
                      setAmountTouched(true);
                    }}
                    className="tabular pl-7"
                  />
                </div>
                <Button type="submit" size="lg" disabled={busy === "bid" || confirmBid !== null}>{busy === "bid" ? "Bidding…" : "Place bid"}</Button>
              </div>
              {confirmBid !== null && (
                <div role="alertdialog" aria-labelledby="confirm-bid-text" className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-3">
                  <p id="confirm-bid-text" className="text-sm font-medium">Are you sure you want to bid {formatCAD(confirmBid)}?</p>
                  <p className="text-xs text-muted-foreground">Bids can't be taken back. If you win, you agree to buy at the final price.</p>
                  <div className="flex gap-2">
                    <Button type="button" onClick={submitBid}>Yes, place bid</Button>
                    <Button type="button" variant="ghost" onClick={() => setConfirmBid(null)}>Cancel</Button>
                  </div>
                </div>
              )}
              <p className="text-xs text-muted-foreground">Enter {formatCAD(min)} or more. We bid for you, only as much as needed.</p>
              {noticeEl}
            </form>
          )}
          {!auction && noticeEl}

          {canBuyNow &&
            (confirmBuy ? (
              <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
                <p className="text-sm">Buy now for {formatCAD(listing.buy_it_now_price)}? This ends the listing.</p>
                <div className="flex gap-2">
                  <Button onClick={buyNow} disabled={busy === "buy"}>{busy === "buy" ? "Buying…" : "Confirm"}</Button>
                  <Button variant="ghost" onClick={() => setConfirmBuy(false)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <Button variant={auction ? "outline" : "default"} size="lg" onClick={() => setConfirmBuy(true)}>
                Buy now for {formatCAD(listing.buy_it_now_price)}
              </Button>
            ))}

          {listing.accepts_best_offer &&
            (offer.open ? (
              <form onSubmit={sendOffer} className="flex flex-col gap-2 rounded-lg border border-border p-3">
                <label htmlFor="offer-amount" className="text-sm font-medium">Your offer</label>
                <Input id="offer-amount" type="number" min="0" step="0.01" inputMode="decimal" value={offer.amount} onChange={(e) => setOffer({ ...offer, amount: e.target.value })} className="tabular" />
                <Input value={offer.message} onChange={(e) => setOffer({ ...offer, message: e.target.value })} placeholder="Message to the seller (optional)" aria-label="Message to the seller" />
                <div className="flex gap-2">
                  <Button type="submit" disabled={busy === "offer"}>Send offer</Button>
                  <Button type="button" variant="ghost" onClick={() => setOffer({ ...offer, open: false })}>Cancel</Button>
                </div>
              </form>
            ) : (
              <Button variant="outline" size="lg" onClick={() => setOffer({ ...offer, open: true })}>Make an offer</Button>
            ))}

          {auction &&
            (snipe.open ? (
              <form onSubmit={scheduleSnipe} className="flex flex-col gap-2 rounded-lg border border-border p-3">
                <p className="text-sm font-medium">Schedule a snipe bid</p>
                <p className="text-xs text-muted-foreground">We place your maximum bid automatically just before the auction ends.</p>
                <Input type="number" min="0" step="0.01" inputMode="decimal" value={snipe.max} onChange={(e) => setSnipe({ ...snipe, max: e.target.value })} placeholder="Maximum bid" aria-label="Maximum bid" className="tabular" />
                <select value={snipe.minutes} onChange={(e) => setSnipe({ ...snipe, minutes: e.target.value })} className="h-11 rounded-lg border border-border bg-surface px-3 text-base" aria-label="Minutes before end">
                  {[1, 2, 3, 5, 10].map((m) => (
                    <option key={m} value={m}>{m} {m === 1 ? "minute" : "minutes"} before the end</option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <Button type="submit" disabled={busy === "snipe"}>Schedule</Button>
                  <Button type="button" variant="ghost" onClick={() => setSnipe({ ...snipe, open: false })}>Cancel</Button>
                </div>
              </form>
            ) : (
              <button type="button" onClick={() => setSnipe({ ...snipe, open: true })} className="self-start text-sm font-medium text-primary hover:underline">
                Schedule a snipe bid
              </button>
            ))}

          {watchButton}
        </>
      )}
    </div>
  );
}
