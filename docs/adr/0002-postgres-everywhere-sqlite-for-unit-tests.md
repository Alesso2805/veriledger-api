# ADR-0002: PostgreSQL wherever the app runs; SQLite only for unit tests

- **Status:** Accepted on 2026-10-20 (product owner)
- **Date:** 2026-10-20
- **Related:** SPEC.md › Data model; VLA-11, VLA-25, VLA-30; audit 2026-10-20 § 6

## Context

The repository says two things. The README says "SQLite (aiosqlite) … no external database engine is required" and its test commands use `sqlite+aiosqlite:///:memory:`. `.env.example`, `docker-compose.yml` and the `asyncpg` dependency say PostgreSQL. The migrations run on both (checked on 2026-10-20: upgrade on SQLite and on PostgreSQL 16, `alembic check` clean on PostgreSQL).

What differs between them matters to a ledger: concurrent writers (two miners), `SELECT … FOR UPDATE`, enum types, CHECK constraints and transactional DDL. Tests on SQLite would not see the duplicate-block race of VLA-17.

## Options

1. **SQLite everywhere.** Simplest to run, but one writer at a time and none of the locking VLA-17 needs; a deployed demo with several users would serialize every write.
2. **PostgreSQL everywhere,** including unit tests. Slower unit tests, Docker needed to run any test.
3. **PostgreSQL wherever the app runs** (local Compose, CI integration tests, the server), **SQLite in memory only for unit tests** that never reach SQL specifics.

## Decision

Option 3.

- `DATABASE_URL` is always `postgresql+asyncpg://…` in `.env.example`, Compose and the server.
- Unit tests mock the repositories, as they do today; the few that need a session may use SQLite in memory.
- Integration tests run against PostgreSQL in their own database (VLA-25), never the one in `DATABASE_URL`: the current `conftest.py` points at "the main DB for now" and its `drop_all` fixture would empty it.
- `aiosqlite` moves to the dev dependency group.
- The README is corrected in VLA-30.

## Consequences

- Running the integration tests needs Docker; CI provides it.
- Anything that depends on PostgreSQL behavior (locks in VLA-17, CHECK constraints in VLA-25) is tested only in integration tests, by design.
