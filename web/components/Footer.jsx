import Link from "next/link";

// How It Works, Terms, Privacy and About are linked prominently, not buried (FR-33, source L48).
const INFO_LINKS = [
  { href: "/how-it-works", label: "How It Works" },
  { href: "/terms", label: "Terms of Service" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/about", label: "About Us" },
];

export function Footer() {
  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-6 px-4 py-8 text-sm text-muted-foreground sm:px-6">
        <nav aria-label="About BidCa" className="flex flex-wrap gap-x-6 gap-y-2 text-base font-semibold text-foreground">
          {INFO_LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-primary hover:underline">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p>
            <span className="font-semibold text-foreground">BidCa</span> · Local auctions for British Columbia residents.
            BidCa never handles payments — buyers and sellers exchange in person.
          </p>
          <nav className="flex gap-5">
            <Link href="/auctions" className="hover:text-foreground">Browse</Link>
            <a href="/create-listing" className="hover:text-foreground">Sell</a>
          </nav>
        </div>
      </div>
    </footer>
  );
}
