// Server-side fetches may use an internal URL (API_URL); the browser always uses NEXT_PUBLIC_API_URL.
export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
export const SERVER_API_URL = process.env.API_URL || PUBLIC_API_URL;
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3100";
export const SITE_NAME = "BidCa";
