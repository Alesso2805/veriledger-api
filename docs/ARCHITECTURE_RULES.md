# Architecture rules

Oct 20, 2026 · Sources: [SPEC.md](SPEC.md), [BACKLOG.md](BACKLOG.md), [CLAUDE.md](../CLAUDE.md), the README and [the ADRs](adr/).

Each rule is one sentence that a test can prove or refute. A rule about "every" module, route, table or port is checked by a test that walks the whole list, so something new that breaks it fails without anyone adding a case. The tests do not exist yet: they are VLA-13, and wait for the tool below to be confirmed.

## Rules

| ID | Rule | Origin | How it is verified |
| --- | --- | --- | --- |
| AR-01 | Every module under `backend/app/domain` imports only the standard library and `backend.app.domain`. | README › Architecture ("zero dependencies on external frameworks"); SPEC › Architecture; ADR-0001 | Pytest: parse every `.py` under `domain` with `ast` and assert each import is in `sys.stdlib_module_names` or starts with `backend.app.domain`. |
| AR-02 | Every module under `backend/app/application` imports only the standard library, `pydantic`, and `backend.app.{domain,core,application}`. | SPEC › Architecture (layer table); CLAUDE.md › Architecture rules ("never FastAPI, SQLAlchemy or httpx") | Pytest: the same `ast` walk over every module of `application`, with that allowlist. An allowlist, not a denylist, so a new I/O library fails too. |
| AR-03 | `backend.app.infrastructure` imports neither `backend.app.application` nor `backend.app.presentation`, directly or transitively. | SPEC › Architecture (layer table and the seed note) | import-linter `forbidden` contract, run by `lint-imports` in CI. |
| AR-04 | `backend.app.core` imports no other layer of `backend.app`. | SPEC › Architecture (`core` is cross-cutting) | import-linter `forbidden` contract. |
| AR-05 | Only `backend.app.main` imports `backend.app.presentation`. | SPEC › Architecture (`presentation` is the outer layer) | import-linter `forbidden` contract from `domain`, `application`, `infrastructure` and `core` to `presentation`. |
| AR-06 | The SQLAlchemy models and the Alembic history describe the same schema. | SPEC › Data model › Rules | Integration test on Postgres: `alembic upgrade head`, then `alembic check` must report no new operations. Covers every table by construction. |
| AR-07 | The migration history is reversible: `upgrade head → downgrade base → upgrade head` succeeds on Postgres and `downgrade base` leaves no table or enum type behind. | SPEC › Data model › Rules | Integration test on Postgres that runs the cycle and queries `pg_tables` and `pg_type` for leftovers. |
| AR-08 | Every route requires a valid JWT except the public ones listed in SPEC › API contract: `/health`, `/auth/login`, `/auth/demo`, `/wallets/generate`, `/wallets/{address}/balance`, `/wallets/{address}/nonce`, `/wallets/{address}/transactions`, the OpenAPI docs, and from VLA-36 the reads of ADR-0006 (`GET /blocks…`, `GET /transactions…`, `GET /nodes`). No write route is public. | SPEC › API contract; ADR-0006 | Pytest: iterate `app.routes`, walk each route's dependency tree and assert `get_current_user` is in it unless the method and path are in the public list; a second assertion fails on any public route whose method is not GET, except `/auth/login` and `/auth/demo`. |
| AR-09 | Every route requires the roles of SPEC › Permissions by role; a demo account has exactly the `trader` role. | SPEC › Non-functional requirements › Permissions by role; ADR-0006 | Pytest: a table path → roles taken from SPEC; iterate `app.routes` and fail on a route missing from the table or with other roles. |
| AR-10 | Every route declares a Pydantic response model. | SPEC › API contract ("the generated OpenAPI document is the contract") | Pytest: iterate `app.routes` and assert `route.response_model` is a `BaseModel` subclass (or a list of one). |
| AR-11 | Every port in `domain/ports` has an implementation in `infrastructure`, and every repository implementation is `<Port>Impl` in `infrastructure/repositories/<name>_repository_impl.py`. | ADR-0001; naming convention of the code | Pytest: import every module, iterate the `ABC` subclasses defined in `domain/ports`, find their concrete subclasses and check module and name. |
| AR-12 | Every use case is one class in `application/use_cases/<context>/<name>.py` with a public `execute` method and a unit test file `tests/unit/application/use_cases/<context>/test_<name>.py`. | SPEC › Architecture ("one class per file, an `execute` method"); ADR-0001 | Pytest: iterate the files under `use_cases`. |
| AR-13 | Every table and column name is English `snake_case`, and every table has `created_at` and `updated_at`. | SPEC › Data model; SPEC › Conventions | Pytest: iterate `Base.metadata.sorted_tables` and their columns. |
| AR-14 | The signed message of a transaction is built by one function, and it reproduces every vector of `docs/signing-vectors.json`. | SPEC › Signing and hashing contract; ADR-0004 (proposed) | Pytest: iterate the vectors; for each, build the message, compare it byte for byte and verify the signature. Verifiable once ADR-0004 is accepted and VLA-15 writes the vectors. |
| AR-15 | With `APP_ENV=production`, the settings refuse a missing `SECRET_KEY`, the example value or one under 32 bytes. | SPEC › Non-functional requirements › Security; CLAUDE.md ("production refuses default secrets") | Pytest: build `Settings` for each bad case and expect a validation error. |

