# Sprint 4 — Safe production settings, readiness and abuse limits, a deployment rehearsed in CI, runbooks, and the 1.0.0 release (VLA-21, VLA-24, VLA-26 to VLA-30, VLA-38)

**Status as of 2026-10-21:** closed on October 21, 2026, ahead of the planned December 7 – 20, except for one step: deploying on a server.

- Seven of the eight stories are done, 14 of 19 points.
- VLA-27 (5 points) is prepared and rehearsed in CI on every pull request. It waits for the product owner's server, a Google Cloud VM with a DuckDNS name.
- VLA-31 (Could, 3 points) moved to after 1.0.0.

**The webapp's counterpart:**

- VLW-23, the end-to-end flows, runs against this sprint's published image through `docker-compose.ghcr.yml`.
- VLW-24 is done.
- VLW-25 is in progress. Its image is on GHCR, and its PR #51 runs our deploy runbook with its own image and its browser flows through our Caddy. That PR pins the API at 1.0.0.
- VLW-26, the webapp's 1.0.0, comes after the deployment, because its screenshots come from the deployed instance.

**Order:** VLA-21, VLA-24, VLA-38, VLA-26, VLA-29, VLA-27, VLA-28, VLA-30. The first three come first because the webapp's VLW-23 runs against them (#45).

**Decisions it waited for, all taken by the product owner on 2026-10-21**

