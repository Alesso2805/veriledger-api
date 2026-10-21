# Sprint 1 — Green from a clean clone, CI that blocks regressions, and transactions from the webapp accepted (VLA-10 to VLA-15, VLA-32)

**Status as of 2026-10-21:** closed on October 21, 2026, ahead of the planned October 26 – November 8. All 7 stories done, 19 points. Webapp counterpart: VLW-10 to VLW-14, VLW-27 and VLW-33.

**Order:** VLA-11, VLA-32, VLA-12, VLA-10, VLA-13, VLA-15, VLA-14, as planned.

**Decisions it waited for, all taken by the product owner**

- The architecture-test tool: import-linter + Pytest architecture tests + Alembic, confirmed on 2026-10-20 (VLA-13).
- ADR-0004 (canonical signed message), accepted on 2026-10-20 (#15), together with ADR-0002 and ADR-0005 (VLA-15).
- The comment inventory, `docs/COMMENTS_REVIEW.md`, approved on 2026-10-21 (VLA-14).

## What was delivered

`main` at `a76f7b0`, CI green. Every PR below was merged with a merge commit after its `checks` run passed.

| Story | PRs | Result | Verification |
| --- | --- | --- | --- |
| VLA-11 | #3 | `httpx` and `sqlalchemy[asyncio]` are runtime dependencies; dev tools in a uv dependency group; Python 3.12 pinned (`.python-version`); `Pipfile` removed; `python-dateutil` replaced by `datetime.fromisoformat` | `uv sync` on a fresh clone installs Ruff, Mypy and pytest; `make check-imports`; `docker compose up --build` answers `/health` |
| VLA-32 | #4 | `POST /users` saves the user: one transaction per request, committed by the session dependency before the response (ADR-0007, AR-16); peers hear of transactions and blocks only after the commit | `backend/tests/integration/test_users.py` on Postgres: the user is read back from a new session and signs in; the same email twice answers 400 |
| VLA-12 | #5, #6, #7, #8 | Ruff 186 errors → 0; 29 files formatted; Mypy strict runs and passes; `.git-blame-ignore-revs` skips the formatting commits | `make lint`, `uv run ruff format --check backend`, `make typecheck` |
| VLA-10 | #9 | GitHub Actions job `checks` on every PR and on `main`: lock install, Ruff, format, Mypy, layer contracts, runtime-only import, tests with a PostgreSQL 16 service. `main` is protected: a PR and `checks` are required, administrators included | Any PR shows `checks`; canary #10 (a broken integration assertion) failed |
| VLA-13 | #11, #12, #13 | Every rule AR-01 to AR-16 has its test; the seed moved to `backend/app/cli/`; AR-10 fixed (two response models); failing rules recorded as debt (see decisions) | `uv run lint-imports`, `pytest backend/tests/architecture`, `backend/tests/integration/test_migrations.py`; canary #14 (infrastructure importing application) failed at the layer-contracts step |
| VLA-15 | #16 | `build_signed_message` builds ADR-0004's canonical message; `POST /transactions` takes `amount` and `fee` as the signed 8-decimal strings; `docs/signing-vectors.json` (version 1) signed with `@noble/curves`, the webapp's library | `backend/tests/unit/test_signing_vectors.py` (AR-14); `backend/tests/integration/test_signed_transactions.py`: the 4 vectors are accepted (201), a changed amount answers 400 |
| VLA-14 | #17 | Comments: 32 removed, 10 rewritten, 54 kept, per `docs/COMMENTS_REVIEW.md`; three rewrites now state a defect with the story that fixes it (VLA-16, VLA-19, VLA-20) | The 13 changed files have the same AST once docstrings are set aside; the inventory script lists the 64 entries kept or rewritten |

**How to check the whole sprint from a clean clone**

```bash
git clone https://github.com/Alesso2805/veriledger-api.git && cd veriledger-api
uv sync                                   # Python 3.12, runtime and dev dependencies from uv.lock
make lint                                 # Ruff and the layer contracts
uv run ruff format --check backend
make typecheck                            # Mypy strict
DATABASE_URL=postgresql+asyncpg://u:u@localhost/u make check-imports
docker run -d --rm --name vl-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 55439:5432 postgres:16-alpine
DATABASE_URL=sqlite+aiosqlite:///:memory: \
TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@localhost:55439/test \
uv run pytest backend/tests -rs            # 63 passed, 4 xfailed
docker stop vl-test
docker compose up --build                 # /health answers {"status":"ok",...}
```

## Sprint decisions

- **One transaction per request** (ADR-0007, AR-16). `get_db_session` commits after the endpoint returns, with `scope="function"` so the commit happens before the response; repositories flush; broadcasts run as background tasks after the response.
- **The request carries the signed strings** (ADR-0004, decided with VLA-15). `amount` and `fee` travel as 8-decimal strings with no leading zeros, so no side formats a float. The nonce comes with VLA-16 and version 2 of the vectors.
- **How failing architecture rules are recorded.** A rule over a list pins today's violations one by one; a rule without a list is `xfail(strict=True)`. Either way a fix fails until its marker goes. Debt carried into the next sprints: AR-02 (three use cases import `httpx`) and AR-09 (three routes lack their roles) for VLA-19, AR-07 (the ledger downgrade leaves its enum) for VLA-25, AR-15 (production settings) for VLA-21.
- **AR-10 was fixed, not pinned**, because no story covered it; AR-08 allows the public `POST /wallets/generate`, which writes nothing.
- **Pinned tooling.** GitHub Actions at releases at least two weeks old (`actions/checkout@v7.0.1`, `astral-sh/setup-uv@v10.2.0`), uv 0.11.25, import-linter 2.15.
- **Redesign early, in order** (product owner, 2026-10-20): the data endpoints VLA-20, VLA-33, VLA-34 and VLA-36 move to Sprint 2, VLA-18 to Sprint 3; deployment stays in Sprint 4.

## Changes to the specification in this sprint

- `docs(spec)` commits: the repository tree lists `.python-version`, `.pre-commit-config.yaml` and the CI workflow (VLA-11, VLA-10); the request flow and › Processes describe the commit before the response and the background broadcast (VLA-32); the seed lives in `backend/app/cli/` (VLA-13); the signed message as built and the request amounts of `POST /transactions` (VLA-15).
- ARCHITECTURE_RULES.md: the tool confirmed, AR-16 added, every rule's test listed, how failing rules are recorded, AR-08's exception, and how to walk every route (FastAPI 0.140 keeps included routers out of `app.routes`).
- ADRs: ADR-0007 (one transaction per request) added; ADR-0002, ADR-0004 and ADR-0005 accepted.

## Retro

- **Went well:** every change was checked by a real run, on Postgres, in CI, by canaries and by mutations, which caught mistakes before merge: an import only a test could reach, a migration-test reset that never ran, a canary that failed at Ruff instead of at the contract.
- **To improve:** two sessions edited `docs/` in parallel, so one PR conflicted (#15 and #16) and planning changes sat uncommitted for a day; and the GitHub API failed for hours, delaying PRs.
- **To try:** one session owns `docs/` at a time and opens its PR the same hour; scripts read files from git with `git ls-tree`, since Git Bash rewrites `revision:path` arguments.
