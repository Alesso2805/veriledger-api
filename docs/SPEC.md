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
| Identity | Demo accounts | One click makes a 24-hour `trader` account, with no email or password (ADR-0006) | Built (VLA-35), with its limits |
| Identity | Admin seed | `make seed` creates the admin once | Built (VLA-02); credentials from the environment in VLA-24 |
| Wallets | Key pair | `POST /wallets/generate` returns an Ed25519 pair in hex | Built (VLA-04); development only in VLA-21, the webapp generates keys itself (VLW-16) |
| Wallets | Balance | `GET /wallets/{address}/balance`: confirmed received − (confirmed and pending sent + fees) | Built (VLA-04) |
| Ledger | Signed transactions | The API rebuilds the signed message and verifies the Ed25519 signature; valid ones enter the mempool as `PENDING` | Built (VLA-03); canonical message in VLA-15 |
| Ledger | Replay protection | A per-sender nonce inside the signed message, and a transaction hash over what was signed | Built (VLA-16) |
| Ledger | Notarization | Amount 0 with a `payload` (the document's hash) that is part of the signed message | Built (VLA-08) |
| Mining | Proof of Work | All pending transactions plus a coinbase go into one block; SHA-256 with `MINING_DIFFICULTY` leading hex zeros (4 by default) | Built (VLA-05); the difficulty is a setting since VLA-17 |
| Mining | Reward and fees | Coinbase from `SYSTEM` of `MINING_REWARD` (50 by default) + the block's fees to the miner | Built (VLA-06); the reward is a setting since VLA-17 |
| Mining | Atomic and non-blocking | One DB transaction per block; PoW off the event loop; difficulty and reward in settings | Built (VLA-17): one transaction per request (ADR-0007), 409 for a taken height, the PoW in a worker thread (ADR-0008) |
| Network | Peers | Register, list; new transactions and blocks are broadcast to peers, which take the shared peer token in place of a user | Built (VLA-07); the peer token and safe peer URLs since VLA-19 |
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

**Request flow (mine a block, VLA-17).** Router → `MineBlockUseCase` → the latest block, then the mempool → the coinbase and the block, built in memory → the Proof of Work, in a worker thread (ADR-0008), with nothing written yet → the block (a flush), then the coinbase, already in its block, then the confirmations → the session dependency commits → the response → peers are asked to resolve, as a background task. A failure at any step leaves nothing written. Two requests that mine on the same latest block aim at the same height: the unique `block_number` stops the second at its insert, and it answers 409 with nothing written. Reading the latest block before the mempool keeps a transaction out of two blocks: a block committed between the two reads is missing from the first, so the request aims at that block's height and gets the 409.

**Peer calls.** Use cases call peers through the `PeerClient` port (`domain/ports/services/peer_client.py`), implemented with httpx in `infrastructure/peers/`. They offer new transactions (`POST /transactions`), ask peers to resolve after a new block (`POST /nodes/resolve`), and read a peer's whole chain, page by page, from `GET /blocks/full` to resolve conflicts. A peer's chain is as long as what was fetched, never the `total` it claims, and it is compared with our whole chain, not one page.

**Peer token (VLA-19).** The nodes of one network share `PEER_TOKEN`. Every peer call sends it in `X-Peer-Token`, and `POST /transactions` and `POST /nodes/resolve` accept it in place of a user, compared in constant time; no other route takes it. It names a node, not a person: a transaction a peer offers is checked against its signature, balance and nonce like any other. Unset or empty, the header is ignored and those routes need a user. Every registered peer receives the token, so an admin registers only nodes of the same network.

**Peer URLs (VLA-19).** The `PeerUrlPolicy` port (`ResolvingPeerUrlPolicy` in `infrastructure/peers/`) decides which URLs this node may call. A peer URL is `http` or `https` with a host, and every address its host resolves to is public: loopback, private, link-local, shared (`100.64.0.0/10`), reserved and multicast addresses are refused, and `::ffff:a.b.c.d` counts as `a.b.c.d`. This keeps an admin, or whoever holds an admin's token, from pointing the server at its own network or at a cloud's metadata service. Registration checks it and answers 400 with the reason. Every call checks it again and skips a peer that fails, since a host can change its answer after it was registered. httpx does not follow redirects. A host is resolved once more when httpx connects, so one that changes its answer between the check and the call (DNS rebinding) is not stopped. `ALLOW_PRIVATE_PEERS=true` lifts the address rule, not the scheme rule, for development and private networks; Compose sets it, and `.env.example` leaves it false.

**Adopting a chain.** Each adopted transaction keeps its payload and nonce. A pending transaction that the new chain already holds, or whose nonce it used, leaves the mempool, since it can no longer be mined.

**Processes.** One API process (uvicorn). A `migrate` container runs Alembic once before the API starts (VLA-23). There are no background workers; broadcasts run as FastAPI background tasks in the API process, after the response, so peers only hear of committed data (ADR-0007). The Proof of Work runs in a worker thread of the same process, so the event loop keeps answering while a block is mined (ADR-0008).

## Data model

PostgreSQL 16. One Alembic history in `backend/alembic/versions`. Every table inherits `created_at` and `updated_at` (timestamptz, `now()` by default) from `BaseModel`. Identifiers are UUID v4 strings generated in the application.

| Table | Column | Type | Constraints | Status |
| --- | --- | --- | --- | --- |
| `users` | `id` | varchar | PK | Built |
| | `email` | varchar | Unique index; NULL only for a demo account (VLA-35) | Built |
| | `password_hash` | varchar | bcrypt; NULL only for a demo account (VLA-35) | Built |
| | `role` | enum `userrole` (`ADMIN`, `TRADER`, `VIEWER`) | NOT NULL | Built |
| | `deleted_at` | timestamptz | NULL; queries ignore deleted users | Built |
| | `expires_at` | timestamptz | NULL; set only on a demo account, 24 h after it was created; indexed (VLA-35) | Built |
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
| | `nonce` | bigint | Unique (`sender_address`, `nonce`); NULL only on rows from before VLA-16; a coinbase takes its block number | Built |
| `nodes` | `id` | varchar(36) | PK | Built |
| | `url` | varchar(255) | NOT NULL, unique index | Built |
| | `status` | varchar(20) | NOT NULL, `ACTIVE` | Built |

**Rules.** A confirmed transaction always has a `block_id`; a pending one never does. `downgrade base` leaves no enum types behind (VLA-25). Models and migrations never diverge (AR-06).

## API contract

The generated OpenAPI document is the contract; this table is its summary. `make openapi` writes it to `docs/openapi.json` (`backend/app/openapi_document.py`) with sorted keys and a fixed indent, so the same API always writes the same bytes. A unit test fails when the file is stale, so a route or a response model that changed without it fails CI; another checks that every operation answers a named schema and that the enums are named (VLA-37). The webapp generates its types from this file, pinned to a commit.

| Method | Path | Auth | Role (target, VLA-19) | Purpose |
| --- | --- | --- | --- | --- |
| GET | `/health` | Public | — | Liveness, and `demo_mode`: whether `POST /auth/demo` exists (VLA-35); database readiness in VLA-26 |
| POST | `/auth/login` | Public | — | OAuth2 password form → `{access_token, token_type}` |
| POST | `/auth/demo` | Public, only with `DEMO_MODE` | — | Creates a 24-hour `trader` account named `Guest XXXX` and returns its token, 201 (› Demo accounts); 404 without `DEMO_MODE`; 429 past › Demo limits |
| GET | `/auth/me` | JWT | Any | The current user: `email` (null for a demo account), `display_name` (the email, or `Guest XXXX`), `role`, `expires_at` (set only for a demo account) |
| POST | `/users` | JWT | admin | Create a user |
| POST | `/wallets/generate` | Public | — | Development only (VLA-21) |
| GET | `/wallets/{address}/balance` | Public | — | `{address, balance}` |
| GET | `/wallets/{address}/nonce` | Public | — | The sender's next nonce: one more than the last accepted, 1 for a new address |
| POST | `/transactions` | JWT or peer token | Any | Submit a signed transfer or notarization (201); `amount` and `fee` are the signed 8-decimal strings. A byte-identical replay answers 200 with the stored transaction; another body with a used or skipped `nonce` answers 409 |
| GET | `/transactions/{tx_hash}` | Public | — | Lookup by hash (404 if unknown), with `block_number` and `block_hash` (null while pending) |
| GET | `/transactions?status=PENDING` | Public | — | What waits for the next block, newest first (`skip`, `limit` up to 100); only `PENDING` for now |
| GET | `/wallets/{address}/transactions` | Public | — | What an address sent or received, newest first (`skip`, `limit` up to 100), each with its status, `tx_hash` and block |
| GET | `/blocks` | Public | — | Paginated blocks, newest first (`skip`, `limit` up to 100), each with its `transaction_hashes` |
| GET | `/blocks/full` | Public | — | Blocks with their transactions, payloads included, for peers (`skip`, `limit` up to 100) |
| GET | `/blocks/{block_hash}` | Public | — | One block with its transactions (404 if unknown) |
| POST | `/blocks/mine` | JWT | trader, admin | Mine the mempool into a block; 409 if another request mined that height first (› Request flow (mine a block)); 429 for a demo account past its hourly limit (› Demo limits) |
| POST | `/nodes/register` | JWT | admin | Add a peer URL (201; 400 if duplicate, or if › Peer URLs refuses it, with the reason) |
| GET | `/nodes` | Public | — | List peers |
| POST | `/nodes/resolve` | JWT or peer token | admin | Adopt the longest valid chain among peers |

**Public reads (ADR-0006, VLA-36).** Blocks, transactions and peers are read without a token; every write needs one, with the role of › Permissions by role. A public page holds at most 100 items.

**Demo accounts (VLA-35, ADR-0006).** With `DEMO_MODE=true`, `POST /auth/demo` creates a `trader` with no email or password, named `Guest XXXX` after the last four hex digits of its id, which expires 24 hours later. Its JWT carries `sub`, `role`, `exp` at the account's `expires_at`, and `demo: true`, so the webapp can tell an ended demo from an expired session even after a reload; a normal account's token has no `demo` claim. After `expires_at`, every request with the token answers 401 `Could not validate credentials`, like any expired token, and the account's own date is checked as well as the token's. A demo account cannot sign in with `/auth/login`. `make purge-demo-accounts` (`backend/app/cli/purge_demo_accounts.py`), run on a schedule in a demo deployment, deletes the expired accounts; blocks and transactions refer to addresses, not to users, so what a demo recorded stays on the chain.

**Demo limits (VLA-35, ADR-0006).** Each answers 429 with `Retry-After` in seconds, and 0 turns it off, as the webapp's end-to-end CI does:

| Setting | Default | Counts | `detail` |
| --- | --- | --- | --- |
| `DEMO_ACCOUNTS_PER_IP_PER_HOUR` | 5 | Demo accounts made from one client address in the last hour | `Too many demo accounts from your network in the last hour; try again later` |
| `DEMO_MAX_ACTIVE_ACCOUNTS` | 500 | Demo accounts not yet expired; `Retry-After` is when the oldest expires | `The demo is full right now; try again later` |
| `DEMO_MINES_PER_HOUR` | 10 | A demo account's mining requests in the last hour; normal accounts have no limit | `A demo account can mine N blocks per hour; try again later`, with N the setting |

The active count is read from the database. The other two are counted by a sliding window in the API process's memory (`infrastructure/limits/`), which suffices with one API process (ADR-0005) and starts again after a restart. Behind Caddy, the client address is the visitor's only when uvicorn runs with `--proxy-headers` and trusts Caddy's address (VLA-27).

**Errors.** Validation and business errors answer 400 with `{"detail": "<message>"}`; missing or invalid tokens 401; a role without permission 403; unknown resources 404; conflicts (duplicate nonce, concurrent mining) 409 from VLA-16 and VLA-17.

**Pagination.** `total` is the number of rows that match, not the page size.

## Signing and hashing contract

**Keys.** Ed25519 raw keys in lowercase hex: 32-byte public key (the address), 32-byte private key, 64-byte signature (ADR-0003).

**Signed message (ADR-0004; VLA-15, VLA-16).** `build_signed_message` in `backend/app/domain/signed_message.py`: UTF-8 JSON with keys sorted, no whitespace, `payload` omitted when absent:

```json
{"amount":"10.00000000","fee":"0.10000000","nonce":1,"payload":"<hex>","receiver_address":"<hex>","sender_address":"<hex>"}
```

- `amount` and `fee` are strings with exactly 8 decimals and no leading zeros; the body of `POST /transactions` carries those same strings, and a number answers 422.
- `nonce` is an integer from 1 to 2^53 − 1, one more than the sender's last accepted nonce (`GET /wallets/{address}/nonce`). A reused or skipped nonce answers 409; two requests racing for one nonce meet the unique (`sender_address`, `nonce`) constraint, which also answers 409.
- `docs/signing-vectors.json` (version 2) pins the format; its signatures come from `@noble/curves`, the webapp's library, and both repositories' tests verify every vector.

**Transaction hash (VLA-16).** SHA-256 of compact sorted-key JSON over the signed fields (`amount` and `fee` as 8-decimal strings, `nonce`, `payload` when present, `receiver_address`, `sender_address`) plus `signature`, with no id or arrival time. The same signed body is the same transaction, and two signatures are two transactions. A coinbase, which signs nothing, takes its block number as nonce, so its hash stays unique. Rows from before VLA-16 keep the hashes they were stored with.

**Block hash and Proof of Work.** SHA-256 of sorted-key JSON over `id`, `block_number`, `previous_hash`, `timestamp`, `nonce` and the sorted `transaction_ids`. A block is valid when its hash starts with `MINING_DIFFICULTY` hex zeros (4 by default, from 1 to 64). The coinbase pays `MINING_REWARD` (50 by default, not negative) plus the block's fees. The nodes of one network need the same two values, since a peer's blocks are checked against ours (VLA-18).

**Valid chain (target, VLA-18).** Starts at a genesis block with `previous_hash` of 64 zeros; each block's hash recomputes and meets the difficulty; each `previous_hash` equals the previous block's hash; block numbers are consecutive; exactly one coinbase per block of `MINING_REWARD` + its fees; every other transaction has a valid signature, an unused nonce and a covered balance at that point of the chain.

## Non-functional requirements and security

| Category | Requirement | How it is verified |
| --- | --- | --- |
| Integrity | No transaction enters the mempool without a valid signature over the canonical message | Golden vectors and invalid-signature tests (VLA-15) |
| Integrity | A captured request cannot be replayed | Replay test with the same body twice → 409 (VLA-16) |
| Integrity | A peer cannot replace the chain with forged or tampered blocks | One test per rule of "Valid chain" (VLA-18) |
| Atomicity | Mining writes coinbase, block and confirmations together or not at all | `test_mining.py`: a confirmation that fails after the block and the coinbase were flushed leaves nothing written (VLA-17) |
| Concurrency | Two simultaneous mine requests never produce a duplicate `block_number` | `test_mining.py`: four simultaneous mines give consecutive blocks or 409, one coinbase each, and the pending transfer in one block; a stale latest block answers 409 (VLA-17) |
| Availability | Mining does not block other requests | `test_mining.py`: with the Proof of Work held, `/health` answers first (VLA-17, ADR-0008) |
| Security | Production refuses a missing, default or short `SECRET_KEY`; debug off by default; CORS origins from configuration | Settings tests (VLA-21) |
| Security | The server never generates or receives private keys in production | `/wallets/generate` answers 404 in production (VLA-21); webapp test (VLW-16) |
| Security | Peer URLs cannot point the server at internal addresses | One test per refused range and a name with one private answer (`test_resolving_peer_url_policy.py`); refused and not stored at the endpoint (`test_peer_urls.py`); skipped before a call (VLA-19) |
| Security | Only a node holding the peer token submits or asks for a resolve without a user, and the token opens no other route | `test_peer_token.py`, AR-08, and two running nodes in `test_two_nodes.py` (VLA-19) |
| Security | Login and transaction submission are rate limited | 429 tests (VLA-29) |
| Security | The public demo cannot be flooded with accounts or mining | `test_demo_limits.py`: each limit's 429 and `Retry-After`, another address not held back, 0 turns a limit off (VLA-35) |
| Reproducibility | The image installs exactly `uv.lock` and the app imports with runtime dependencies only | CI builds the image and imports the app (VLA-11, VLA-22) |
| Deployment | `docker compose up` applies migrations before the API starts | Startup from an empty database in CI (VLA-23) |
| Observability | JSON logs in production with a request id; `/health` reports the database | Log and health tests (VLA-26) |
| Quality | Ruff and Mypy strict without errors; architecture tests green; coverage ≥ 80 % in `domain` and `application` | GitHub Actions (VLA-10, VLA-12, VLA-13) |

**Permissions by role (VLA-19).** Each endpoint declares its required role in the router through `RequireRole`, or `RequireRoleOrPeer` on the two routes a peer calls; this table is its specification.

A demo account (ADR-0006) is a `trader` for 24 hours. Without an account, a visitor can read blocks, transactions and peers. Another node of the network, with the peer token, may submit transactions and ask for a resolve (› Peer calls); it has no role and no other write.

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
│   │   ├── infrastructure/       # database, models, repositories, security, consensus, peers (VLA-19), limits (VLA-35)
│   │   ├── presentation/         # api/ routers, dependencies/
│   │   ├── cli/                  # seed.py (make seed), purge_demo_accounts.py (VLA-35)
│   │   ├── main.py
│   │   └── openapi_document.py   # make openapi (VLA-37)
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
│   ├── openapi.json              # generated by make openapi (VLA-37)
│   ├── adr/
│   ├── runbooks/                 # VLA-28
│   └── sprints/
├── .github/workflows/ci.yml      # lint, format, types, tests on Postgres
├── docker-compose.yml            # with the migrate service (VLA-23)
├── Dockerfile
├── Makefile
├── pyproject.toml
├── uv.lock
├── .python-version               # 3.12.13, read by uv locally and in CI
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
