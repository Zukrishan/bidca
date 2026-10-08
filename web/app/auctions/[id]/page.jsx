import { cache } from "react";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { MapPin } from "lucide-react";

import { ListingGrid } from "@/components/ListingCard";
import { Badge } from "@/components/ui/badge";
import { Gallery } from "@/components/listing/Gallery";
import { BidPanel } from "@/components/listing/BidPanel";
import { ReportForm } from "@/components/listing/ReportForm";
import { apiGet } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { CONDITION_LABELS, LISTING_TYPE_LABELS, formatCAD, formatDate, headlinePrice, isAuction } from "@/lib/format";

const PUBLIC_STATUSES = ["active", "ended", "sold", "unsold"];

/** Public fetch first; sellers/admins get a second, cookie-authenticated try for pending/rejected listings. */
const loadListing = cache(async (id) => {
  const path = `/listings/${encodeURIComponent(id)}`;
  // Bid state must be live (a refresh after a bid or socket event has to show it), so no data cache.
  const listing = await apiGet(path, { revalidate: 0 });
  if (listing) return listing;
  const jar = await cookies();
  if (!jar.get("access_token")) return null;
  return apiGet(path, { cookie: jar.toString() });
});

const CONDITION_SCHEMA = {
  new: "https://schema.org/NewCondition",
  poor: "https://schema.org/DamagedCondition",
};

export async function generateMetadata({ params }) {
  const { id } = await params;
  const listing = await loadListing(id);
  if (!listing) return { title: "Listing not available", robots: { index: false } };
  const snippet = (listing.description || "").replace(/\s+/g, " ").slice(0, 155).trim();
  const description = `${snippet} ${formatCAD(headlinePrice(listing))} · ${listing.city}, BC`.trim();
  const image = listing.images?.[0];
  return {
    title: listing.title,
    description,
    alternates: { canonical: `/auctions/${id}` },
    robots: PUBLIC_STATUSES.includes(listing.status) ? undefined : { index: false, follow: false },
    openGraph: { title: listing.title, description, type: "website", url: `/auctions/${id}`, images: image ? [image] : undefined },
    twitter: { card: "summary_large_image", title: listing.title, description, images: image ? [image] : undefined },
  };
}

