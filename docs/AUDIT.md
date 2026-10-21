# VeriLedger API architecture audit

Date: 2026-10-20 · Commit audited: `c1f113a` (branch `main`, clean working tree at the start). Compared against `docs/SPEC.md`, `docs/BACKLOG.md`, `CLAUDE.md`, `docs/ARCHITECTURE_RULES.md` and `docs/adr/`, written the same day from the code and the README.

## How this audit was done, and its limits

- **What I executed myself:** `ruff check`, `ruff format --check`, `mypy backend/app backend/tests` and `pytest backend/tests` (with `DATABASE_URL=sqlite+aiosqlite:///:memory:`, as the README does) on the working copy. On a fresh `git clone` in a scratch folder: `uv sync`, importing `backend.app.main`, `docker build` of the `Dockerfile` and importing the app inside that image, and `alembic upgrade head` on SQLite. On a throwaway PostgreSQL 16 container: `alembic upgrade head`, `alembic check` and `alembic downgrade base`, then a query for leftover types.
- **Cross-repository check:** a transfer signed exactly as `veriledger-webapp/src/pages/Transaction.tsx` does (`@noble/curves`, `JSON.stringify` of sorted keys), verified with this repository's `Ed25519ServiceImpl` and the message `SubmitTransactionUseCase` builds.
- **Replay check:** a script that calls `SubmitTransactionUseCase` with the real hasher, the real signature service and SQLite, submitting the same signed body six times to a sender with a balance of 50.
- **Second pass, same day (live).** Once the ports were free: `docker compose up -d --build` from the fresh clone. Since its API container cannot import the app, I then ran the API from the working copy's virtualenv (same commit, with the dev extra installed) against that Compose Postgres: `alembic upgrade head` and `make seed`'s module twice on two databases, two nodes (A on :8000, B on :8001), and a script that exercised the findings over HTTP (`verify_api.py`, kept outside the repository). It covered roles, replay, peer URLs, pagination, payloads, the lookup by id, resolve and gossip between the two nodes, three concurrent mines, and a fake peer on :8009. Rows checked this way say "en vivo". The webapp was also driven in Chrome against node A; see the webapp's audit.
- **What I did not execute:** any load, and a deployment.
- **Architecture tests:** they do not exist yet (VLA-13 waits for the tool proposed in ARCHITECTURE_RULES.md). Section 2 gives, for each rule, the evidence of a grep, a read or a command, and says which.

Status vocabulary: **Cumple** (meets), **Parcial** (partly), **No cumple** (does not), **No verificable / no verificado** (could not be confirmed by reading code or running something).

---

## 1. Repository structure

SPEC tree (`docs/SPEC.md` › Repository) against the real tree. The SPEC tree is the target: entries marked with a story are expected to be missing.

**Present as promised:** the five layers under `backend/app` (`core`, `domain`, `application`, `infrastructure`, `presentation`), `backend/alembic/`, `backend/alembic.ini`, `backend/tests/{unit,integration}`, `docs/` with SPEC, BACKLOG, ARCHITECTURE_RULES, adr and sprints, `docker-compose.yml`, `Dockerfile`, `Makefile`, `pyproject.toml`, `uv.lock`, `CLAUDE.md`, `README.md`.

**Missing**

| Item | Story | Note |
| --- | --- | --- |
| `.github/workflows/ci.yml` | VLA-10 | No CI has ever run on this repository. |
| `backend/tests/architecture/` | VLA-13 | — |
| `backend/app/cli/seed.py` | VLA-13 | The seed is in `infrastructure/` (see "elsewhere"). |
| `backend/app/infrastructure/peers` (`PeerClient`) | VLA-19 | Peer calls are inside use cases. |
| `deploy/` (prod overlay, Caddyfile) | VLA-23, VLA-27 | — |
| `docs/signing-vectors.json` | VLA-15 | — |
| `docs/openapi.json`, `CHANGELOG.md` | VLA-30 | — |
| `docs/runbooks/` | VLA-28 | — |
| `.python-version` | VLA-11 | Nothing pins the interpreter; the local virtualenv runs Python 3.14 while the Dockerfile uses 3.12. |

**Extra**

