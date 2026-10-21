# ADR-0008: The Proof of Work runs in a worker thread of the API process

- **Status:** Accepted on 2026-10-21 (product owner, with the plan of VLA-17)
- **Date:** 2026-10-21
- **Related:** VLA-17; ADR-0003 (SHA-256 Proof of Work), ADR-0007 (one transaction per request)

## Context

`MineBlockUseCase` searched the nonce with a synchronous loop inside an `async` request. One API process serves every request on one event loop (SPEC › Processes), so while a block was mined nothing else was answered, not even `/health`.

The search is CPU-bound: it hashes a small JSON again and again. At the default difficulty of 4 that is about 65,000 hashes, well under a second. `MINING_DIFFICULTY` now lets an operator raise it, and each step multiplies the work by 16.

## Options

1. **Keep it on the event loop** (as built). The node stops answering for as long as the search takes.
2. **A worker thread** (`asyncio.to_thread`). The event loop stays free. The search holds the GIL, because hashlib only releases it for inputs larger than about 2 KB, but CPython switches threads every 5 ms, so other requests keep being answered, a little slower while a block is mined.
3. **A process pool.** The search runs in parallel with the requests. The block and the hasher must be pickled, and the pool must be started and shut down in the app's lifespan. On Windows, where processes are spawned, every worker starts a new interpreter.
4. **A separate miner service or a task queue.** It would need another container and a broker. That is out of scope for the plan (SPEC › Processes: no background workers).

## Decision

Option 2.

- `ConsensusService.mine_block` is `async`. `ProofOfWorkServiceImpl` runs its search with `asyncio.to_thread`, so how the work leaves the event loop is an infrastructure detail.
- The thread touches only the block being mined, never the database session. The writes happen after the search, on the event loop, inside the request's transaction (ADR-0007, VLA-17).

## Consequences

- `/health` and every other request are answered while a block is mined. `test_mining.py` holds the search and checks that `/health` answers first.
- Simultaneous mines each take a thread of the default executor (`min(32, CPUs + 4)`), and they share one CPU core because of the GIL.
- A request that is cancelled does not stop its thread; the search runs until it finds the nonce. That is negligible at difficulty 4, but not at 6 or more.
- If the difficulty has to rise, or mines become frequent, a process pool (option 3) is the next step, and only `ProofOfWorkServiceImpl` changes.
