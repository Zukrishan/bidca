#!/usr/bin/env node
// Phase 4 gate (R22 / NFR-01): what a crawler gets from the public routes — raw server HTML, no JS.
//
//   SITE=http://localhost:3100 API=http://localhost:8100 [PENDING_ID=<id>] node scripts/check-seo.mjs
//
// Needs the API with at least one active listing (backend/scripts/seed_demo.py) and, for the
// fallback check, the CRA app on CRA_ORIGIN. Exits 1 if any check fails.

const SITE = (process.env.SITE || "http://localhost:3100").replace(/\/$/, "");
const API = (process.env.API || "http://localhost:8100").replace(/\/$/, "");
const PENDING_ID = process.env.PENDING_ID;

let failures = 0;
const check = (ok, label) => {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (!ok) failures++;
};

async function page(path) {
  const res = await fetch(SITE + path, { redirect: "manual" });
  return { status: res.status, html: await res.text() };
}

const tag = (html, re) => (html.match(re) || [])[1];
const title = (html) => tag(html, /<title>([^<]*)<\/title>/);
const meta = (html, name) =>
  tag(html, new RegExp(`<meta[^>]+(?:name|property)="${name}"[^>]+content="([^"]*)"`)) ||
  tag(html, new RegExp(`<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="${name}"`));
const canonical = (html) => tag(html, /<link[^>]+rel="canonical"[^>]+href="([^"]*)"/);
const jsonLd = (html) =>
  [...html.matchAll(/<script type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].flatMap((m) => {
    try {
      const v = JSON.parse(m[1]);
      return Array.isArray(v) ? v : [v];
    } catch {
      return [{ "@type": "INVALID_JSON" }];
    }
  });
const ldTypes = (html) => jsonLd(html).map((d) => d["@type"]);
const decode = (s = "") => s.replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"');

const listings = (await (await fetch(`${API}/api/listings?status=active&limit=5`)).json()).listings;
if (!listings?.length) {
  console.error("No active listings in the API — run backend/scripts/seed_demo.py first.");
  process.exit(1);
}
const listing = listings[0];

// Home
{
  const { status, html } = await page("/");
  check(status === 200, "/ → 200");
  check(!!title(html), `/ has <title> (${title(html)})`);
  check(!!meta(html, "description"), "/ has meta description");
  check(/^https?:\/\/[^/]+\/?$/.test(canonical(html) || ""), `/ canonical is the site root (${canonical(html)})`);
  check(ldTypes(html).includes("WebSite"), "/ JSON-LD WebSite");
  check(html.includes(`/auctions/${listings[0]._id}`) || /\/auctions\/[0-9a-f]{24}/.test(html), "/ server-renders listing links");
}

// Browse
{
  const { status, html } = await page("/auctions");
  check(status === 200, "/auctions → 200");
  check(!!title(html) && !!meta(html, "description"), "/auctions title + description");
  check(/\/auctions\/[0-9a-f]{24}/.test(html), "/auctions server-renders results");
  check(!/noindex/.test(meta(html, "robots") || ""), "/auctions is indexable");
  const q = await page("/auctions?q=zzzz-no-match");
  check(q.status === 200, "/auctions?q=… → 200 (empty state)");
  check(/noindex/.test(meta(q.html, "robots") || ""), "/auctions?q=… is noindex");
}

// Listing detail
{
  const { status, html } = await page(`/auctions/${listing._id}`);
  check(status === 200, `/auctions/${listing._id} → 200`);
  check(decode(title(html)).includes(listing.title), "detail <title> contains the listing title");
  check(!!meta(html, "description"), "detail meta description");
  check(canonical(html)?.endsWith(`/auctions/${listing._id}`), "detail canonical");
  check(!!meta(html, "og:image"), "detail og:image");
  const product = jsonLd(html).find((d) => d["@type"] === "Product");
  check(!!product, "detail JSON-LD Product");
  check(product?.offers?.priceCurrency === "CAD" && product?.offers?.price != null, "Product offer price in CAD");
  check(ldTypes(html).includes("BreadcrumbList"), "detail JSON-LD BreadcrumbList");
  check(!html.includes("highest_bidder_max_bid"), "detail never ships the proxy max (D9)");
  check(!/escrow|guarantee|releasing funds/i.test(html), "no payment/escrow copy (Q004)");
}
if (PENDING_ID) {
  const { status, html } = await page(`/auctions/${PENDING_ID}`);
  check(status === 404, `pending listing → 404 for visitors (got ${status})`);
  check(!html.includes("should not be public"), "pending listing content not rendered");
}

// Seller profile
{
  const { status, html } = await page(`/users/${listing.seller_id}`);
  check(status === 200, `/users/${listing.seller_id} → 200`);
  check(!!title(html) && canonical(html)?.endsWith(`/users/${listing.seller_id}`), "profile title + canonical");
  check(ldTypes(html).includes("Person"), "profile JSON-LD Person");
  check(/\/auctions\/[0-9a-f]{24}/.test(html), "profile server-renders the seller's listings");
}

// Sitemap + robots
{
  const sm = await page("/sitemap.xml");
  check(sm.status === 200 && sm.html.includes("<urlset"), "/sitemap.xml → 200");
  check(sm.html.includes(`/auctions/${listing._id}</loc>`), "sitemap lists an active listing");
  if (PENDING_ID) check(!sm.html.includes(PENDING_ID), "sitemap omits the pending listing");
  const rb = await page("/robots.txt");
  check(rb.status === 200 && /Sitemap:/i.test(rb.html) && /Disallow: \/admin/.test(rb.html), "/robots.txt with sitemap + disallows");
}

// Everything else falls through to the CRA app
{
  const { status, html } = await page("/login");
  check(status === 200 && html.includes('<div id="root">'), "/login falls back to the CRA app");
}

// Unapproved content must not leak anywhere public
for (const path of ["/", "/auctions", "/sitemap.xml"]) {
  const { html } = await page(path);
  check(!html.includes("should not be public"), `${path} has no pending listing`);
}

console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