function ago(iso) {
  const s = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

const json = (o) => JSON.stringify(o).replace(/</g, "\\u003c");

export default async function ListingPage({ params }) {
  await connection();
  const { id } = await params;
  const listing = await loadListing(id);
  if (!listing) notFound();

  const auction = isAuction(listing);
  const isPublic = PUBLIC_STATUSES.includes(listing.status);
  const seller = listing.seller_info || {};
  const url = `${SITE_URL}/auctions/${id}`;
  const category = listing.category;
  const history = listing.bid_history || [];
  const related = listing.related_items || [];

  const productLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: listing.title,
    description: listing.description,
    image: listing.images || [],
    sku: id,
    category: [listing.category, listing.subcategory].filter(Boolean).join(" > "),
    itemCondition: CONDITION_SCHEMA[listing.condition] || "https://schema.org/UsedCondition",
    offers: {
      "@type": "Offer",
      priceCurrency: "CAD",
      price: String(auction ? (listing.current_bid ?? listing.starting_bid) : (listing.buy_it_now_price ?? listing.current_bid)),
      availability: listing.status === "active" ? "https://schema.org/InStock" : "https://schema.org/SoldOut",
      ...(auction && listing.end_time ? { priceValidUntil: listing.end_time.slice(0, 10) } : {}),
      url,
      seller: { "@type": "Person", name: seller.full_name || listing.seller_name },
      areaServed: `${listing.city}, BC`,
    },
  };
  const breadcrumbLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: category, item: `${SITE_URL}/auctions?category=${encodeURIComponent(category)}` },
      { "@type": "ListItem", position: 3, name: listing.title, item: url },
    ],
  };

  const details = [
    ["Condition", CONDITION_LABELS[listing.condition] || listing.condition],
    ["Category", [listing.category, listing.subcategory].filter(Boolean).join(" › ")],
    ["Listed", formatDate(listing.created_at)],
    auction && listing.end_time ? ["Ends", formatDate(listing.end_time)] : null,
    ["Views", listing.views_count ?? 0],
  ].filter(Boolean);

  return (
    <div className="flex flex-col gap-8 pb-24 lg:pb-0">{/* room for the sticky mobile bid bar */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json(productLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json(breadcrumbLd) }} />

      {!isPublic && (
        <p role="status" className="rounded-lg border border-border bg-muted p-3 text-sm">
          Pending review — only you can see this
        </p>
      )}

      <nav aria-label="Breadcrumb" className="text-sm text-muted-foreground">
        <ol className="flex flex-wrap items-center gap-x-2">
          <li><Link href="/" className="hover:underline">Home</Link></li>
          <li aria-hidden>›</li>
          <li><Link href={`/auctions?category=${encodeURIComponent(category)}`} className="hover:underline">{category}</Link></li>
          <li aria-hidden>›</li>
          <li aria-current="page" className="line-clamp-1 text-foreground">{listing.title}</li>
        </ol>
      </nav>

      <div className="grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Gallery images={listing.images} title={listing.title} />
        </div>

        <div className="flex flex-col gap-5 lg:col-span-2">
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              <Badge>{LISTING_TYPE_LABELS[listing.listing_type] || listing.listing_type}</Badge>
              {seller.verification_badge && <Badge variant="success">Verified seller</Badge>}
            </div>
            <h1 className="text-2xl font-bold tracking-tight">{listing.title}</h1>
            <p className="text-sm text-muted-foreground">
              {CONDITION_LABELS[listing.condition] || listing.condition} ·{" "}
              <span className="inline-flex items-center gap-1"><MapPin className="size-3" aria-hidden />Pickup in {listing.city}, BC</span>
            </p>
          </div>
          <BidPanel listing={listing} />
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        <div className="flex flex-col gap-8 lg:col-span-3">
          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">Description</h2>
            <p className="whitespace-pre-line text-foreground">{listing.description}</p>
          </section>

          <section className="flex flex-col gap-2">
            <h2 className="text-lg font-semibold">Details</h2>
            <dl className="divide-y divide-border rounded-lg border border-border bg-surface text-sm">
              {details.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 px-4 py-2.5">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="text-right">{v}</dd>
                </div>
              ))}
            </dl>
          </section>

          {auction && (
            <section className="flex flex-col gap-2">
              <h2 className="text-lg font-semibold">Bid history</h2>
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground">No bids yet. Be the first.</p>
              ) : (
                <ul className="divide-y divide-border rounded-lg border border-border bg-surface text-sm">
                  {history.map((b, i) => (
                    <li key={i} className="flex items-center justify-between gap-4 px-4 py-2.5">
                      <span>{b.bidder_name}</span>
                      <span className="flex items-baseline gap-3">
                        <span className="tabular font-medium">{formatCAD(b.amount)}</span>
                        <span className="text-xs text-muted-foreground">{ago(b.created_at)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>

        <aside className="flex flex-col gap-4 lg:col-span-2">
          <section className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4">
            <h2 className="text-lg font-semibold">Seller</h2>
            <Link href={`/users/${listing.seller_id}`} className="font-medium text-primary hover:underline">
              {seller.full_name || listing.seller_name}
            </Link>
            <p className="text-sm text-muted-foreground">{seller.city || listing.seller_city}, BC</p>
            <p className="text-sm">
              {seller.total_ratings ? `${Math.round(seller.positive_percentage)}% positive` : "No ratings yet"}
              {seller.total_ratings ? ` · ${seller.total_ratings} ratings` : ""}
            </p>
            <p className="text-sm text-muted-foreground">
              {seller.total_sales ?? 0} sales{seller.member_since ? ` · Member since ${formatDate(seller.member_since)}` : ""}
            </p>
          </section>
          {isPublic && <ReportForm listingId={id} />}
        </aside>
      </div>

      {related.length > 0 && (
        <section className="flex flex-col gap-4">
          <h2 className="text-xl font-semibold">Related items</h2>
          <ListingGrid listings={related} />
        </section>
      )}
    </div>
  );
}
