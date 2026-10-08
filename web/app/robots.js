import { SITE_URL } from "@/lib/config";

export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/seller", "/watchlist", "/create-listing", "/verification", "/messages", "/admin", "/login", "/register", "/verify-email"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
