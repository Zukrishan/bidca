import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>
          <span className="font-semibold text-foreground">BidCa</span> · Local auctions for British Columbia residents
        </p>
        <nav className="flex gap-5">
          <Link href="/auctions" className="hover:text-foreground">Browse</Link>
          <a href="/create-listing" className="hover:text-foreground">Sell</a>
        </nav>
      </div>
    </footer>
  );
}