- **VLA-38 added** (#45): a Compose file that runs the published image, asked for by the webapp so that its CI does not build the API.
- **VLA-27 prepared and rehearsed without a server** (#45). It is deployed when there is one.
- **Required checks on `main`.** `image` and `compose` became required, which answered Sprint 3's open question. `rehearsal` became required once it existed. All four are required today.
- **`/health` is a readiness check** (VLA-26, option A). It answers 503 without its database, and CI's `image` job got a PostgreSQL service so that the image's healthcheck can pass.
- **The admin seed runs inside the `migrate` service** (VLA-24), right after the migrations. The API starts only if both succeed.
- **VLA-31 after 1.0.0.** Amounts as strings would change the JSON the webapp's generated types read, so it is coordinated with the webapp first. Under semantic versioning it needs a major version.
- **The webapp's image is public on GHCR,** so the rehearsal pulls it without credentials.
- **The `v1.0.0` tag and its GitHub release,** after #54 merged.

## What was delivered

`main` is at `fd109e5`, tagged `v1.0.0`. CI is green on all four required checks (`checks`, `image`, `compose`, `rehearsal`). `ghcr.io/alesso2805/veriledger-api:1.0.0` is published for amd64 and arm64, and the release notes are the changelog's 1.0.0 section. Every PR below was merged with a merge commit after its CI run passed.

| Story | PRs | Result | Verification |
| --- | --- | --- | --- |
| VLA-21 | #46 | With `APP_ENV=production` the API does not start when `SECRET_KEY` is missing, the example value or shorter than 32 bytes. `APP_DEBUG` is off unless set. Browser origins come from `CORS_ORIGINS`. `/wallets/generate` answers 404 outside development. AR-15 passes and loses its `xfail` | `test_settings.py`, `test_cors.py` (the app built in a subprocess with other origins), `test_wallet_generate.py` |
| VLA-24 | #47 | The seed reads `ADMIN_EMAIL` and `ADMIN_PASSWORD` from the environment and stays idempotent. In production it refuses an empty or the development password, and `migrate` fails, so the API does not start | `test_seed.py`, `test_settings.py`; CI's `compose` job |
| VLA-38 | #48 | `docker-compose.ghcr.yml` runs `migrate` and the API from `ghcr.io/alesso2805/veriledger-api:${API_IMAGE_TAG}`, with no build, no bind mount and the variables of `docker-compose.yml` | CI's `compose` job starts it with the image that the same run built, and `/health` answers |
| VLA-26 | #49 | `/health` runs `SELECT 1` with a 2-second timeout and reports `database`. Without the database it answers 503 with `"database": "unreachable"`. Each request is logged once with its id, as JSON in production. A client's `X-Request-ID` is kept only when it matches `[A-Za-z0-9._-]{1,64}` | `test_health.py`, `test_logger.py`, `test_documented_status_codes.py` |
| VLA-29 | #50 | Five sign-ins a minute per address, 60 transactions a minute per sender, and one mining request at a time per node. Each answers 429 with `Retry-After`, is set through the environment, and 0 or `false` turns it off | `test_abuse_limits.py`, `test_mining.py`; the webapp's end-to-end flows retry after a 429 or a 409, as a person reading the toast would |
| VLA-27 | #51, #52 | `deploy/Caddyfile` puts the webapp at `/` and the API under `/api` on one hostname, with Let's Encrypt for a real domain and Caddy's own CA for `localhost`. The API publishes no port and trusts Caddy's `X-Forwarded-For`. `docs/runbooks/deploy.md` and `deploy/verify.sh`. This PR adds the runbook's notes for a cloud VM with a dynamic DNS name | `test_behind_caddy.py`; CI's `rehearsal` job follows the runbook on `localhost`, checks the certificate against Caddy's CA, and runs `verify.sh` and the webapp's smoke test |
| VLA-28 | #52, #53 | `deploy/backup.sh` and `deploy/restore.sh`. The command `python -m backend.app.cli.set_admin_password`, since the seed never overwrites a password. `backup-and-restore.md` and `rotate-secrets.md` | `test_set_admin_password.py`; on every PR, `rehearsal` mines a block, backs up, drops every table, restores, and finds the block again |
| VLA-30 | #54 | Version 1.0.0 in the app, `pyproject.toml` and `docs/openapi.json`. `CHANGELOG.md` in the Keep a Changelog format. A README that matches the stack, with commands that work from the repository root | `test_version.py` keeps the app's version, pyproject's and the changelog's entry in step; the README's steps were run as written |

**How to check the whole sprint from a clean clone**

```bash
git clone https://github.com/Alesso2805/veriledger-api.git && cd veriledger-api
uv sync                                   # Python 3.12.13, runtime and dev dependencies from uv.lock
make lint && uv run ruff format --check backend && make typecheck
docker run -d --rm --name vl-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 55439:5432 postgres:16-alpine
DATABASE_URL=sqlite+aiosqlite:///:memory: \
TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@127.0.0.1:55439/test \
uv run pytest backend/tests -rs            # 305 passed, nothing skipped or xfailed
docker stop vl-test
docker compose up -d --build backend       # migrate and seed, then the API
curl http://127.0.0.1:8000/health          # {"status":"ok","environment":"development","demo_mode":false,"database":"ok"}
```

The production stack is checked by following [docs/runbooks/deploy.md › Rehearse on your own machine](../runbooks/deploy.md#rehearse-on-your-own-machine), as CI's `rehearsal` job does.

## Sprint decisions

- **Production refuses; it does not warn.** An unsafe secret or password stops the start, so a bad `deploy/.env` fails at `migrate` or at the API's start, where the operator is looking.
- **The new limits live in memory too,** in the same sliding window as the demo's (ADR-0005: one API process). A restart resets them. A second mining request gets a 429 instead of waiting, so the client decides whether to try again.
- **Readiness, not liveness.** Docker's healthcheck and Compose's `service_healthy` now mean the API can serve, so Caddy starts only once the database answers.
- **A request id cannot write into the logs.** A client's id is kept only when it is short and plain; any other value is replaced.
- **Sprint 3's limit behind Caddy is solved.** The API publishes no port, so trusting `X-Forwarded-For` (`FORWARDED_ALLOW_IPS=*`) is safe, and the demo limits see the visitor's address.
- **The rehearsal checks TLS the way a browser does.** It trusts Caddy's local CA through `CURL_CA_BUNDLE` instead of skipping the check with `curl -k`. It pins the webapp's smoke test at a commit, so a change in that repository cannot turn our CI red.
- **Backups are tested for real.** Every pull request wipes a throwaway database and restores it, instead of only checking that a dump file exists.
- **Settings read at import are tested in a subprocess.** The CORS test builds the app with other origins, so hardcoded origins fail it.

## Changes to the specification in this sprint

- **`docs(spec)` commits, one per story or part:**
  - production settings (VLA-21);
  - the seed's credentials from the environment (VLA-24);
  - the Compose file that runs the published image (VLA-38);
  - readiness and request ids (VLA-26);
  - the abuse limits (VLA-29);
  - Caddy in front of the webapp and the API, then the deploy runbook and its rehearsal (VLA-27);
  - backups and secret rotation (VLA-28);
  - the changelog in the tree (VLA-30).
- **ARCHITECTURE_RULES.md:** AR-15 passes, so no rule is pinned any more.
- **BACKLOG.md:**
  - VLA-38 added, and VLA-27 prepared without a server (#45);
  - each story records its own PRs;
  - VLA-31 moved to after 1.0.0;
  - this PR records where VLA-27 will be deployed.
- **Runbooks:** `docs/runbooks/` is new: `deploy.md`, `backup-and-restore.md`, `rotate-secrets.md`.
- **ADRs:** none added.
- **`CHANGELOG.md`:** new, with 1.0.0 and the July baseline as 0.1.0.

## After Sprint 4

- **Deploy.** On the Google Cloud VM with its DuckDNS name, follow `docs/runbooks/deploy.md`, including its notes for a cloud VM. Run `verify.sh` against the public name. That finishes VLA-27, with the webapp's VLW-25, and lets the webapp take its screenshots for VLW-26.
- **VLA-31,** after 1.0.0 and coordinated with the webapp, since amounts would become strings in JSON.
- **121 warnings in the test run, none of them a failure.** PyJWT warns that the development `SECRET_KEY` used in the tests is shorter than 32 bytes, and a synchronous test in `test_cors.py` inherits the module's `asyncio` mark. They are noise that could hide a real warning. A small `chore` PR can remove them, if the product owner wants it.
- **Known limits, written in the SPEC:**
  - the demo, sign-in and transaction counters live in one process and reset on restart;
  - DNS rebinding between a peer URL's check and its connection.

## Retro

- **Went well:** nine PRs in a day, each green on the four required checks. The rehearsal turned the runbook into a test, and the webapp now runs it too, with its own image and its browser flows through our Caddy.
- **To improve:** one CI check passed without checking anything. VLA-38's grep for `source: ./backend` never matched, because `compose config` prints absolute paths. JSON escapes in the tool layer also cost time twice: a literal `\n` in the CI YAML, and a raw `U+2028` in a test.
- **To try:** before trusting a new CI assertion, make it fail once on purpose. Write multi-line files with an editor, never through escaped strings.
