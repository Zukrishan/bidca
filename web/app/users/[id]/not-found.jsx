import Link from "next/link";

export const metadata = { title: "Profile not available", robots: { index: false } };

export default function UserNotFound() {
  return (
    <div className="flex flex-col items-start gap-3 py-12">
      <h1 className="text-2xl font-bold tracking-tight">This profile isn&apos;t available</h1>
      <p className="text-muted-foreground">The seller may not exist, or the link may be wrong.</p>
      <Link href="/auctions" className="text-sm font-medium text-primary hover:underline">Browse listings</Link>
    </div>
  );
}