| Item | Note |
| --- | --- |
| `Pipfile` | Empty, declares Python 3.11; the project uses uv. VLA-11 removes it. |
| `backend/tests/e2e/` | Only an empty `__init__.py`. |
| `.pre-commit-config.yaml` | Useful, but not in the SPEC tree, and pins Ruff `v0.5.6` while `uv.lock` has `0.16.0`: the hook and CI would disagree. Keep it, add it to the tree, align the version (VLA-11). |

**Elsewhere**

| Item | Where it is | Where SPEC puts it |
| --- | --- | --- |
| Admin seed | `backend/app/infrastructure/seed.py` | `backend/app/cli/seed.py` (VLA-13) |
| Tests | `backend/tests/` | Same; but the README's test command points at `tests/unit/...` from the repository root, which does not exist. |

Section 1: 12 items present · 9 missing (all with a story) · 3 extra · 2 elsewhere.

---

## 2. Architecture rules

### 2.1 Architecture tests: result

**No architecture test exists, so none could be run.** The table below gives the evidence by other means; "lectura" means read in the code, "grep" a search, "ejecutado" a command I ran.

| Rule | Status | Evidence |
| --- | --- | --- |
| AR-01 domain imports only the standard library | Cumple | grep: the only imports under `domain/` are `abc`, `dataclasses`, `datetime`, `enum`, `typing` and `backend.app.domain.*`. |
| AR-02 application imports only stdlib, pydantic, domain, core | No cumple | grep: `import httpx` in `application/use_cases/ledger/mine_block.py:2`, `ledger/submit_transaction.py:2`, `network/resolve_conflicts.py:1`. |
| AR-03 infrastructure does not import application or presentation | No cumple | grep: `infrastructure/seed.py:5-6` imports `UserCreateDTO` and `RegisterUserUseCase`. |
| AR-04 core imports no other layer | Cumple | grep: `core/` imports `pydantic_settings`, `logging`, `structlog`, `sys`. |
| AR-05 only `main` imports presentation | Cumple | grep: the only import of `backend.app.presentation` outside it is `main.py:10`. |
| AR-06 models and migrations agree | Cumple | ejecutado: `alembic check` on PostgreSQL 16 after `upgrade head` → "No new upgrade operations detected". |
| AR-07 migrations are reversible | No cumple | ejecutado: after `downgrade base`, `pg_type` still has the enum `transactionstatus`, and the next `upgrade head` fails with `DuplicateObjectError: type "transactionstatus" already exists`. |
| AR-08 every non-public route requires a JWT | Cumple | lectura: every route outside `/health`, `/auth/login` and `/wallets/*` depends on `get_current_user`, directly or through `RequireRole` (`presentation/dependencies/auth.py:48`). |
| AR-09 roles per SPEC › Permissions | No cumple | en vivo: a `viewer` registered `http://10.0.0.1` and `http://127.0.0.2:9` (201), called resolve (200) and mined (200). Code: `block_router.py:100-104`, `node_router.py:16-20`, `node_router.py:40-43`. |
| AR-10 every route declares a Pydantic response model | No cumple | lectura: `POST /nodes/resolve` has none (`node_router.py:40`); `GET /wallets/{address}/balance` returns a bare `dict` (`wallet_router.py:27-31`). |
| AR-11 every port has an implementation, `<Port>Impl` naming | Cumple | lectura: 4 repository ports with `…RepositoryImpl` in `…_repository_impl.py`; 6 service ports implemented by `SHA256HasherImpl`, `Ed25519ServiceImpl` (two ports), `ProofOfWorkServiceImpl`, `PasswordHasherImpl`, `JWTTokenService`. |
| AR-12 one use case per file with `execute` and a test file | Cumple | lectura: 9 use cases, 9 matching test files. |
| AR-13 snake_case names and timestamps on every table | Cumple | lectura: `users`, `blocks`, `transactions`, `nodes` inherit `created_at` and `updated_at` from `BaseModel`. |
| AR-14 one canonical signed message that matches the vectors | No cumple | ejecutado: the webapp's signature over `{"amount":10,...}` fails against the API's `{"amount": 10.0, ...}` (`False`) and passes against the compact string (`True`). There are no vectors. |
| AR-15 production refuses default secrets | No cumple | lectura: `core/config.py:9` defaults `secret_key` to `"supersecretkey"`; `docker-compose.yml` does not set `SECRET_KEY`, so the container signs tokens with that value. |

