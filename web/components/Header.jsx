import Link from "next/link";
import { Search } from "lucide-react";

import { AccountLink } from "@/components/AccountLink";

// Links to routes still served by the CRA app (/create-listing, /login, /dashboard) are plain <a>
// so they do a full navigation through the fallback rewrite instead of a client-side route change.
export function Header() {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center gap-3 px-4 sm:gap-6 sm:px-6">
        <Link href="/" className="text-xl font-bold tracking-tight text-foreground">
          BidCa
        </Link>
        <form action="/auctions" className="relative flex-1" role="search">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            name="q"
            type="search"
            placeholder="Search items in BC"
            aria-label="Search items in BC"
            className="h-11 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-base placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </form>
        <a href="/create-listing" className="hidden h-11 items-center rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary-hover sm:inline-flex">
          Sell an item
        </a>
        <AccountLink />
      </div>
    </header>
  );
}
