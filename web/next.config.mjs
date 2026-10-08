// Incremental port (Phase 4): Next.js serves the public, SEO-relevant routes
// (/, /auctions, /auctions/[id], /users/[id]). Every other path falls through
// to the CRA app, which runs on CRA_ORIGIN (dev :3101) until it is ported too.
const CRA_ORIGIN = process.env.CRA_ORIGIN || "http://localhost:3101";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle for the Docker image (no full node_modules at runtime).
  output: "standalone",
  async rewrites() {
    return {
      fallback: [{ source: "/:path*", destination: `${CRA_ORIGIN}/:path*` }],
    };
  },
};

export default nextConfig;
