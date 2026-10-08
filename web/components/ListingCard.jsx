import Link from "next/link";
import { MapPin } from "lucide-react";

import { Countdown } from "@/components/Countdown";
import { formatCAD, headlinePrice, isAuction } from "@/lib/format";

/** Card content is fixed by the design: photo, title, price, bids, time left, city. Nothing else. */
export function ListingCard({ listing }) {
  const auction = isAuction(listing);
  const image = listing.images?.[0];

  return (
    <Link
      href={`/auctions/${listing._id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-border bg-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="aspect-square bg-muted">
        {image ? (
          // Listing photos come from arbitrary seller uploads (Cloudinary or URLs), so a plain img.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={image} alt={listing.title} loading="lazy" className="h-full w-full object-cover" />
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <h3 className="line-clamp-2 text-sm font-medium text-foreground group-hover:underline">{listing.title}</h3>
        <div className="mt-auto flex items-baseline justify-between gap-2 pt-1">
          <span className="tabular text-base font-semibold">
            {auction ? "" : "Buy now "}
            {formatCAD(headlinePrice(listing))}
          </span>
          {auction ? (
            <span className="text-xs text-muted-foreground">
              {listing.bid_count || 0} {listing.bid_count === 1 ? "bid" : "bids"}
            </span>
          ) : null}
        </div>
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          {auction && listing.end_time ? <Countdown endTime={listing.end_time} /> : <span />}
          <span className="inline-flex items-center gap-1">
            <MapPin className="size-3" aria-hidden />
            {listing.city}
          </span>
        </div>
      </div>
    </Link>
  );
}

export function ListingGrid({ listings, className = "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4" }) {
  return (
    <div className={`grid gap-4 ${className}`}>
      {listings.map((l) => (
        <ListingCard key={l._id} listing={l} />
      ))}
    </div>
  );
}