## Promises that are not verifiable as written

They come from the README. They are not rules until they are made concrete; this is how I propose to do it.

| Promise | Why it is not verifiable | Proposal |
| --- | --- | --- |
| "Strictly follows Clean Architecture" | Names a style, not a dependency rule. | It already means AR-01 to AR-05. Change the README to say "layers with the dependency rules of docs/ARCHITECTURE_RULES.md". |
| "Domain-Driven Design" | There are no aggregates, invariants in entities or bounded contexts beyond the folder names. | Either (a) make the contexts `auth`, `ledger`, `network`, `wallet` independent (import-linter `independence` contract over `application/use_cases/*`, which holds today) and move invariants into the entities (a `Transaction` with a negative amount cannot be built), or (b) drop "DDD" from the README. |
| "Mathematically valid chain" and "decentralized consensus" | Today the check is only that hashes link; "valid" has no definition in the code. | SPEC › Valid chain defines it; each of its rules becomes one tampered-chain test in VLA-18. |

## Proposed rules (not in the specification; they need your decision)

| Proposal | Why | State today |
| --- | --- | --- |
| A composition root: only `presentation/dependencies` imports `infrastructure`; routers receive use cases through `Depends`. | The wiring is repeated in every router, and swapping an implementation means editing six files. | Every router imports `infrastructure` directly. |
| An injected clock and id generator: `datetime.now` and `uuid.uuid4` only inside `infrastructure` (Ruff `banned-api`, as in willay). | Use cases become deterministic in tests; replay and ordering tests (VLA-16, VLA-18) need a controllable clock. | 8 occurrences in `application`. |
| Use cases do not commit; a unit of work does. | Atomic mining (VLA-17) is impossible while every repository method commits on its own. | Every `create` and `update` commits. |

## Proposed tool (waiting for your confirmation)

**import-linter + Pytest architecture tests + Alembic**, all run in CI (VLA-10):

- **import-linter** for the contracts between internal packages (AR-03, AR-04, AR-05). It follows imports transitively, which a per-file check does not, and it is what willay uses (`[tool.importlinter]` in `pyproject.toml`, `uv run lint-imports`).
- **Pytest** in `backend/tests/architecture/` for the rules that walk a list: the `ast` allowlists (AR-01, AR-02), the routes (AR-08, AR-09, AR-10), the ports and use cases (AR-11, AR-12) and the schema names (AR-13). An allowlist needs code; import-linter's `forbidden` contracts only take a list of packages to forbid, so a new library would slip through.
- **Alembic against a real Postgres** in `backend/tests/integration/` for AR-06 and AR-07.
- AR-14 and AR-15 are ordinary unit tests in `backend/tests/unit/`.

Alternatives considered: only Pytest with `ast` (no new dependency, but transitive imports would need to be reimplemented), and PyTestArch (an ArchUnit port for Python, less used and slower). Neither checks more than the proposal.

## Which test covers which rule (after confirmation)

| Test | Rules |
| --- | --- |
| `pyproject.toml` › `[tool.importlinter]` (`lint-imports`) | AR-03, AR-04, AR-05 |
| `backend/tests/architecture/test_imports.py` | AR-01, AR-02 |
| `backend/tests/architecture/test_routes.py` | AR-08, AR-09, AR-10 |
| `backend/tests/architecture/test_ports_and_use_cases.py` | AR-11, AR-12 |
| `backend/tests/architecture/test_schema_names.py` | AR-13 |
| `backend/tests/integration/test_migrations.py` | AR-06, AR-07 |
| `backend/tests/unit/test_signing_vectors.py` | AR-14 |
| `backend/tests/unit/core/test_settings.py` | AR-15 |

**A rule that will fail on the first run, on its own.** AR-02: `mine_block.py`, `submit_transaction.py` and `resolve_conflicts.py` import `httpx`. AR-03 (the seed), AR-07 (the enum left behind), AR-09 (roles), AR-10 (two routes without a response model), AR-14 and AR-15 fail too. VLA-13 lands the tests with those rules marked `xfail` and the story that fixes each, so CI is green and the debt is visible; removing an `xfail` is part of the fixing story's DoD.
