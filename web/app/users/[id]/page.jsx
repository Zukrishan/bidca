import { notFound } from "next/navigation";
import { connection } from "next/server";
import { BadgeCheck } from "lucide-react";

import { JsonLd } from "@/components/JsonLd";
import { ListingGrid } from "@/components/ListingCard";
import { FeedbackList } from "@/components/profile/FeedbackList";
import { OwnerPanel } from "@/components/profile/OwnerPanel";
import { RatingSummary } from "@/components/profile/Rating";
import { StatsRow } from "@/components/profile/StatsRow";
import { Badge } from "@/components/ui/badge";
import { apiGet } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { formatDate } from "@/lib/format";

const getProfile = (id) => apiGet(`/users/${encodeURIComponent(id)}/profile`, { revalidate: 60 });

const TIER_LABELS = { top_seller: "Top Seller", power_bidder: "Power Bidder" };
const EXCHANGE_LABELS = {
  cash_on_pickup: "Cash on pickup",
  e_transfer: "E-transfer",
  meet_public: "Meet in a public place",
};

export async function generateMetadata({ params }) {
  await connection();
  const { id } = await params;
  const p = await getProfile(id);
  if (!p) return { title: "Profile not available", robots: { index: false } };
  return {
    title: `${p.display_name} — member in ${p.city}, BC`,
    description: `${p.display_name} buys and sells in ${p.city}, BC on BidCa: ${p.active_listings} active listings, ${p.completed_as_seller} completed sales, ${p.completed_as_buyer} completed purchases, ${p.total_ratings} ratings.`,
    alternates: { canonical: `/users/${id}` },
  };
}

function Avatar({ profile }) {
  if (profile.avatar_url) {
    // Cloudinary upload (validated server-side); a plain img like the listing photos
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={profile.avatar_url} alt="" className="size-20 rounded-full border border-border object-cover" />;
  }
  return (
    <span aria-hidden className="flex size-20 items-center justify-center rounded-full bg-muted text-2xl font-semibold text-muted-foreground">
      {profile.display_name?.charAt(0)?.toUpperCase() || "?"}
    </span>
  );
}

export default async function UserProfilePage({ params }) {
  await connection();
  const { id } = await params;
  const profile = await getProfile(id);
  if (!profile) notFound();

  const [fb, list] = await Promise.all([
    apiGet(`/users/${encodeURIComponent(id)}/feedback`, { revalidate: 60 }),
    apiGet(`/listings?status=active&seller_id=${encodeURIComponent(id)}&limit=24`, { revalidate: 60 }),
  ]);
  const feedback = fb?.feedback || [];
  const listings = list?.listings || [];

  const personLd = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: profile.display_name,
    address: { "@type": "PostalAddress", addressLocality: profile.city, addressRegion: "BC", addressCountry: "CA" },
    url: `${SITE_URL}/users/${id}`,
  };

  const stats = [
    { label: "Completed as seller", value: profile.completed_as_seller },
    { label: "Completed as buyer", value: profile.completed_as_buyer },
    { label: "Ratings", value: profile.total_ratings },
    { label: "Active listings", value: profile.active_listings },
  ];

  return (
    <div className="flex flex-col gap-10">
      <JsonLd data={personLd} />

      <header className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <Avatar profile={profile} />
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{profile.display_name}</h1>
            {profile.verified_badge ? (
              <Badge variant="success" title="Phone number verified, with at least two completed deals">
                <BadgeCheck aria-hidden className="mr-1 size-3.5" />
                Phone verified
              </Badge>
            ) : null}
            {(profile.tiers || []).map((t) => (
              <Badge key={t}>{TIER_LABELS[t] || t}</Badge>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">
            {profile.city}, {profile.province === "British Columbia" ? "BC" : profile.province}
            {profile.member_since ? ` · Member since ${formatDate(profile.member_since)}` : ""}
          </p>
          <RatingSummary ratings={profile.ratings} />
        </div>
      </header>

      <StatsRow stats={stats} />

      <section className="flex flex-col gap-2">
        <h2 className="text-xl font-semibold">Preferred exchange</h2>
        {profile.exchange_methods?.length ? (
          <ul className="flex flex-wrap gap-2">
            {profile.exchange_methods.map((m) => (
              <li key={m}><Badge>{EXCHANGE_LABELS[m] || m}</Badge></li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">Not set yet — agree on how to meet in the transaction chat.</p>
        )}
        <p className="text-xs text-muted-foreground">BidCa never handles money: buyer and seller exchange in person.</p>
      </section>

      <OwnerPanel userId={profile.id} />

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Active listings</h2>
        {listings.length > 0 ? (
          <ListingGrid listings={listings} />
        ) : (
          <p className="text-muted-foreground">No active listings right now.</p>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Ratings and comments</h2>
        <FeedbackList feedback={feedback} />
      </section>
    </div>
  );
}
