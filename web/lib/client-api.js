import { PUBLIC_API_URL } from "@/lib/config";

/** Browser call to the API with the httpOnly auth cookies (contract D5). Throws Error(detail) on failure. */
export async function clientApi(path, { method = "GET", body } = {}) {
  const res = await fetch(`${PUBLIC_API_URL}/api${path}`, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}
