import Link from "next/link";

export const metadata = { title: "Page not found", robots: { index: false } };

export default function NotFound() {
  return (
    <div className="flex flex-col items-start gap-3 py-12">
      <h1 className="text-2xl font-bold tracking-tight">We couldn&apos;t find that page</h1>
      <p className="text-muted-foreground">It may have ended, been removed, or the link may be wrong.</p>
      <Link href="/auctions" className="text-sm font-medium text-primary hover:underline">Browse listings</Link>
    </div>
  );
}
