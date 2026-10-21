# VeriLedger API — specification

Oct 20, 2026 · @Alessandro David

This document describes what the API is, what was built between July 28 and 29, 2026, and what it must become to be deployed. Items marked with a story ID (VLA-NN) are not built yet; the story in [BACKLOG.md](BACKLOG.md) is where they get done. The webapp that uses this API has its own specification in the `veriledger-webapp` repository.

## Vision and problem

**The problem.** Showing that a payment happened, or that a document existed at a given moment, usually means trusting whoever keeps the record. A ledger where every entry is signed by its author, chained by hashes and replicated between nodes lets anyone check the record instead of trusting it.

**The proposal.** A small, readable verifiable ledger: signed transfers between Ed25519 addresses, document notarization (proof of existence) by anchoring a hash, Proof-of-Work blocks with a reward for the miner, and peer nodes that converge on the longest valid chain. It is a portfolio project inspired by verifiable finance infrastructure, so clarity of the code and of its guarantees matters more than throughput.

**Goals of the current plan**

- A demo deployed on the internet that anyone can try from the webapp (VLA-27, VLW-25).
- Every guarantee the README claims is backed by a test: signatures verified, no replays, atomic mining, tampered chains rejected.
- The repository is green from a clean clone: lint, types, architecture tests and tests in CI (VLA-10 to VLA-13).

**Success metrics**

| Metric | Target | How it is measured |
| --- | --- | --- |
| A transfer signed by the webapp is accepted | 100 % of the golden vectors | Vectors in `docs/signing-vectors.json` verified by both repositories' tests (VLA-15, VLW-15) |
| Replayed or tampered data accepted | 0 | Replay test (VLA-16) and one tampered-chain test per validation rule (VLA-18) |
| Clean clone to a running API | One command, no manual steps | `docker compose up` in CI answers `/health` (VLA-23) |
| CI on every PR | Ruff, format, Mypy strict, architecture tests, Pytest green before merge | GitHub branch protection (VLA-10) |

## Scope and features

Status: **Built** (exists on `main`, see the audit for its defects), **Planned** (a story in the backlog).

