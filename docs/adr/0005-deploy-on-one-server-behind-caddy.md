# ADR-0005: Deploy the API and the webapp on one server, behind Caddy, on one hostname

- **Status:** Proposed
- **Date:** 2026-10-20
- **Related:** VLA-21 to VLA-23, VLA-27, VLA-28; webapp VLW-21, VLW-22, VLW-25 and its ADR-0003; willay ADR-0010 (same pattern)

## Context

The goal of Sprint 4 is a demo anyone can try from a link, at no cost. The stack is small: PostgreSQL, the API, a `migrate` step and the webapp's static files. Today everything assumes `localhost`: the webapp's API URL is `http://127.0.0.1:8000` in its code, CORS allows only `localhost:5173`, and Compose runs the API with `--reload` and a bind mount.

## Options

1. **Webapp on a static host** (Netlify, Vercel, Cloudflare Pages) **and the API on a platform with managed Postgres** (Render, Fly.io, Railway). Little to maintain, but two origins (CORS), free tiers that sleep or expire their database, and two providers to configure.
2. **One server with Docker Compose and Caddy,** one hostname: `/` serves the webapp, `/api` the API. One origin (no CORS in production), one certificate, the same Compose file as on a laptop. Willay already runs this way (its ADR-0010), so the runbook is known.
3. **Kubernetes.** Far more machinery than one demo needs.

## Decision (proposed)

Option 2.

- `deploy/docker-compose.prod.yml` on top of `docker-compose.yml`: no bind mounts, no published ports except Caddy's, `APP_ENV=production`, secrets from the server's `.env` (VLA-23).
- Caddy gets the certificate on its own and routes `/api/*` to the API with the prefix stripped (FastAPI `root_path="/api"` keeps the OpenAPI links right) and everything else to the webapp container.
- The webapp image is built once and reads its API URL from `/config.json` at start (VLW-21), so the same image serves any hostname.
- Target: an Oracle Cloud Always Free ARM server or Google Cloud's free trial, with a free DuckDNS hostname, as in willay's runbook. Every image must exist for arm64.

## Consequences

- One server is a single point of failure; acceptable for a demo. Backups of the Postgres volume are the runbook of VLA-28.
- CORS stays only for local development (Vite on port 5173); in production the browser sees one origin.
- If the product owner prefers option 1, VLW-21 and VLA-21 still apply (configurable API URL and CORS origins); only VLA-27 and VLW-25 change.
