"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { clientApi } from "@/lib/client-api";
import { cn } from "@/lib/utils";

export function Inbox() {
  const [state, setState] = useState({ status: "loading", items: [] });

  useEffect(() => {
    clientApi("/conversations").then(
      (d) => setState({ status: "ok", items: d.conversations || [] }),
      (e) => setState({ status: e.status === 401 ? "visitor" : "error", items: [] })
    );
  }, []);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-2xl font-bold">Messages</h1>
      {state.status === "loading" && <p className="text-muted-foreground">Loading…</p>}
      {state.status === "visitor" && (
        <p>
          <a href="/login" className="font-semibold text-primary underline">Sign in</a> to see your messages.
        </p>
      )}
      {state.status === "error" && <p className="text-destructive">Couldn&apos;t load your messages. Try again shortly.</p>}
      {state.status === "ok" && state.items.length === 0 && (
        <p className="text-muted-foreground">
          No conversations yet. When you buy or sell an item, you can message the other person here to arrange pickup.
        </p>
      )}
      {state.items.length > 0 && (
        <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
          {state.items.map((c) => (
            <li key={c.transaction_id}>
              <Link href={`/messages/${c.transaction_id}`} className="flex gap-3 p-3 hover:bg-muted">
                <div className="size-14 shrink-0 overflow-hidden rounded-lg bg-muted">
                  {c.listing_image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.listing_image} alt="" className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className={cn("truncate", c.unread_count ? "font-bold" : "font-semibold")}>{c.listing_title}</span>
                    {c.unread_count > 0 && <Badge className="border-transparent bg-primary text-primary-foreground">{c.unread_count}</Badge>}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {c.role === "buyer" ? "Seller" : "Buyer"}: {c.other_party.full_name}
                  </p>
                  <p className="truncate text-sm text-muted-foreground">
                    {c.last_message ? c.last_message.body : "No messages yet. Say hello to arrange pickup."}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
