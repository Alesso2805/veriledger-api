# Deploy VeriLedger on one server

One server runs everything behind Caddy, on one hostname (ADR-0005): the webapp at `/`, the API under `/api`. CI's `rehearsal` job follows steps 2 to 4 on every pull request, on `localhost`, so this runbook is checked from scratch each time.

## What you need

- A Linux server with Docker Engine and its Compose plugin; 2 GB of memory is enough for the demo.
- Ports 80 and 443 open to the internet. Caddy needs port 80 to obtain its certificate.
- A DNS `A` (and, with IPv6, `AAAA`) record for your domain, pointing at the server.

## 1. Get the deploy files

Only `deploy/` is used: the images come from GHCR.

```bash
git clone https://github.com/Alesso2805/veriledger-api.git /srv/veriledger && cd /srv/veriledger
```

## 2. Write `deploy/.env`

```bash
cp deploy/.env.example deploy/.env && chmod 600 deploy/.env
```

Fill in every empty value. The API refuses to start with an unsafe one:

| Variable | What to put |
| --- | --- |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`; at least 32 bytes |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | The admin the migrate service creates once. The development password is refused |
| `DOMAIN` | Your hostname, such as `demo.example.org` |
| `API_IMAGE_TAG`, `WEBAPP_IMAGE_TAG` | A `sha-<commit>` of each, or a release version. `main` moves with every push |
| `DEMO_MODE` | `true` for a public demo (ADR-0006), with its limits below it |

Leave `CORS_ORIGINS` empty: the browser sees one origin. Leave `ALLOW_PRIVATE_PEERS` false.

## 3. Start

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

What happens, in order:

1. PostgreSQL starts.
2. `migrate` applies the migrations, creates the admin, and exits. If it fails, the API does not start; `docker compose -f deploy/docker-compose.prod.yml logs migrate` says why.
3. The API starts and turns healthy once its database answers.
4. Caddy obtains a certificate for `DOMAIN` from Let's Encrypt and starts serving.

## 4. Verify

```bash
ADMIN_EMAIL=... ADMIN_PASSWORD=... sh deploy/verify.sh https://$DOMAIN
```

It checks five things over HTTPS:

- `/api/health` reports the database;
- `/api/docs` and `/api/openapi.json` answer;
- the webapp answers at `/`, at a deep link and at `/config.json`;
- no `Server` header is sent;
- the admin signs in.

## 5. Schedule the demo cleanup

With `DEMO_MODE=true`, expired demo accounts should be deleted every hour (ADR-0006). Their chain data stays. In the server's crontab:

```cron
0 * * * * cd /srv/veriledger && docker compose -f deploy/docker-compose.prod.yml run --rm --no-deps api python -m backend.app.cli.purge_demo_accounts
```

## 6. Update

1. Set the new `API_IMAGE_TAG` and `WEBAPP_IMAGE_TAG` in `deploy/.env`.
2. Run:

   ```bash
   docker compose -f deploy/docker-compose.prod.yml pull
   docker compose -f deploy/docker-compose.prod.yml up -d
   sh deploy/verify.sh https://$DOMAIN
   ```

`migrate` runs again and applies only what is new.

## 7. Roll back

Set the previous tags and run `up -d` again. The migrations only go forward. If the new version migrated the database, restore the backup taken before the update (VLA-28's runbook) before starting the old version.

## Rehearse on your own machine

This is the same as steps 2 to 4, with Caddy's internal CA instead of Let's Encrypt:

1. In `deploy/.env`, set `DOMAIN=localhost`, and `HTTP_PORT=8088` and `HTTPS_PORT=8443` if ports 80 and 443 are taken.
2. Start as in step 3.
3. Trust Caddy's CA for the check, as a browser would after importing it:

   ```bash
   docker compose -f deploy/docker-compose.prod.yml cp caddy:/data/caddy/pki/authorities/local/root.crt caddy-root.crt
   CURL_CA_BUNDLE="$PWD/caddy-root.crt" sh deploy/verify.sh https://localhost:8443
   ```

   On Windows, Git's `curl` uses Schannel and ignores `CURL_CA_BUNDLE`. Run the check from WSL, or in a Linux container that shares Caddy's network.
4. Clean up with `docker compose -f deploy/docker-compose.prod.yml down -v`.
