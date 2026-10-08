import { SERVER_API_URL } from "@/lib/config";

/**
 * GET an /api endpoint from a server component. Returns null on 404 so pages can call notFound().
 * Public data is cached for `revalidate` seconds; pass `cookie` for a per-user, uncached fetch.
 */
export async function apiGet(path, { revalidate = 30, cookie } = {}) {
  const init = cookie
    ? { cache: "no-store", headers: { cookie } }
    : { next: { revalidate } };
  const res = await fetch(`${SERVER_API_URL}/api${path}`, init);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /api${path} failed: ${res.status}`);
  return res.json();
}
