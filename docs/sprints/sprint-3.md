# Sprint 3 — Forged chains rejected, a reproducible image, one-command start, endpoints tested on Postgres, and the one-click demo (VLA-18, VLA-22, VLA-23, VLA-25, VLA-35, VLA-37)

**Status as of 2026-10-21:** closed on October 21, 2026, ahead of the planned November 23 – December 6. All 6 stories are done, 25 points.

The webapp's counterpart, VLW-19, VLW-29, VLW-31, VLW-32 and VLW-34, was built on these endpoints and on the OpenAPI document. Its session reported each part merged or set to auto-merge as the API's counterpart landed.

**Order:** VLA-35, VLA-37, VLA-22, VLA-23, VLA-25, VLA-18. This is the order the product owner approved on 2026-10-21, after the API and webapp sessions agreed on it (#32).

**Decisions it waited for, all taken by the product owner on 2026-10-21**

- `docs/openapi.json` was brought forward from VLA-30 as VLA-37, so the webapp's generated types (VLW-19b) would not wait for Sprint 4.
- VLA-35's contract gained the JWT claim `demo: true` and `/health`'s `demo_mode`, both requested by the webapp.
- VLA-22 also publishes the image to GHCR, for the webapp's end-to-end CI.
- Python is pinned to one patch release, 3.12.13, in CI and locally (#33). This came from Sprint 2's retro.

## What was delivered

`main` is at `8532b71`, CI green (`checks`, `image`, `compose`). Every PR below was merged with a merge commit after its CI run passed.

| Story | PRs | Result | Verification |
| --- | --- | --- | --- |
| VLA-35 | #34, #35, #37 | With `DEMO_MODE`, `POST /auth/demo` makes a 24-hour trader `Guest XXXX` with no email or password. Its JWT ends with the account and says `demo: true`. An expired account answers 401. `/auth/me` returns `display_name` and `expires_at`, and `/health` returns `demo_mode`. `make purge-demo-accounts` deletes expired accounts and keeps their chain data. Three limits answer 429 with `Retry-After`, are configurable through the environment, and are turned off by 0: accounts per address, active accounts, mines per demo account. #37 fixed "1 blocks" | `test_demo.py`, `test_demo_limits.py`, `test_sliding_window.py`; the webapp's session checked the three 429s live |
| VLA-37 | #36 | `make openapi` writes `docs/openapi.json` deterministically. A test fails when the file is stale; another checks that every operation answers a named schema and that the enums are named | `test_openapi_document.py`; CI regenerates the file on Linux and it matches the one written on Windows |
| VLA-22 | #38 | A two-stage image: `uv sync --frozen --no-dev` on the base image's Python 3.12.13; a final stage with no uv, tests or `.env`; uid 10001, no `--reload`, a `HEALTHCHECK`, bases pinned by digest. 320 MB. Published for amd64 and arm64 to `ghcr.io/alesso2805/veriledger-api` (`main`, `sha-<commit>`), public | CI's `image` job: build, import, uid, healthcheck. The first publication was checked, including an anonymous pull |
| VLA-23 | #39 | `docker compose up`: PostgreSQL 16, then `migrate`, then the API only if `migrate` succeeded. Port, demo and mining settings come from the environment. `deploy/docker-compose.prod.yml` runs the published image with secrets from `deploy/.env`, no bind mounts, no published database port, and the API on loopback | CI's `compose` job; both files run locally, the production one with `sha-c17791f` |
| VLA-25 | #40, #41 | CHECKs `amount ≥ 0` and `fee ≥ 0`. The ledger migration's downgrade drops its enum, so AR-07 passes and loses its `xfail`. Every status code the SPEC documents is produced by a test: a recorder in the test client found four that were missing, and a guard keeps the list complete | `test_migrations.py`, `test_transaction_constraints.py`, `test_documented_status_codes.py` |
| VLA-18 | #42, #43 | `ChainValidator` checks every rule of SPEC › Valid chain and returns the first one broken. The blocks: genesis, consecutive numbers, links, hashes that recompute, difficulty. The transactions: hashes, one coinbase of the reward plus fees, signatures, nonces, balances. Resolve adopts only a valid chain and logs why it refused the others | `test_chain_validator.py`, 26 tampered cases; `test_two_nodes.py` validates real chains that crossed HTTP |

**How to check the whole sprint from a clean clone**

```bash
git clone https://github.com/Alesso2805/veriledger-api.git && cd veriledger-api
uv sync                                   # Python 3.12.13, runtime and dev dependencies from uv.lock
make lint && uv run ruff format --check backend && make typecheck
docker run -d --rm --name vl-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 55439:5432 postgres:16-alpine
DATABASE_URL=sqlite+aiosqlite:///:memory: \
TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@127.0.0.1:55439/test \
uv run pytest backend/tests -rs            # 265 passed, 3 xfailed
docker stop vl-test
docker compose up -d --build backend       # migrate, then the API
curl http://127.0.0.1:8000/health          # {"status":"ok","environment":"development","demo_mode":false}
```

## Sprint decisions

- **Contracts first.** Before each PR that changed what the webapp reads, its session got the contract with the exact strings and agreed to it: VLA-35's two parts, VLA-37, VLA-22's image and VLA-23's variables. Nothing on the webapp broke when the API merged first.
- **The demo's counters live in memory.** The active count is read from the database; the per-address and per-account counters are a sliding window in the API process. That suffices with one process (ADR-0005), and a restart resets them. Behind Caddy, the client address needs uvicorn's `--proxy-headers` (VLA-27).
- **The OpenAPI exporter sits next to `main.py`.** AR-05 forbids `cli` from importing `presentation`, even indirectly.
- **The image keeps neither uv nor its cache.** A build stage makes the virtual environment and the final stage copies it: 520 MB went down to 320 MB.
- **Postgres 16 on a new volume name.** 16 cannot open 15's files, so a developer with old data starts empty instead of with a container that fails.
- **What the database refuses, the models refuse too.** The integration tests build their schema with `create_all`, and Alembic does not compare CHECKs, so the constraints live in both places and are tested in both.
- **A valid chain is what this network mines.** The balance rule is the submit check's own (confirmed credits, pending debits), so a node never refuses a chain its peers legitimately mine. Amounts are exact `Decimal`s, spelled `f"{x:.8f}"`, since `str(Decimal)` writes a zero fee as `0E-8`.

## Changes to the specification in this sprint

- **`docs(spec)` commits, one per story or part:**
  - demo accounts and their limits (VLA-35, with #37's singular);
  - the OpenAPI document and the tree (VLA-37);
  - the production image (VLA-22);
  - one command that migrates and starts, and the production Compose file (VLA-23);
  - the CHECKs, and every documented status code having a test (VLA-25);
  - the rules of a valid chain (VLA-18);
  - `.python-version` pinning 3.12.13 (#33).
- **ARCHITECTURE_RULES.md:** AR-07 passes and is no longer pinned. Only AR-15 remains pinned, for VLA-21.
- **BACKLOG.md:** the Sprint 3 plan (#32): VLA-37 added, VLA-22 and VLA-35 widened, the order inside Sprints 3 and 4. Each story now records its own PR numbers in the PR that closes it, as Sprint 2's retro proposed.
- **ADRs:** none added.

## Carried into Sprint 4

- **Sprint 4's plan:** VLA-21, VLA-24, VLA-26 to VLA-30, and VLA-31 if there is room.
- **Order:** VLA-21 (`CORS_ORIGINS`, production refusing unsafe settings; AR-15) and VLA-24 (seeded users from the environment) first, because the webapp's end-to-end tests, VLW-23, run against them.
- **Asked by the webapp for Sprint 4 planning:** a Compose override that runs the published image, so its CI needs no API build. The product owner decides.
- **Open:** whether the `image` and `compose` jobs become required checks on `main`; today only `checks` is.
- **Known limits, written in the SPEC:**
  - DNS rebinding between a peer URL's check and its connection;
  - the demo counters resetting on restart;
  - `--proxy-headers` needed behind Caddy (VLA-27).

## Retro

- **Went well:** two sessions moved together without breaking each other. Every contract went to the webapp before its PR, and its live checks caught what tests at the default values could not ("1 blocks"). The tests that run the real thing proved the hard parts: two nodes recompute each other's hashes and verify each other's signatures over HTTP.
- **To improve:** a configurable text was tested only at its default value. A shell detail cost time twice: `localhost` on Windows trying `::1` first, and PowerShell 5.1 splitting a quoted PR title.
- **To try:** test agreed texts at the edges of configurable values (0, 1, the default). In commands and URLs, write `127.0.0.1`, and keep PR titles free of nested quotes.