### 2.2 Rules from CLAUDE.md

| Rule | Status | Evidence |
| --- | --- | --- |
| Python 3.12 | Parcial | `pyproject.toml:6` `>=3.12` and `Dockerfile:1` `python:3.12-slim`; the README says "Python 3.14+", `Pipfile` says 3.11, and the local `.venv` runs 3.14. |
| PostgreSQL wherever the app runs; SQLite only for unit tests | Parcial | Compose and `.env.example` use PostgreSQL; the README says the project "is currently configured to use SQLite"; `tests/conftest.py:13` runs integration tests on `settings.database_url`, "the main DB for now". |
| Layer rules | Parcial | AR-01, AR-04, AR-05 meet; AR-02 and AR-03 do not. |
| Every table by a migration; models match | Cumple | AR-06. |
| One canonical signed message shared with the webapp | No cumple | AR-14. |
| Configuration from the environment; no secrets in the repository; production refuses defaults | No cumple | AR-15; and the admin password `adminpassword123` is in `infrastructure/seed.py:29` (the webapp pre-fills it in its login form). |
| DoD: green CI (Ruff, format, Mypy, architecture tests, Pytest) | No cumple | ejecutado: Ruff 195 errors (182 fixable); `ruff format --check` 28 files to reformat; Mypy stops at once: "Source file found twice under different module names: `app.application.dto.transaction` and `backend.app.application.dto.transaction`"; Pytest 18 passed. There is no CI. |
| DoD: `docker compose up` from a clean clone with no manual steps | No cumple | en vivo (section 8): the API container shows "Up" but never answers `/health`; migrations and the seed are manual steps. |
| DoD: an integration test per endpoint on a real Postgres | No cumple | One integration test (`test_health.py`), on whatever `DATABASE_URL` points at. |

Section 2: 9 Cumple · 3 Parcial · 12 No cumple · 0 No verificable.

---

## 3. Stories: acceptance criteria and their tests

The MVP as built is E0 (VLA-01 to VLA-08). "Test —" marks a criterion without a test. All tests are unit tests of use cases with mocked ports, except `test_health_check`. Criteria are the ones in `docs/BACKLOG.md`.

### VLA-01 Layered project

| Criterion | Test | Status |
| --- | --- | --- |
| Five layers | — | Cumple (lectura) |
| `GET /health` 200 with the environment | `integration/test_health.py::test_health_check` | Cumple |
| Alembic creates the schema | — | Cumple (ejecutado on SQLite and PostgreSQL 16) |
| `make up` builds and starts the API with Postgres | — | No cumple (en vivo, section 8) |

### VLA-02 Users, roles, JWT

| Criterion | Test | Status |
| --- | --- | --- |
| Login returns a bearer JWT (HS256, 30 min) | `auth/test_login.py::test_login_success` | Parcial: the token service is mocked; the token's content is not checked |
| Wrong email or password → 401 | `test_login_invalid_email`, `test_login_invalid_password` | Parcial: they check the use case's `ValueError`, not the router's 401 |
| `GET /auth/me` | — | Cumple (lectura) |
| `POST /users` only for admin, 403 otherwise | — | No cumple (en vivo): it answers 201 with the new user, but nothing is saved; the database still had only the admin. `user_router.py` never commits; the repository only flushes (`user_repository_impl.py:36`) and the seed works because it commits itself (`seed.py:32`). The 403 was not tried. |
| Duplicate email → 400 | `auth/test_register_user.py::test_register_user_already_exists` | No cumple (en vivo): the same email twice → 201 and 201, because the first one was never saved |
| bcrypt hashes | — | Cumple (lectura) |
| `make seed` creates the admin once | — | Cumple (en vivo: "Admin user seeded successfully", then "Admin user already exists" on a second run) |

### VLA-03 Signed transactions

