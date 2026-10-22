# VeriLedger API

**A small, readable verifiable ledger, and the engine behind [VeriLedger](https://github.com/Alesso2805/veriledger-webapp).**

It keeps a chain of Proof-of-Work blocks with two kinds of transactions:

- transfers between Ed25519 addresses, signed in the browser over one canonical message;
- document notarizations (proof of existence), which anchor a document's hash.

Peer nodes converge on the longest valid chain. The private keys never reach the server: the webapp signs in the browser, and the API checks every signature.

## Try it

**Live demo: [veriledger.duckdns.org](https://veriledger.duckdns.org)**

The webapp and this API share one hostname. The API answers under `/api`:

- [`/api/docs`](https://veriledger.duckdns.org/api/docs): the interactive documentation of every endpoint;
- [`/api/health`](https://veriledger.duckdns.org/api/health): whether the API and its database answer.

Blocks, transactions and peers are public reads. **Try the demo**, in the webapp, starts a 24-hour account with one click, which can sign, send and mine.

## Highlights

- **Signed transactions** over a canonical message shared with the webapp, with golden vectors ([docs/signing-vectors.json](docs/signing-vectors.json)). A nonce per sender prevents replays (ADR-0004).
- **Mining** that is atomic, answers 409 when two requests mine the same height, and runs its Proof of Work off the event loop (ADR-0007, ADR-0008).
- **Peers** that call each other with a shared token, only at public addresses, and adopt a chain only once every block and transaction in it is valid.
- **Public reads** of blocks, transactions and peers, and **one-click demo accounts** that last 24 hours (ADR-0006).
- **Production settings:**
  - it refuses unsafe secrets;
  - it limits sign-ins, transactions and mining;
  - it reports its database in `/health`;
  - every log line has a request id.
- **The OpenAPI document** in [docs/openapi.json](docs/openapi.json), from which the webapp generates its types.

## Quality

- **Audited against its own documents.** On 2026-10-20 an audit compared the first version with its specification. It found 9 blocking problems, including these:
  - transactions signed in the webapp were rejected, and the same signed body was accepted five times;
  - JWTs could be forged with a default key;
  - any user could rewrite the chain through a peer;
  - a peer's URL could reach the server's own network;
  - concurrent mining created money.

  Every blocking and important finding became a story, and all of them are done.
- **Architecture rules that fail the build.** The 16 rules of [docs/ARCHITECTURE_RULES.md](docs/ARCHITECTURE_RULES.md) each name the test that checks them:
  - import-linter keeps the domain free of FastAPI and SQLAlchemy;
  - the models and the migrations agree, and the migration history goes down and up cleanly;
  - production refuses unsafe secrets.
- **Tests:** 199 test functions, unit and architecture tests, and integration tests against a real PostgreSQL. Mypy runs in strict mode.
- **CI on every pull request:**
  - lint, format, types and the layer contracts;
  - the tests on PostgreSQL;
  - the image, Compose, and a rehearsal of the deployment behind Caddy over HTTPS.

## Stack

Python 3.12.13, FastAPI, SQLAlchemy 2 (async) with asyncpg, PostgreSQL 16, Pydantic v2, Alembic, uv, structlog; Ruff, Mypy (strict), pytest, import-linter; Docker Compose and Caddy.

## Run it

### With Docker

One command starts PostgreSQL, migrates it, creates the admin, then starts the API with `--reload` on your code:

```bash
docker compose up
```

- The API answers on `http://127.0.0.1:8000` (`API_PORT`), with its docs at `/docs`. PostgreSQL is on `127.0.0.1:5433` (`POSTGRES_HOST_PORT`).
- The admin is `admin@veriledger.com` / `adminpassword123` in development (`ADMIN_EMAIL`, `ADMIN_PASSWORD`).
- `DEMO_MODE`, `MINING_DIFFICULTY`, `PEER_TOKEN`, `CORS_ORIGINS` and the limits come from the shell or from `.env` (see [.env.example](.env.example)).
- `API_IMAGE_TAG=sha-<commit> docker compose -f docker-compose.ghcr.yml up` runs the published image instead of building it, as the webapp's end-to-end CI does.

### Without Docker

Run every command from the repository root.

```bash
uv sync                          # Python 3.12.13 and every dependency, exactly as uv.lock pins them
cp .env.example .env             # DATABASE_URL points at the PostgreSQL of `docker compose up -d postgres`
docker compose up -d postgres
make migrate                     # alembic upgrade head
make seed                        # the admin of ADMIN_EMAIL and ADMIN_PASSWORD, once
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Develop

```bash
make lint                        # Ruff and the layer contracts (import-linter)
uv run ruff format backend       # or `make format`, which also fixes what Ruff can
make typecheck                   # Mypy, strict
make openapi                     # regenerate docs/openapi.json after changing a route or a response model
```

The tests need a throwaway PostgreSQL. Never point them at a database you care about: they drop every table.

```bash
docker run -d --rm --name vl-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 55439:5432 postgres:16-alpine
DATABASE_URL=sqlite+aiosqlite:///:memory: \
TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@127.0.0.1:55439/test \
uv run pytest backend/tests -rs
docker stop vl-test
```

Without `TEST_DATABASE_URL` the integration tests skip and the unit and architecture tests still run. CI runs everything on every pull request: lint, format, types, the layer contracts, the tests on PostgreSQL, the image, Compose, and a rehearsal of the deployment.

A new migration:

```bash
uv run alembic -c backend/alembic.ini revision --autogenerate -m "what changes"
```

AR-06 and AR-07 check that the models and the migrations agree, and that the history goes down and up again cleanly.

## Architecture

One FastAPI service in layers, with the dependencies pointing inward (ADR-0001):

| Layer | Holds |
| --- | --- |
| `domain/` | Entities, ports, the signed message and the chain rules. Standard library only |
| `application/` | One use case per file, and the DTOs |
| `infrastructure/` | The database, repositories, cryptography, Proof of Work, peers and limits |
| `presentation/` | FastAPI routers and dependencies |
| `core/` | Settings and logging |
| `cli/` | The seed, the demo cleanup, and the admin's password |

[docs/ARCHITECTURE_RULES.md](docs/ARCHITECTURE_RULES.md) states each rule, and names the test that checks it.

## Deploy

The image is published to `ghcr.io/alesso2805/veriledger-api` on every push to `main`. One server runs it behind Caddy, with the webapp, on one hostname (ADR-0005):

- [docs/runbooks/deploy.md](docs/runbooks/deploy.md): from an empty server to a verified demo. CI rehearses it on every pull request;
- [docs/runbooks/backup-and-restore.md](docs/runbooks/backup-and-restore.md);
- [docs/runbooks/rotate-secrets.md](docs/runbooks/rotate-secrets.md).

## Documentation

- [docs/SPEC.md](docs/SPEC.md): what the API does, its contract, and how each guarantee is verified.
- [docs/BACKLOG.md](docs/BACKLOG.md): the stories and the sprint plan; [docs/sprints/](docs/sprints/): what each sprint delivered.
- [docs/adr/](docs/adr/): one decision per file.
- [CHANGELOG.md](CHANGELOG.md): what changed in each release.

## About

Built by [Alessandro David](https://github.com/Alesso2805) as a portfolio project: specification, API, web app and deployment, in two-week sprints. The API's stories are `VLA-NN` and the webapp's are `VLW-NN`.

Found a security issue? See [SECURITY.md](SECURITY.md). Licensed under the [MIT License](LICENSE).
