import Link from "next/link";
import { connection } from "next/server";

import { ListingGrid } from "@/components/ListingCard";
import { apiGet } from "@/lib/api";
import { SITE_URL } from "@/lib/config";

export const metadata = {
  alternates: { canonical: "/" },
};

export default async function HomePage() {
  // Render per request (the build has no API); apiGet still caches the data for 30s.
  await connection();
  const [endingSoon, newest, catalog] = await Promise.all([
    apiGet("/listings/ending-soon"),
    apiGet("/listings?status=active&sort=newly_listed&limit=8"),
    apiGet("/categories", { revalidate: 3600 }),
  ]);
  const categories = Object.keys(catalog?.categories || {});
  const ending = (endingSoon?.listings || []).slice(0, 4);
  const fresh = newest?.listings || [];

  const websiteLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "BidCa",
    url: SITE_URL,
    potentialAction: {
      "@type": "SearchAction",
      target: `${SITE_URL}/auctions?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <div className="flex flex-col gap-12">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteLd) }} />

      <section className="flex flex-col gap-5">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Buy and sell locally across British Columbia.</h1>
        <nav aria-label="Categories" className="flex flex-wrap gap-2">
          {categories.map((c) => (
            <Link
              key={c}
              href={`/auctions?category=${encodeURIComponent(c)}`}
              className="rounded-full border border-border bg-surface px-4 py-2 text-sm hover:bg-muted"
            >
              {c}
            </Link>
          ))}
        </nav>
      </section>

      {ending.length > 0 && (
        <section className="flex flex-col gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-semibold">Ending soon</h2>
            <Link href="/auctions?sort=ending_soonest" className="text-sm font-medium text-primary hover:underline">See all</Link>
          </div>
          <ListingGrid listings={ending} />
        </section>
      )}

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">New in BC</h2>
          <Link href="/auctions?sort=newly_listed" className="text-sm font-medium text-primary hover:underline">See all</Link>
        </div>
        {fresh.length > 0 ? (
          <ListingGrid listings={fresh} />
        ) : (
          <p className="text-muted-foreground">
            No listings yet. <a href="/create-listing" className="font-medium text-primary hover:underline">Be the first to sell something.</a>
          </p>
        )}
      </section>
    </div>
  );
}