| Criterion | Test | Status |
| --- | --- | --- |
| Rebuilds the signed message and verifies Ed25519 | — (the signature service is mocked to `True`) | No cumple (en vivo): a transfer and a notarization submitted from the webapp in Chrome got 400 "Invalid transaction signature" (AR-14) |
| Invalid signature → 400 | — | Cumple (en vivo) |
| Insufficient balance → 400 | `ledger/test_submit_transaction.py::test_submit_transaction_insufficient_funds` | Cumple |
| Valid → `PENDING` with a SHA-256 `tx_hash` | `test_submit_transaction_success` | Cumple |
| Resubmitting the same hash returns the existing transaction | `test_submit_transaction_already_exists` | Cumple as written; but a replayed body never has the same hash (ejecutado: accepted 5 times out of 6, until the balance ran out; en vivo over HTTP: 201 and 201 with two different hashes). VLA-16 |
| `GET /transactions/{tx_hash}`, 404 if unknown | `ledger/test_get_transaction.py` (2 tests) | Parcial: use case only |

### VLA-04 Wallet and balance

| Criterion | Test | Status |
| --- | --- | --- |
| `POST /wallets/generate` returns an Ed25519 pair in hex | `wallet/test_generate_wallet.py::test_generate_wallet_success` | Parcial: the wallet service is mocked; `Ed25519ServiceImpl` has no test |
| Balance = confirmed received − (confirmed and pending sent + fees) | — (`test_get_balance_success` mocks the repository that implements the formula) | Cumple (lectura, `transaction_repository_impl.py:72-91`) |

### VLA-05 Proof of Work

