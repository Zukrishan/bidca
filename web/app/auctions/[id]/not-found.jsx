import Link from "next/link";

export const metadata = { title: "Listing not available", robots: { index: false } };

export default function ListingNotFound() {
  return (
    <div className="flex flex-col items-start gap-4 py-16">
      <h1 className="text-2xl font-bold tracking-tight">This listing isn&apos;t available</h1>
      <p className="text-muted-foreground">It may have been removed, or the link is wrong.</p>
      <Link href="/auctions" className="font-medium text-primary hover:underline">Browse all listings</Link>
    </div>
  );
}
