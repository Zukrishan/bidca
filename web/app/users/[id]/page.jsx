import { notFound } from "next/navigation";
import { connection } from "next/server";

import { ListingGrid } from "@/components/ListingCard";
import { FeedbackList } from "@/components/profile/FeedbackList";
import { StatsRow } from "@/components/profile/StatsRow";
import { Badge } from "@/components/ui/badge";
import { apiGet } from "@/lib/api";
import { SITE_URL } from "@/lib/config";
import { formatDate } from "@/lib/format";

const getProfile = (id) => apiGet(`/users/${encodeURIComponent(id)}/profile`, { revalidate: 60 });

export async function generateMetadata({ params }) {
  await connection();
  const { id } = await params;
  const p = await getProfile(id);
  if (!p) return { title: "Profile not available", robots: { index: false } };
  return {
    title: `${p.full_name} — seller in ${p.city}, BC`,
    description: `${p.full_name} sells in ${p.city}, BC on BidCa: ${p.active_listings} active listings, ${p.total_sales} sales, ${p.total_ratings} ratings (${p.positive_percentage}% positive).`,
    alternates: { canonical: `/users/${id}` },
  };
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
    name: profile.full_name,
    address: { "@type": "PostalAddress", addressLocality: profile.city, addressRegion: "BC", addressCountry: "CA" },
    url: `${SITE_URL}/users/${id}`,
  };

  const stats = [
    { label: "Positive", value: profile.total_ratings ? `${profile.positive_percentage}%` : "—" },
    { label: "Ratings", value: profile.total_ratings },
    { label: "Total sales", value: profile.total_sales },
    { label: "Active listings", value: profile.active_listings },
  ];

  return (
    <div className="flex flex-col gap-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(personLd) }} />

      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{profile.full_name}</h1>
          {profile.verification_badge ? <Badge variant="success">Verified seller</Badge> : null}
        </div>
        <p className="text-sm text-muted-foreground">
          {profile.city}, {profile.province === "British Columbia" ? "BC" : profile.province}
          {profile.member_since ? ` · Member since ${formatDate(profile.member_since)}` : ""}
        </p>
      </header>

      <StatsRow stats={stats} />

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Active listings</h2>
        {listings.length > 0 ? (
          <ListingGrid listings={listings} />
        ) : (
          <p className="text-muted-foreground">No active listings right now.</p>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-semibold">Feedback</h2>
        <FeedbackList feedback={feedback} />
      </section>
    </div>
  );
}