| Criterion | Test | Status |
| --- | --- | --- |
| Takes every `PENDING` transaction | `ledger/test_mine_block.py::test_mine_block_success` | Cumple |
| Nonce with 4 leading hex zeros | — (consensus mocked; `ProofOfWorkServiceImpl` has no test) | Cumple (en vivo: every block hash starts with `0000`) |
| Links `previous_hash`, 64 zeros for genesis | `test_mine_block_success` (non-genesis case) | Parcial: genesis has no test |
| Confirms the transactions and links them to the block | — (no assertion on `tx_repo.update`) | Cumple (lectura) |
| `GET /blocks` newest first | — | Cumple (en vivo, in the webapp's explorer) |

### VLA-06 Reward and fees

| Criterion | Test | Status |
| --- | --- | --- |
| Coinbase of 50 + fees to the miner | — (the test counts two transactions, not the amount) | Cumple (en vivo: a new address had a balance of 50.0 after mining) |
| `fee` ≥ 0 | — | Cumple (lectura, `dto/transaction.py:13`) |
| A sender needs `amount + fee` | `test_submit_transaction_insufficient_funds` | Cumple |

### VLA-07 Peers and consensus

| Criterion | Test | Status |
| --- | --- | --- |
| Register 201, duplicate 400 | `network/test_register_node.py` (2 tests) | Cumple (en vivo: 201, then 400 "Node already registered") |
| `GET /nodes` | — | Cumple (en vivo, in the webapp's network page) |
| Resolve adopts a longer valid chain | `network/test_resolve_conflicts.py::test_resolve_conflicts_replacement` | No cumple (en vivo). Between two real nodes: B (0 blocks) resolved against A (9 blocks), A answered 401 to `/blocks/full`, and B kept 0 blocks with "Our chain is authoritative". Against a fake peer that claimed `total: 1000` with 2 unmined blocks, B accepted the chain as valid and crashed in `replace_chain` with `ModuleNotFoundError: No module named 'dateutil'` (500). The unit test shows the same weakness: a peer answering `total: 10` with 2 blocks is adopted |
| Says whether it replaced | Both resolve tests | Cumple |
| Broadcasts transactions and blocks | `test_submit_transaction_success`, `test_mine_block_success` (assert a task is created) | No cumple (en vivo): node B's log shows A's `POST /transactions` and `POST /nodes/resolve` answered 401; a transaction submitted on A was 404 on B |

### VLA-08 Notarization

| Criterion | Test | Status |
| --- | --- | --- |
| Payload signed, mined and returned by `GET /transactions/{tx_hash}` | — (no test mentions `payload`) | Parcial (en vivo): returned by `GET /transactions/{tx_hash}` after mining, but `null` for the same transaction in `/blocks/full` (`block_router.py:68-79`), which is what peers copy; `replace_chain` would not copy it either (`block_repository_impl.py:91-102`) |

### Stories outside the built MVP

VLA-09 (this documentation) is in review. VLA-10 to VLA-31 are not started; none of their criteria has a test.

### Totals for section 3

33 criteria in VLA-01 to VLA-08: 16 with a test, **17 without a test**. 21 Cumple · 6 Parcial · 6 No cumple. The live pass changed six statuses: two criteria that read well failed when run (`POST /users`, duplicate email), and three findings that came from reading were confirmed.

---

## 4. Data

What SPEC › Data model promises against what the migrations create on PostgreSQL 16.

| Item | Status | Evidence |
| --- | --- | --- |
| `users`: columns, unique index on `email`, enum `userrole` | Cumple | `2026_07_28_2245_create_users_table.py` |
| `blocks`: columns, unique indexes on `block_number` and `block_hash`, `nonce` default 0 | Cumple | `…2a0af7913890_create_ledger_tables.py`, `…1e7e4b033bd6_add_nonce_to_blocks.py` |
| `transactions`: columns, indexes on addresses, `status` and unique `tx_hash`, FK to `blocks` | Cumple | `…2a0af7913890…`, `…f494b1b603cf…`, `…753f79042c54…`, `…ae3c16a02c57…` |
| `nodes`: columns, unique index on `url` | Cumple | `…2359d827e9ba_add_nodes_table.py` |
| Models and migrations agree | Cumple | AR-06 |
| CHECK `amount ≥ 0` and `fee ≥ 0` | No cumple | Only the DTO validates it; nothing stops a row written by `replace_chain` with peer data. VLA-25 |
| `transactions.nonce`, unique (`sender_address`, `nonce`) | No cumple | Not built; VLA-16 |
| "A confirmed transaction always has a `block_id`; a pending one never does" | No cumple | en vivo: of three concurrent mines, one failed on the unique `block_number` after its coinbase was committed, leaving a `CONFIRMED` coinbase of 50 with no block. It counts in the miner's balance: 50 units that are in no block. No constraint enforces the rule (`mine_block.py:54` commits the coinbase before the block exists). |
| `downgrade base` leaves nothing | No cumple | AR-07 |
| Database roles and permissions | No verificable | SPEC promises none. The app connects as the role the Postgres image creates (`POSTGRES_USER`), owner of every table: it can drop the schema. See section 7. |

Also seen: the first migration's revision is a hand-written `1234567890ab`; file names mix two templates (`2026_07_28_2245_…` and `2026_7_29_017-<rev>_…`); `add_signature_to_transactions` adds a NOT NULL column without a default, which works only on an empty table.

Section 4: 5 Cumple · 0 Parcial · 4 No cumple · 1 No verificable.

---

## 5. Decisions (ADRs)

| ADR | Exists | Matches the code | Status |
| --- | --- | --- | --- |
| 0001 Layered FastAPI service | Yes | Except `httpx` in use cases and the seed in infrastructure, both recorded in the ADR with their story | Parcial |
| 0002 PostgreSQL everywhere, SQLite for unit tests | Yes, Proposed | The README still says SQLite; integration tests use the main database | No verificable (proposed) |
| 0003 Ed25519 and SHA-256 Proof of Work | Yes | Yes; the server-side key generation it flags is recorded as a deviation | Cumple |
| 0004 Canonical signed message with a nonce | Yes, Proposed | Not implemented | No verificable (proposed) |
| 0005 One server behind Caddy | Yes, Proposed | Not implemented | No verificable (proposed) |

No decision visible in the code is missing an ADR, except the three "proposed rules" of ARCHITECTURE_RULES.md (composition root, injected clock, unit of work), which are proposals, not decisions.

Section 5: 1 Cumple · 1 Parcial · 0 No cumple · 3 No verificable.

---

## 6. Deviations from SPEC.md

| What the code does | What SPEC says | ADR that justifies it |
| --- | --- | --- |
| Signs and verifies `json.dumps` with spaces and float amounts | One canonical message shared with the webapp | None (ADR-0004 proposes the fix) |
| Hashes `id`, addresses, `amount`, `timestamp`, `payload`; not `fee` or `signature` | The hash covers every signed field (target) | None (VLA-16) |
| `resolve` trusts the peer's `total` and checks only hash links | SPEC › Valid chain | None (VLA-18) |
| Fetches at most 100 blocks from a peer and counts at most 100 local blocks | The whole chain | None (VLA-18) |
| `replace_chain` and `/blocks/full` drop `payload` | Notarizations survive a sync | None (VLA-18, VLA-20) |
| `total` in paginated responses is the page size (`block_router.py:44`, "Simplified total for now") | The number of matching rows | None (VLA-20) |
| Mining, peers and resolve open to any role | SPEC › Permissions by role | None (VLA-19) |
| Each repository method commits; mining is several transactions | Mining is atomic | None (VLA-17) |
| Server generates private keys in every environment | Development only | ADR-0003 records it; fix in VLA-21 |
| README: SQLite, Python 3.14+, `tests/unit/...` from the root | PostgreSQL, Python 3.12, `backend/tests` | None (ADR-0002 proposed; VLA-30) |
| `POST /users` answers 201 and saves nothing (en vivo) | Admin creates users | None (VLA-32) |
| A failed mine leaves a confirmed coinbase outside any block (en vivo) | A confirmed transaction always has a block | None (VLA-17) |

12 deviations; none is justified by an accepted ADR.

---

## 7. Scalability risks

- **Layers crossed.** Use cases do HTTP to peers (`httpx` in three of them), so peer behavior cannot be tested or swapped without patching a library (AR-02).
- **Duplicated code.** The same `Transaction → TransactionResponseDTO` mapping is written three times (`transaction_router.py:36-48`, `:63-75`, `block_router.py:68-79`, the last one missing `payload`, which is how it was lost); the broadcast loop is duplicated in `mine_block.py` and `submit_transaction.py`; every router wires infrastructure by hand.
- **Unbounded work per request.** `get_balance` loads every transaction of an address into memory and sums in Python, on every submission; mining takes every pending transaction with no block size limit; `/blocks/full` runs one query per block (N + 1).
- **The event loop.** Proof of Work is a synchronous loop inside an `async` endpoint: while a block is mined, the node answers nothing else. Fine at difficulty 4, a freeze at 6.
- **Concurrency.** Concurrent `POST /blocks/mine` read the same latest block. En vivo, three at once answered 200, 500 and 200: the failed one hit `UniqueViolationError` on `ix_blocks_block_number` after its coinbase was already committed.
- **Database privileges.** The app uses the owner role; a SQL injection or a bad `replace_chain` can delete everything. `replace_chain` already deletes every confirmed transaction before inserting the peer's.
- **Size of files.** No file is large: the biggest is `uv.lock`; in code, `block_router.py` (118 lines) and `mine_block.py` (120). Not a risk today.

---

## 8. Reproducibility

From a fresh clone, following the README and the Makefile:

| Step | Result | Evidence |
| --- | --- | --- |
| `git clone`, `uv sync` | Partly works | ejecutado: installs runtime dependencies only. `pytest`, `ruff` and `mypy` are an optional extra (`[project.optional-dependencies] dev`), so they are not in the virtualenv; `uv run pytest` falls back to whatever is on the PATH. `uv sync --extra dev` is needed and not documented. |
| Import the app with runtime dependencies | Fails | ejecutado: `ModuleNotFoundError: No module named 'httpx'` (`submit_transaction.py:2`). `python-dateutil` (used in `replace_chain`) is not installed either. |
| README test command | Fails | `tests/unit/application/use_cases` does not exist from the root, and the command hard-codes `C:\Users\USER\...` in `PYTHONPATH`. `make test` (`backend/tests`) works with the dev extra. |
| `make lint`, `make typecheck` | Fail | Section 2.2. |
| `docker build .` | Builds | ejecutado. |
| Import the app inside the image | Fails | ejecutado: `ImportError: … requires that the Python 'greenlet' library is installed`. The Dockerfile copies `pyproject.toml` but not `uv.lock`, so the image resolved SQLAlchemy 2.1.5 instead of the locked 2.0.51, and no greenlet; `httpx` would fail next. |
| `make up` / `docker compose up` | Fails | en vivo: Postgres becomes healthy and the API container shows "Up", but its log ends in the same `greenlet` `ImportError` and `/health` never answers. "Up" is misleading: with `--reload`, uvicorn's reloader process stays alive after the app fails to import. `docker compose config` warns that `version` is obsolete. |
| Migrations | Manual | ejecutado: `alembic upgrade head` works on SQLite and PostgreSQL 16, but nothing runs it on start. |
| `make seed` | Works | en vivo on two databases: creates the admin, and a second run says it already exists. Note that `python-dateutil` is missing even from the working copy's virtualenv, so this machine's dev setup is not complete either. |

**Verdict:** the project does not come up from a clean clone with the documented commands (en vivo). It runs only from a virtualenv that has the dev extra, with migrations and the seed run by hand.

---

## Summary

| Section | Cumple | Parcial | No cumple | No verificable |
| --- | :-: | :-: | :-: | :-: |
| 1. Structure (present / missing / extra / elsewhere) | 12 | — | 9 missing · 3 extra · 2 elsewhere | — |
| 2. Architecture rules (AR and CLAUDE.md) | 9 | 3 | 12 | 0 |
| 3. Story criteria (VLA-01 to 08) | 21 | 6 | 6 | 0 |
| 4. Data | 5 | 0 | 4 | 1 |
| 5. ADRs | 1 | 1 | 0 | 3 |
| 6. Deviations | — | — | 12, none justified | — |
| 8. Reproducibility | 3 steps work | 1 | 5 | 0 |

## Corrections, by priority

### Blocking

1. **Transactions signed in the webapp are rejected.** Accept ADR-0004 and implement it with shared vectors. VLA-15 (with VLW-15).
2. **The Docker image cannot start the app.** Declare `httpx` and `sqlalchemy[asyncio]`; build from `uv.lock` with `--frozen`. VLA-11, VLA-22.
3. **Forgeable tokens.** Without `SECRET_KEY` the API signs JWTs with `"supersecretkey"`, and Compose does not set it. Refuse it in production. VLA-21.
4. **Known admin password.** `adminpassword123` is in the seed and pre-filled in the webapp's login form. VLA-24 (with VLW-17).
5. **Replayable transactions.** The same signed body was accepted five times. VLA-16.
6. **Any user can rewrite the chain.** Any authenticated user can register a peer and call resolve, and resolve adopts whatever a peer calls longer if its hashes link. Full validation and roles. VLA-18, VLA-19.
7. **Server-side request forgery.** A registered peer URL can be any address, including the server's own network. VLA-19.
8. **No CI.** Nothing stops a PR that breaks the build. VLA-10.
9. **Concurrent mining creates money.** A failed mine left a confirmed coinbase of 50 outside any block, counted in the balance (en vivo). VLA-17.

### Important

1. `POST /users` answers 201 and saves nothing, so the admin cannot create any other account (en vivo). VLA-32.
2. Mining is not atomic and freezes the event loop. VLA-17.
3. Broadcast and resolve fail between authenticated nodes; a longer chain makes resolve crash on the missing `dateutil`. VLA-19, VLA-11.
4. Notarization payloads are lost when a chain is synced; full blocks do not send them. VLA-18, VLA-20.
5. `total` is the page size, and sync stops at 100 blocks. VLA-18, VLA-20.
6. Ruff 195 errors, 28 files to reformat, Mypy does not run. VLA-12.
7. Integration tests run on the main database and their fixture drops all tables. VLA-25.
8. `uv sync` does not install the dev tools; the README's commands do not work from a clean clone. VLA-11, VLA-30.
9. CORS allows only `localhost:5173`, hard-coded. VLA-21.
10. The transaction hash does not cover `fee` or `signature`. VLA-16.
11. No test with a real signature, no test of `payload`, no test of any router's status codes. VLA-15, VLA-25.

### Minor

1. `downgrade base` leaves the `transactionstatus` type. VLA-25.
2. `Pipfile` with Python 3.11; pre-commit pins Ruff 0.5.6 against 0.16.0 in the lock. VLA-11.
3. `version: '3.8'` in `docker-compose.yml` is obsolete; `--reload` and the bind mount belong to development only. VLA-23.
4. The first migration's revision id is a placeholder and the file names mix two templates. Leave them (renaming revisions breaks existing databases); fix the template for new ones.
5. `use_cases/{ledger,network,wallet}` have no `__init__.py` while `auth` does; unused imports (`Optional`, `TransactionStatus` in `block_model.py`). VLA-12.
6. Comments that narrate instead of explaining ("Wait, our /transactions requires auth!"). VLA-14.
