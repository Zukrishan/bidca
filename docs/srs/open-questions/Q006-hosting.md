# Q006 — Hosting target
Status: **answered (26 Oct 2026, user): DigitalOcean.** Default setup: one Droplet running the existing `docker compose` stack (api, web, cra), with MongoDB as DigitalOcean Managed MongoDB rather than the bundled container; HTTPS via a reverse proxy (Caddy or nginx + certbot) in front of :3100/:8100. Sizing and the database plan are confirmed at deploy time.