| Area | Feature | Detail | Status |
| --- | --- | --- | --- |
| Identity | Login | `POST /auth/login` with the OAuth2 password form; JWT HS256, 30 min | Built (VLA-02) |
| Identity | Users and roles | Roles `admin`, `trader`, `viewer`; only admin creates users; bcrypt hashes; soft delete column | Built (VLA-02) |
| Identity | Admin seed | `make seed` creates the admin once | Built (VLA-02); credentials from the environment in VLA-24 |
| Wallets | Key pair | `POST /wallets/generate` returns an Ed25519 pair in hex | Built (VLA-04); development only in VLA-21, the webapp generates keys itself (VLW-16) |
| Wallets | Balance | `GET /wallets/{address}/balance`: confirmed received − (confirmed and pending sent + fees) | Built (VLA-04) |
| Ledger | Signed transactions | The API rebuilds the signed message and verifies the Ed25519 signature; valid ones enter the mempool as `PENDING` | Built (VLA-03); canonical message in VLA-15 |
| Ledger | Replay protection | A per-sender nonce inside the signed message | Planned (VLA-16) |
| Ledger | Notarization | Amount 0 with a `payload` (the document's hash) that is part of the signed message | Built (VLA-08) |
| Mining | Proof of Work | All pending transactions plus a coinbase go into one block; SHA-256 with 4 leading hex zeros | Built (VLA-05) |
| Mining | Reward and fees | Coinbase from `SYSTEM` of 50 + the block's fees to the miner | Built (VLA-06) |
| Mining | Atomic and non-blocking | One DB transaction per block; PoW off the event loop; difficulty and reward in settings | Planned (VLA-17) |
| Network | Peers | Register, list; new transactions and blocks are broadcast to peers | Built (VLA-07); broadcast fails between authenticated nodes until VLA-19 |
| Network | Consensus | `POST /nodes/resolve` adopts the longest valid chain among peers | Built (VLA-07) with a structural check only; full validation in VLA-18 |
| Operations | Health | `GET /health` | Built (VLA-01); database check in VLA-26 |
| Operations | Deployment | One server, Docker Compose, Caddy, HTTPS | Planned (VLA-22, VLA-23, VLA-27) |

**Out of scope for this plan:** smart contracts, UTXO model, difficulty adjustment, forks other than "longest valid chain", a public peer discovery protocol, a native token with market value.

## Architecture

One FastAPI process with five layers under `backend/app` (ADR-0001):

| Layer | Holds | May import |
| --- | --- | --- |
| `core` | Settings (`pydantic-settings`), logging (`structlog`) | Standard library and third-party config/logging libraries |
| `domain` | Entities (`dataclasses`), enums, ports (`abc.ABC`) for repositories and services | Standard library and `domain` only |
| `application` | Use cases (one class per file, an `execute` method) and Pydantic DTOs | `domain`, `core`, Pydantic |
| `infrastructure` | SQLAlchemy models and repositories, database session, Ed25519, SHA-256, JWT, bcrypt, PoW | `domain`, `core` |
| `presentation` | FastAPI routers and dependencies (current user, roles); wires infrastructure into use cases | Every layer |

The admin seed lives in `backend/app/cli/seed.py`. Like the routers, it is a composition script that wires infrastructure into a use case, so `infrastructure` never imports `application` (AR-03).

**Request flow (submit a transfer).** Router → `SubmitTransactionUseCase` → rebuild the signed message → `SignatureService.verify_signature` → `HasherService.hash_transaction` → duplicate check by hash → balance check → `TransactionRepository.create` (a flush) → the session dependency commits → the response → the broadcast to peers, as a background task (ADR-0007).

**Peer calls.** Use cases call peers (`/transactions`, `/nodes/resolve`, `/blocks/full`). Today they import `httpx` directly, which breaks the application rule; VLA-19 moves the calls behind a `PeerClient` port in `domain/ports/services` with an httpx implementation in `infrastructure`.

**Processes.** One API process (uvicorn). A `migrate` container runs Alembic once before the API starts (VLA-23). There are no background workers; broadcasts run as FastAPI background tasks in the API process, after the response, so peers only hear of committed data (ADR-0007).

## Data model

PostgreSQL 16. One Alembic history in `backend/alembic/versions`. Every table inherits `created_at` and `updated_at` (timestamptz, `now()` by default) from `BaseModel`. Identifiers are UUID v4 strings generated in the application.

| Table | Column | Type | Constraints | Status |
| --- | --- | --- | --- | --- |
| `users` | `id` | varchar | PK | Built |
| | `email` | varchar | NOT NULL, unique index | Built |
| | `password_hash` | varchar | NOT NULL (bcrypt) | Built |
| | `role` | enum `userrole` (`ADMIN`, `TRADER`, `VIEWER`) | NOT NULL | Built |
| | `deleted_at` | timestamptz | NULL; queries ignore deleted users | Built |
| `blocks` | `id` | varchar | PK | Built |
| | `block_number` | integer | NOT NULL, unique index; 0 is genesis | Built |
| | `previous_hash` | varchar | NOT NULL; 64 zeros for genesis | Built |
| | `timestamp` | timestamptz | NOT NULL | Built |
| | `nonce` | integer | NOT NULL, default 0 | Built |
| | `block_hash` | varchar | NOT NULL, unique index | Built |
| `transactions` | `id` | varchar | PK | Built |
| | `sender_address`, `receiver_address` | varchar | NOT NULL, indexed; `SYSTEM` is the coinbase sender | Built |
| | `amount`, `fee` | numeric(18, 8) | NOT NULL, `fee` default 0; CHECK ≥ 0 | Built without CHECK; CHECK in VLA-25 |
| | `status` | enum `transactionstatus` (`PENDING`, `CONFIRMED`, `FAILED`) | NOT NULL, indexed | Built |
| | `timestamp` | timestamptz | NOT NULL | Built |
| | `signature` | varchar | NOT NULL; `COINBASE` for coinbase transactions | Built |
| | `tx_hash` | varchar | Unique index; NOT NULL once VLA-16 hashes every transaction at creation | Built nullable |
| | `payload` | varchar | NULL; the notarized document hash | Built |
| | `block_id` | varchar | FK → `blocks.id`, NULL while pending | Built |
| | `nonce` | bigint | NOT NULL for non-coinbase; unique (`sender_address`, `nonce`) | Planned (VLA-16) |
| `nodes` | `id` | varchar(36) | PK | Built |
| | `url` | varchar(255) | NOT NULL, unique index | Built |
| | `status` | varchar(20) | NOT NULL, `ACTIVE` | Built |

**Rules.** A confirmed transaction always has a `block_id`; a pending one never does. `downgrade base` leaves no enum types behind (VLA-25). Models and migrations never diverge (AR-06).

## API contract

The generated OpenAPI document is the contract; this table is its summary. It is exported to `docs/openapi.json` and checked in CI from VLA-30.

| Method | Path | Auth | Role (target, VLA-19) | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/health` | Public | — | Liveness; database readiness in VLA-26 |
| POST | `/auth/login` | Public | — | OAuth2 password form → `{access_token, token_type}` |
| POST | `/auth/demo` | Public, only with `DEMO_MODE` | — | Creates a 24-hour `trader` account named `Guest XXXX` and returns its token (ADR-0006). Planned (VLA-35) |
| GET | `/auth/me` | JWT | Any | The current user |
| POST | `/users` | JWT | admin | Create a user |
| POST | `/wallets/generate` | Public | — | Development only (VLA-21) |
| GET | `/wallets/{address}/balance` | Public | — | `{address, balance}` |
| GET | `/wallets/{address}/nonce` | Public | — | The sender's next nonce. Planned (VLA-16) |
| POST | `/transactions` | JWT | Any | Submit a signed transfer or notarization (201) |
| GET | `/transactions/{tx_hash}` | JWT | Any | Lookup by hash (404 if unknown); `block_number` and `block_hash` in the response from VLA-20 |
| GET | `/transactions?status=PENDING` | JWT | Any | What waits for the next block, paginated. Planned (VLA-33) |
| GET | `/wallets/{address}/transactions` | Public | — | An address's activity, paginated. Planned (VLA-34) |
| GET | `/blocks` | JWT | Any | Paginated blocks, newest first (`skip`, `limit`) |
| GET | `/blocks/full` | JWT; peer token in VLA-19 | Any | Blocks with their transactions, for peers |
| GET | `/blocks/{block_hash}` | JWT | Any | Planned (VLA-20) |
| POST | `/blocks/mine` | JWT | trader, admin | Mine the mempool into a block |
| POST | `/nodes/register` | JWT | admin | Add a peer URL (201; 400 if duplicate) |
| GET | `/nodes` | JWT | Any | List peers |
| POST | `/nodes/resolve` | JWT; peer token in VLA-19 | admin | Adopt the longest valid chain among peers |

**Public reads (ADR-0006, VLA-36).** From VLA-36 the reads `GET /blocks…`, `GET /transactions…` and `GET /nodes` need no token; the table shows the state before that story. Writes always need one.

**Errors.** Validation and business errors answer 400 with `{"detail": "<message>"}`; missing or invalid tokens 401; a role without permission 403; unknown resources 404; conflicts (duplicate nonce, concurrent mining) 409 from VLA-16 and VLA-17.

**Pagination.** `total` is the number of rows that match, not the page size (VLA-20).

## Signing and hashing contract

**Keys.** Ed25519 raw keys in lowercase hex: 32-byte public key (the address), 32-byte private key, 64-byte signature (ADR-0003).

**Signed message, as built.** `json.dumps({"amount", "fee", "receiver_address", "sender_address"[, "payload"]}, sort_keys=True)` with Python's default separators (`", "` and `": "`) and amounts as Python floats (`10.0`). The webapp signs `JSON.stringify` of the same keys, which has no spaces and writes `10` for `10.0`, so the API rejects every transaction the webapp signs (audit, 2026-10-20).

**Signed message, target (ADR-0004, VLA-15 and VLA-16).** UTF-8 JSON with keys sorted, no whitespace, amounts and fees as decimal strings with exactly 8 decimals, and a `nonce`:

```json
{"amount":"10.00000000","fee":"0.10000000","nonce":1,"payload":"<hex>","receiver_address":"<hex>","sender_address":"<hex>"}
```

`payload` is omitted when absent. Golden vectors (key, message, signature) live in `docs/signing-vectors.json` and both repositories' tests verify them.

**Transaction hash.** SHA-256 of sorted-key JSON over `id`, `sender_address`, `receiver_address`, `amount`, `timestamp` and `payload`. VLA-16 makes it cover every signed field plus `fee`, `nonce` and `signature`.

**Block hash and Proof of Work.** SHA-256 of sorted-key JSON over `id`, `block_number`, `previous_hash`, `timestamp`, `nonce` and the sorted `transaction_ids`. A block is valid when its hash starts with `difficulty` hex zeros (4 today; a setting from VLA-17).

**Valid chain (target, VLA-18).** Starts at a genesis block with `previous_hash` of 64 zeros; each block's hash recomputes and meets the difficulty; each `previous_hash` equals the previous block's hash; block numbers are consecutive; exactly one coinbase per block of 50 + its fees; every other transaction has a valid signature, an unused nonce and a covered balance at that point of the chain.

## Non-functional requirements and security

| Category | Requirement | How it is verified |
| --- | --- | --- |
| Integrity | No transaction enters the mempool without a valid signature over the canonical message | Golden vectors and invalid-signature tests (VLA-15) |
| Integrity | A captured request cannot be replayed | Replay test with the same body twice → 409 (VLA-16) |
| Integrity | A peer cannot replace the chain with forged or tampered blocks | One test per rule of "Valid chain" (VLA-18) |
| Atomicity | Mining writes coinbase, block and confirmations together or not at all | Test that fails mid-mining and finds nothing written (VLA-17) |
| Concurrency | Two simultaneous mine requests never produce a duplicate `block_number` | Concurrent integration test (VLA-17) |
| Availability | Mining does not block other requests | `/health` answers while a block is mined (VLA-17) |
| Security | Production refuses a missing, default or short `SECRET_KEY`; debug off by default; CORS origins from configuration | Settings tests (VLA-21) |
| Security | The server never generates or receives private keys in production | `/wallets/generate` answers 404 in production (VLA-21); webapp test (VLW-16) |
| Security | Peer URLs cannot point the server at internal addresses | SSRF tests with loopback and private ranges (VLA-19) |
| Security | Login and transaction submission are rate limited | 429 tests (VLA-29) |
| Reproducibility | The image installs exactly `uv.lock` and the app imports with runtime dependencies only | CI builds the image and imports the app (VLA-11, VLA-22) |
| Deployment | `docker compose up` applies migrations before the API starts | Startup from an empty database in CI (VLA-23) |
| Observability | JSON logs in production with a request id; `/health` reports the database | Log and health tests (VLA-26) |
| Quality | Ruff and Mypy strict without errors; architecture tests green; coverage ≥ 80 % in `domain` and `application` | GitHub Actions (VLA-10, VLA-12, VLA-13) |

**Permissions by role (target, VLA-19).** Each endpoint declares its required role in the router through `RequireRole`; this table is its specification.

A demo account (ADR-0006) is a `trader` for 24 hours. Without an account, a visitor can read blocks, transactions and peers once VLA-36 lands.

| Permission | viewer | trader | admin |
| --- | :-: | :-: | :-: |
| Read blocks, transactions, peers and own profile | ✔ | ✔ | ✔ |
| Submit signed transactions | ✔ | ✔ | ✔ |
| Mine blocks | | ✔ | ✔ |
| Register peers and resolve conflicts | | | ✔ |
| Create users | | | ✔ |

## Engineering rules

**Stack.** Python 3.12, FastAPI, SQLAlchemy 2 async with asyncpg, Pydantic v2, pydantic-settings, Alembic, uv, Ruff, Mypy strict, Pytest with pytest-asyncio, structlog, PyJWT, bcrypt, `cryptography`, httpx. PostgreSQL 16; SQLite only in unit tests (ADR-0002). Docker Compose; Caddy on the server (ADR-0005).

**Architecture rules.** The layer rules of the Architecture section, written as verifiable rules AR-01 to AR-15 in [ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md), each with the test that checks it (VLA-13).

**How we work**

- **A plan first.** Each story starts from a short plan, what will change and which files, agreed with the product owner before any code.
- **Raise contradictions.** If a request contradicts this specification, the contradiction is raised before the work starts. A change to this document goes in its own `docs(spec)` commit.
- **Small commits.** Conventional Commits, one PR per story; work over about 300 lines is split.
- **Explain decisions.** Non-obvious decisions are explained where they are made: a comment that says why, the PR, or an ADR.
- **Cross-repository contracts.** A change to the signed message or an endpoint the webapp uses is decided in an ADR here and lands together with its VLW story.

**Definition of done**

- The acceptance criteria are met and demonstrable.
- Unit tests for the use cases, and at least one integration test per new or changed endpoint, against a real Postgres.
- Green checks: Ruff, Ruff format, Mypy strict, the architecture tests, Pytest.
- `docker compose up` from a clean clone brings the API up with no manual steps.
- The OpenAPI document and this specification are updated when a contract changes.
- If a story changes the architecture, docs/ARCHITECTURE_RULES.md, its tests and the corresponding ADR are updated in the same PR.

## Repository, conventions and living documentation

Target tree. Entries marked with a story do not exist yet.

```text
veriledger-api/
├── backend/
│   ├── app/
│   │   ├── core/                 # settings, logging
│   │   ├── domain/
│   │   │   ├── entities/         # Block, Transaction, User, Node
│   │   │   └── ports/            # repositories/ and services/ (ABCs)
│   │   ├── application/
│   │   │   ├── dto/
│   │   │   └── use_cases/        # auth, ledger, network, wallet
│   │   ├── infrastructure/       # database, models, repositories, security, consensus, peers (VLA-19)
│   │   ├── presentation/         # api/ routers, dependencies/
│   │   ├── cli/seed.py           # make seed
│   │   └── main.py
│   ├── alembic/                  # env.py and versions/
│   ├── alembic.ini
│   └── tests/
│       ├── unit/
│       ├── integration/          # real Postgres (VLA-25)
│       └── architecture/         # AR-NN tests (VLA-13)
├── deploy/                       # docker-compose.prod.yml, Caddyfile (VLA-23, VLA-27)
├── docs/
│   ├── SPEC.md                   # this document
│   ├── BACKLOG.md                # stories and sprint plan
│   ├── ARCHITECTURE_RULES.md
│   ├── AUDIT.md
│   ├── signing-vectors.json      # VLA-15
│   ├── openapi.json              # generated (VLA-30)
│   ├── adr/
│   ├── runbooks/                 # VLA-28
│   └── sprints/
├── .github/workflows/ci.yml      # lint, format, types, tests on Postgres
├── docker-compose.yml            # with the migrate service (VLA-23)
├── Dockerfile
├── Makefile
├── pyproject.toml
├── uv.lock
├── .python-version               # 3.12, read by uv
├── .pre-commit-config.yaml       # Ruff hooks, same version as uv.lock
├── CLAUDE.md
├── CHANGELOG.md                  # VLA-30
└── README.md
```

| Artifact | Purpose | When it is updated |
| --- | --- | --- |
| `docs/SPEC.md` | Vision, scope, architecture, data, contracts | When the scope or a contract changes |
| `docs/BACKLOG.md` | Stories, acceptance criteria, sprint plan | At planning and when a story is added or moved |
| `docs/ARCHITECTURE_RULES.md` | Verifiable architecture rules and their tests | When a story changes the architecture |
| `docs/adr/NNNN-*.md` | One technical decision: context, options, decision, consequences | Every non-trivial decision |
| `docs/sprints/sprint-N.md` | What was delivered, decisions, spec changes, retro | At the close of each sprint |
| `docs/AUDIT.md` | Independent comparison of the repository against these documents | Before a release, or when asked |
| `CHANGELOG.md` | Visible changes per version (Keep a Changelog + SemVer) | Every release |

**Conventions.** Branches `feat/VLA-NN-description`, `fix/…`, `chore/…`; Conventional Commits; PRs reference the story and include the DoD checklist; tables and columns in English `snake_case`; code, comments and documentation in English.
