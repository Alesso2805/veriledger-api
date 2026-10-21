# ADR-0007: One database transaction per request, committed before the response

- **Status:** Accepted on 2026-10-20 (product owner)
- **Date:** 2026-10-20
- **Related:** VLA-32, VLA-17, VLA-19; ARCHITECTURE_RULES.md AR-16; ADR-0001

## Context

On 2026-10-20 the audit found that `POST /users` saves nothing. The user repository flushed, nobody committed, and closing the session rolled the insert back. The other repositories committed inside each `create` and `update`, so a request that failed halfway kept half its writes: a failed concurrent mine leaves a confirmed coinbase outside any block (VLA-17).

Two details of the stack shape the fix:

- In FastAPI 0.140 a dependency with `yield` ends, by default, after the response has been sent (`scope="request"`). A commit there can fail after the client already got a 201.
- New transactions and blocks were broadcast to peers with `asyncio.create_task`. A task started inside the request would use the session while the dependency commits it, or after it is closed.

## Options

1. **Commit in every repository method** (as built). No atomicity, and a use case cannot group writes.
2. **Commit in every router.** Atomic, but every new route must remember it; one that forgets loses data silently, as `POST /users` did.
3. **The session dependency commits, with FastAPI's default scope.** One place, but the commit runs after the response.
4. **The session dependency commits with `scope="function"`,** and broadcasts run after the response.

## Decision

Option 4.

- `get_db_session` commits after the endpoint returns. If the endpoint raises, the commit is skipped and closing the session rolls back.
- Every route and dependency takes the session as `DbSession` (`presentation/dependencies/database.py`), which is `Annotated[AsyncSession, Depends(get_db_session, scope="function")]`. The dependency ends, and commits, before the response is sent. FastAPI caches a dependency per scope, so one alias also keeps one session per request.
- Repositories `flush`, never `commit`, so constraint errors still surface inside the use case.
- Use cases read the peers inside the request; the router schedules `broadcast_*` as a FastAPI background task, which runs after the response. Peers only hear of committed data, and the broadcast never touches the session.

## Consequences

- A request writes all or nothing, and mining is atomic. Its transaction now spans the Proof of Work, which runs on the event loop until VLA-17.
- A route that took the session any other way would commit after the response and open a second session. AR-16's test walks every route and fails on it.
- Background tasks cannot use the request's session; work that needs the database after the response opens its own.
- Integration tests swap the session factory (`database.async_session_maker`), not `get_db_session`, so they go through the real commit.
- A duplicate email that races past the use case's check fails at flush with a 500, not a 400. Not addressed here.
