"use client";

import { useEffect, useState } from "react";

import { clientApi, getMe } from "@/lib/client-api";
import { formatCAD, formatTimeLeft } from "@/lib/format";

/**
 * Owner-only part of the profile (FR-22): Saved Bids (= the watchlist, Q013), private bid history
 * and a link to account settings (CRA /account). Renders nothing for anyone else.
 */
export function OwnerPanel({ userId }) {
  const [state, setState] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then(async (me) => {
        if ((me._id || me.id) !== userId) return;
        const [watch, bids] = await Promise.all([
          clientApi("/users/me/watchlist").catch(() => ({ watchlist: [] })),
          clientApi("/users/me/bids").catch(() => ({ bids: [] })),
        ]);
        if (!cancelled) setState({ watchlist: watch.watchlist || [], bids: bids.bids || [] });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!state) return null;

  return (
    <section className="flex flex-col gap-6 rounded-lg border border-border bg-surface p-4 sm:p-6" aria-labelledby="owner-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="owner-heading" className="text-xl font-semibold">Only you can see this</h2>
          <p className="text-sm text-muted-foreground">Your saved items, your bids and your account.</p>
        </div>
        <a href="/account" className="inline-flex h-11 items-center rounded-lg border border-border px-4 text-sm font-semibold hover:bg-muted">
          Account settings
        </a>
      </div>

      <OwnerList
        title="Saved Bids"
        empty="Nothing saved yet. Tap the heart on a listing to save it."
        items={state.watchlist}
        render={(l) => (l.status === "active" ? `${formatCAD(l.current_bid)} · ${formatTimeLeft(l.end_time)} left` : "Ended")}
      />
      <OwnerList
        title="Bid history"
        empty="You haven't bid on anything yet."
        items={state.bids}
        render={(l) =>
          `Your max ${formatCAD(l.my_max_bid)} · ${l.status === "active" ? (l.is_winning ? "Winning" : "Outbid") : l.is_winning ? "Won" : "Ended"}`
        }
      />
    </section>
  );
}

function OwnerList({ title, empty, items, render }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {items.slice(0, 20).map((l) => (
            <li key={l._id} className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-2.5 text-sm">
              <a href={`/auctions/${l._id}`} className="font-medium text-primary hover:underline">{l.title}</a>
              <span className="text-muted-foreground">{render(l)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
