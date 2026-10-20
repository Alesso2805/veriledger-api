# Sprint 0 — Baseline as built, documented and audited (VLA-01 to VLA-09)

**Status as of 2026-10-20:** VLA-01 to VLA-08 were built on July 28 and 29, 2026, in "phases" before there was a backlog; they are recorded here retroactively so that each one has acceptance criteria the audit can check. VLA-09 (this documentation) is in review. The sprint closes on October 25.

## Where the code stands

`main` at `c1f113a`. The history shows one merged PR (#1, `feat/mining-rewards-and-fees`); the branches `feat/foundation-phase` and `feat/p2p-network` also exist on the remote. No CI ran on any of them: the repository has no workflow.

## What was delivered

| Story | Commits | Result | Verification |
| --- | --- | --- | --- |
| VLA-01 | `dc450f3` | Five layers, FastAPI app, settings, structlog, async SQLAlchemy, Alembic, Compose with Postgres | `GET /health` test passes. `docker compose up` from a clean clone: the container shows "Up" but the app never imports (greenlet, then httpx missing) |
| VLA-02 | `b187581` | JWT login, `/auth/me`, roles, admin-only user creation, bcrypt, admin seed | Unit tests for login and registration. Live: the seed works; `POST /users` answers 201 and saves nothing (VLA-32) |
| VLA-03 | `104df1e`, `6cbca3d` | Signed transactions verified with Ed25519 into the mempool, lookup by hash | Unit tests with mocks. A transaction signed the way the webapp signs is rejected (audit) |
| VLA-04 | `6cbca3d`, `9bb1c8f` | Server-side key pair generation and balance | Unit tests |
| VLA-05 | `104df1e`, `6cbca3d` | Proof of Work with 4 leading zeros, chained blocks, confirmations | Unit test with a mocked consensus service |
| VLA-06 | `9bb1c8f` | Coinbase of 50 + fees, fees in the balance check | Unit tests |
| VLA-07 | `68c1aa2`, `4bad341` | Peers, longest-chain resolve, broadcast of transactions and blocks | Unit tests with a mocked HTTP client. Live with two nodes: every peer call answered 401, so nothing syncs or spreads; a fake peer's chain passed validation and crashed on the missing `dateutil` |
| VLA-08 | `624caac` | Notarization payload inside the signed message | No test covers the payload. Live: returned by hash, `null` in `/blocks/full` |
| VLA-09 | — | CLAUDE.md, SPEC, BACKLOG, five ADRs, ARCHITECTURE_RULES, AUDIT, these notes | In review |

The suite on 2026-10-20: 18 tests (17 unit, 1 integration), all passing with SQLite in memory.

## Sprint decisions

- **One backlog per repository, one sprint calendar.** API stories are VLA-NN and webapp stories VLW-NN; both use the same sprint numbers and dates, and a story that needs its counterpart names it.
- **Contracts live here.** The signed message (ADR-0004) and the deployment (ADR-0005) are decided in this repository; the webapp's ADRs adopt them.
- **The audit drives the plan.** Every blocking or important finding of `docs/AUDIT.md` became a story in E1 to E4.
- **Proposed, not accepted:** ADR-0002 (Postgres everywhere), ADR-0004 (canonical message with a nonce) and ADR-0005 (one server behind Caddy) wait for the product owner.
- **Accepted: ADR-0006, demo access.**
  - Reads become public (VLA-36), and "Try the demo" creates a 24-hour trader account with no email (VLA-35).
  - The account expires, but its transactions stay on the chain.
  - Together with the webapp's design E (VLA-33, VLA-34), this moves the deployment to Sprint 5.

## Changes to the specification in this sprint

The specification did not exist before; `docs/SPEC.md` and `docs/BACKLOG.md` were written on 2026-10-20 from the code, the README and the audit.

## Retro

- **Went well:** the layers made the code quick to read and every use case has a unit test.
- **To improve:** everything was tested with mocks, so the failures that block the core flow (the webapp's signatures, the Docker image, users that are never saved, peers that cannot talk) were invisible until the audit ran the stack. The README describes SQLite and Python 3.14 while the code uses Postgres and 3.12.
- **To try:** from Sprint 1, one PR per story with CI, and every cross-repository contract pinned by a shared test vector.
