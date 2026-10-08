import { connection } from "next/server";

import { apiGet } from "@/lib/api";
import { SITE_URL } from "@/lib/config";

export default async function sitemap() {
  await connection();
  const entries = [
    { url: `${SITE_URL}/` },
    { url: `${SITE_URL}/auctions` },
  ];
  try {
    const catalog = await apiGet("/categories", { revalidate: 3600 });
    const dynamic = [];
    for (const c of Object.keys(catalog?.categories || {})) {
      dynamic.push({ url: `${SITE_URL}/auctions?category=${encodeURIComponent(c)}` });
    }
    const sellers = new Set();
    let page = 1;
    let pages = 1;
    do {
      const data = await apiGet(`/listings?status=active&limit=200&page=${page}`, { revalidate: 300 });
      for (const l of data?.listings || []) {
        dynamic.push({ url: `${SITE_URL}/auctions/${l._id}`, lastModified: l.created_at });
        if (l.seller_id) sellers.add(l.seller_id);
      }
      pages = data?.pages || 1;
      page += 1;
    } while (page <= pages);
    for (const s of sellers) dynamic.push({ url: `${SITE_URL}/users/${s}` });
    return [...entries, ...dynamic];
  } catch {
    return entries;
  }
}
