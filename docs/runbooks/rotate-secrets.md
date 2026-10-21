# Rotate a secret

Each secret lives in `deploy/.env` on the server ([deploy.md](deploy.md)). Rotate one when it may have leaked, when someone who knew it leaves, or on a schedule. Generate new values the same way as in deploy.md, step 2. Every command runs from the repository root.

## `SECRET_KEY`: the key that signs every session

1. Put a new value in `deploy/.env`:

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. Recreate the API, which reads it at start:

   ```bash
   docker compose -f deploy/docker-compose.prod.yml up -d api
   ```

What happens:

- Every token signed with the old key answers 401, so everyone signs in again.
- A demo account has no password, so its session cannot come back. The visitor starts a new demo. What the old one recorded stays on the chain, and the hourly cleanup removes the account when it expires.
- Production refuses a key under 32 bytes, the development default and the example value. If the API does not come up, `docker compose -f deploy/docker-compose.prod.yml logs api` says which.

## The admin's password

The seed creates the admin once and never overwrites it, so a new `ADMIN_PASSWORD` needs its own command:

1. Put the new password in `ADMIN_PASSWORD` in `deploy/.env`.
2. Run:

   ```bash
   docker compose -f deploy/docker-compose.prod.yml run --rm --no-deps api python -m backend.app.cli.set_admin_password
   ```

The admin of `ADMIN_EMAIL` now signs in with the new password, and the old one answers 401. Tokens the admin already holds stay valid until they expire, 30 minutes at most. To end them at once, rotate `SECRET_KEY` too.

Production refuses an empty password and the development one. In development the same command is `make set-admin-password`.

## `PEER_TOKEN`: what the nodes of one network share

Every node must hold the same token (SPEC › Peer token). While two nodes disagree, each refuses the other's broadcasts and resolve requests with 401. Nothing is lost: transactions stay on the node that received them, and the next resolve after the change brings the chains together.

1. Generate one value:

   ```bash
   openssl rand -hex 32
   ```

2. Put it in `PEER_TOKEN` in `deploy/.env` on every node, then recreate each API, one after another, as close together as you can:

   ```bash
   docker compose -f deploy/docker-compose.prod.yml up -d api
   ```

3. On one node, ask the network to converge, with an admin's token:

   ```bash
   curl -fsS -X POST -H "Authorization: Bearer $TOKEN" https://$DOMAIN/api/nodes/resolve
   ```

## The database password

`POSTGRES_PASSWORD` is not one of the three above, but it rotates the same way. The database must learn the new password before the API does:

```bash
docker compose -f deploy/docker-compose.prod.yml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER USER \"$POSTGRES_USER\" PASSWORD '"'"'<new password>'"'"'"'
```

Then put the same value in `deploy/.env`, and recreate everything with `up -d`.
