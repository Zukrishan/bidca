import Link from "next/link";
import { connection } from "next/server";

import { FilterDetails } from "@/components/browse/FilterDetails";
import { SaveSearchButton } from "@/components/browse/SaveSearchButton";
import { SortSelect } from "@/components/browse/SortSelect";
import { ListingGrid } from "@/components/ListingCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiGet } from "@/lib/api";

const FORM_ID = "browse-filters";
const LIMIT = 24;

const TYPES = [
  ["", "All"],
  ["auction", "Auction"],
  ["fixed_price", "Buy now"],
  ["auction_bin", "Auction + Buy now"],
];
const SORTS = [
  ["ending_soonest", "Ending soonest"],
  ["newly_listed", "Newly listed"],
  ["lowest_price", "Lowest price"],
  ["highest_price", "Highest price"],
  ["most_bids", "Most bids"],
];
const TYPE_VALUES = TYPES.map(([v]) => v).filter(Boolean);
const SORT_VALUES = SORTS.map(([v]) => v);

const first = (v) => (Array.isArray(v) ? v[0] : v) ?? "";
const num = (v) => {
  const s = first(v).trim();
  return s !== "" && Number.isFinite(Number(s)) && Number(s) >= 0 ? s : "";
};

/** Normalise raw searchParams to the known, valid set. */
function parseParams(sp) {
  const type = first(sp.listing_type);
  const sort = first(sp.sort);
  const page = parseInt(first(sp.page), 10);
  return {
    q: first(sp.q).trim().slice(0, 100),
    category: first(sp.category),
    city: first(sp.city),
    min_price: num(sp.min_price),
    max_price: num(sp.max_price),
    listing_type: TYPE_VALUES.includes(type) ? type : "",
    sort: SORT_VALUES.includes(sort) ? sort : "ending_soonest",
    page: Number.isInteger(page) && page > 0 ? page : 1,
  };
}

function toQuery(params) {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v !== undefined && v !== null) usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

function titleFor({ q, category, city }) {
  const what = q || category;
  const base = what ? `${what} for sale` : "Auctions and listings";
  return city ? `${base} in ${city}` : `${base} in BC`;
}

export async function generateMetadata({ searchParams }) {
  const raw = await searchParams;
  const p = parseParams(raw);
  const thin = p.q || p.min_price || p.max_price || p.page > 1 || first(raw.sort);
  const where = p.city || "BC";
  return {
    title: titleFor(p),
    description: `Browse local ${p.category ? p.category.toLowerCase() : "auctions and listings"} in ${where}. Bid or buy now from sellers across British Columbia.`,
    alternates: { canonical: `/auctions${toQuery({ category: p.category, city: p.city })}` },
    robots: thin ? { index: false, follow: true } : { index: true, follow: true },
  };
}

function pageList(page, pages) {
  const set = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...set].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const out = [];
  nums.forEach((n, i) => {
    if (i > 0 && n - nums[i - 1] > 1) out.push("gap" + n);
    out.push(n);
  });
  return out;
}

function Pagination({ params, page, pages }) {
  if (pages <= 1) return null;
  const href = (n) => `/auctions${toQuery({ ...params, page: n > 1 ? n : "" })}`;
  const item = "inline-flex h-11 min-w-11 items-center justify-center rounded-lg border px-3 text-sm";
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-center gap-2">
      {page > 1 && (
        <Link href={href(page - 1)} rel="prev" className={`${item} border-border bg-surface hover:bg-muted`}>
          Previous
        </Link>
      )}
      {pageList(page, pages).map((n) =>
        typeof n === "string" ? (
          <span key={n} aria-hidden className="px-1 text-muted-foreground">…</span>
        ) : n === page ? (
          <span key={n} aria-current="page" className={`${item} border-primary bg-primary font-semibold text-primary-foreground`}>
            {n}
          </span>
        ) : (
          <Link key={n} href={href(n)} aria-label={`Page ${n}`} className={`${item} border-border bg-surface hover:bg-muted`}>
            {n}
          </Link>
        )
      )}
      {page < pages && (
        <Link href={href(page + 1)} rel="next" className={`${item} border-border bg-surface hover:bg-muted`}>
          Next
        </Link>
      )}
    </nav>
  );
}

const selectClass =
  "h-11 w-full rounded-lg border border-border bg-surface px-3 text-base text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default async function AuctionsPage({ searchParams }) {
  await connection();
  const p = parseParams(await searchParams);

  const api = new URLSearchParams({ status: "active", limit: String(LIMIT), sort: p.sort, page: String(p.page) });
  if (p.q) api.set("q", p.q); // plain text: the API escapes it (contract v1 changelog)
  for (const k of ["category", "city", "min_price", "max_price", "listing_type"]) if (p[k]) api.set(k, p[k]);

  const [data, catalog, cityData] = await Promise.all([
    apiGet(`/listings?${api}`),
    apiGet("/categories", { revalidate: 3600 }),
    apiGet("/cities", { revalidate: 3600 }),
  ]);
  const listings = data?.listings || [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;
  const categories = Object.keys(catalog?.categories || {});
  const cities = cityData?.cities || [];

  const heading = p.q
    ? `${total} ${total === 1 ? "result" : "results"} for "${p.q}"${p.category ? ` in ${p.category}` : ""}`
    : p.category || "All listings";
  const filtered = p.q || p.category || p.city || p.min_price || p.max_price || p.listing_type;
  const label = "mb-1 block text-sm font-medium";

  return (
    <div className="flex flex-col gap-6 lg:grid lg:grid-cols-[240px_1fr] lg:items-start lg:gap-8">
      <aside aria-label="Filters">
        <FilterDetails summary="Filters">
          <form id={FORM_ID} method="get" action="/auctions" className="flex flex-col gap-5">
            <div>
              <label htmlFor="q" className={label}>Search</label>
              <Input id="q" name="q" type="search" defaultValue={p.q} placeholder="What are you looking for?" />
            </div>

            <fieldset className="flex flex-col">
              <legend className="mb-1 text-sm font-medium">Listing type</legend>
              {TYPES.map(([v, text]) => (
                <label key={v || "all"} className="flex min-h-11 items-center gap-3 text-sm">
                  <input type="radio" name="listing_type" value={v} defaultChecked={p.listing_type === v} className="size-4 accent-primary" />
                  {text}
                </label>
              ))}
            </fieldset>

            <div>
              <label htmlFor="category" className={label}>Category</label>
              <select id="category" name="category" defaultValue={p.category} className={selectClass}>
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="city" className={label}>City</label>
              <select id="city" name="city" defaultValue={p.city} className={selectClass}>
                <option value="">All of BC</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <fieldset>
              <legend className="mb-1 text-sm font-medium">Price (CAD)</legend>
              <div className="flex items-center gap-2">
                <Input name="min_price" type="number" min="0" step="1" inputMode="numeric" aria-label="Minimum price" placeholder="Min" defaultValue={p.min_price} />
                <span aria-hidden className="text-muted-foreground">to</span>
                <Input name="max_price" type="number" min="0" step="1" inputMode="numeric" aria-label="Maximum price" placeholder="Max" defaultValue={p.max_price} />
              </div>
            </fieldset>

            <div className="flex items-center gap-4">
              <Button type="submit">Apply</Button>
              <Link href="/auctions" className="inline-flex h-11 items-center text-sm font-medium text-primary hover:underline">
                Clear filters
              </Link>
            </div>
          </form>
        </FilterDetails>
      </aside>

      <section className="flex min-w-0 flex-col gap-5" aria-labelledby="results-heading">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 id="results-heading" className="text-2xl font-bold tracking-tight">{heading}</h1>
            {!p.q && <p className="text-sm text-muted-foreground">{total} {total === 1 ? "listing" : "listings"}</p>}
          </div>
          <SortSelect formId={FORM_ID} value={p.sort} options={SORTS} />
        </div>

        {filtered && (
          <SaveSearchButton
            name={heading.slice(0, 80)}
            query={p.q}
            category={p.category}
            minPrice={p.min_price}
            maxPrice={p.max_price}
          />
        )}

        {listings.length > 0 ? (
          <>
            <ListingGrid listings={listings} className="grid-cols-2 lg:grid-cols-3" />
            <Pagination params={p} page={p.page} pages={pages} />
          </>
        ) : (
          <div className="rounded-lg border border-border bg-surface p-8 text-center">
            <p className="font-medium">No listings match your search.</p>
            <p className="mt-1 text-sm text-muted-foreground">Try different words or fewer filters.</p>
            <Link href="/auctions" className="mt-4 inline-flex h-11 items-center text-sm font-medium text-primary hover:underline">
              Clear filters
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
