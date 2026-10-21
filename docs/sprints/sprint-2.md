# Sprint 2 — No replays, atomic mining, safe peers, and every piece of data the webapp's views need (VLA-16, VLA-17, VLA-19, VLA-20, VLA-33, VLA-34, VLA-36)

**Status as of 2026-10-21:** closed on October 21, 2026, ahead of the planned November 9 – 22. All 7 stories are done, 24 points.

The webapp's counterpart, VLW-15 to VLW-18, VLW-21, VLW-22, VLW-28 and VLW-30, is merged. On this sprint's endpoints the webapp has also built VLW-29, VLW-31, VLW-32 and the search half of VLW-19.

**Order:** VLA-20, VLA-33, VLA-16, VLA-36, VLA-34, VLA-19, VLA-17.

- The plan put the four data endpoints first and VLA-16 after them. VLA-16 moved up to third, agreed with the webapp, because its signing (VLW-18) needed the version 2 vectors sooner than its wallet needed VLA-34.
- VLA-19 went before VLA-17.

**Decisions it waited for, all taken by the product owner**

- **VLA-16:** a byte-identical replay answers 200 with the stored transaction, and a coinbase takes its block number as its nonce (ADR-0004).
- **VLA-19:** four PRs, in this order: the port, the roles, the peer token, the peer URLs. Reading whole chains was brought forward from VLA-18 after part 1 found the bug described under Sprint decisions.
- **VLA-17:** two parts, and a worker thread rather than a process pool for the Proof of Work (ADR-0008).

## What was delivered

`main` is at `001ed2e`, CI green. Every PR below was merged with a merge commit after its `checks` run passed.

| Story | PRs | Result | Verification |
| --- | --- | --- | --- |
| VLA-20 | #19 | `GET /blocks/{block_hash}`. Block responses carry `transaction_hashes`. Transaction responses carry `block_number` and `block_hash`, `null` while pending. `total` is the real number of blocks. `/blocks/full` keeps each transaction's `payload` | `test_lookups.py` on Postgres: a block by hash, and 404 for an unknown one; `total` with `limit=1`; a transfer before and after mining; the notarization's payload |
| VLA-33 | #20 | `GET /transactions?status=PENDING&skip&limit`: the mempool, newest first, paginated. Any other status answers 422 | `test_pending_transactions.py`: two pages of two, without the mined transaction; 422 for an out-of-range `limit`, `skip` or `status` |
| VLA-16 | #21, #22 | The signed message carries `nonce`, from 1 to 2^53 − 1. `docs/signing-vectors.json` is at version 2, signed with `@noble/curves` 2.2.0. New `GET /wallets/{address}/nonce`. A used or skipped nonce answers 409, backed by a unique (`sender_address`, `nonce`) constraint. `tx_hash` covers the signed fields and the signature, so a byte-identical replay answers 200 with the stored transaction | `test_signing_vectors.py` (AR-14) and `test_nonce.py`: every vector in order; a replay answers 201, then 200, and leaves one row; used and skipped nonces answer 409; the race constraint |
| VLA-36 | #23 | Six reads need no token: `/blocks`, `/blocks/full`, `/blocks/{block_hash}`, the mempool, `/transactions/{tx_hash}` and `/nodes`. `limit` is capped at 100 (ADR-0006) | `test_public_reads.py`: the six reads without `Authorization`; the five writes answer 401; 422 above 100. AR-08 |
| VLA-34 | #24 | `GET /wallets/{address}/transactions`: what an address sent or received, newest first, with its block. The page's blocks are read in one query | `test_address_activity.py`: the order across two pages, an empty address, a notarization listed once, 422 |
| VLA-19 | #25, #26, #27, #28 | Peer calls go through the `PeerClient` port, which reads whole chains page by page. Mining needs the trader or admin role, peers the admin role. Nodes share a `PEER_TOKEN` (`X-Peer-Token`), which `POST /transactions` and `POST /nodes/resolve` accept. A peer URL must be a public `http(s)` address unless `ALLOW_PRIVATE_PEERS` is set; this is checked at registration and before each call | `test_roles.py`, `test_peer_token.py`, `test_peer_urls.py`, `test_resolving_peer_url_policy.py`. `test_two_nodes.py` starts two uvicorn processes with two databases: a transfer and a notarization reach B, and B adopts the chain that mines them |
| VLA-17 | #29, #30 | A block mined at a height already taken answers 409. Nothing is written before the Proof of Work, and the block is written first. The latest block is read before the mempool. The Proof of Work runs in a worker thread (ADR-0008). New settings `MINING_DIFFICULTY` and `MINING_REWARD` | `test_mining.py`: a failure while confirming leaves nothing; a stale latest block answers 409; four simultaneous mines give consecutive blocks or 409, with one coinbase each; `/health` answers while the Proof of Work is held; the endpoint uses the settings |

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
TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@127.0.0.1:55439/test \
uv run pytest backend/tests -rs            # 202 passed, 4 xfailed
docker stop vl-test
```

`test_two_nodes.py` creates and drops its own two databases on that server, and starts the two API processes on free ports. The URL says `127.0.0.1`, not `localhost`: on Windows, `localhost` tries `::1` first, and every refused attempt adds about two seconds to each new connection.

## Sprint decisions

- **Replays and nonces (ADR-0004).**
  - The hash covers what was signed and nothing else: no id and no arrival time. So the same signed body is the same transaction, and resending it is safe.
  - The webapp relies on this to retry after a timeout.
- **Public reads (ADR-0006).**
  - Reading needs no account, and every write keeps its token and role.
  - Pages hold at most 100 items, so a public read cannot ask for the whole chain.
- **Peers.**
  - The peer token names a node, not a person: a transaction a peer offers is checked against its signature, balance and nonce like any other.
  - Peer URLs must resolve only to public addresses. This keeps an admin token from pointing the server at its own network or a cloud's metadata service.
  - DNS rebinding between the check and the connection is not covered, and SPEC › Peer URLs says so.
- **Brought forward from VLA-18,** because the tests of this sprint met it:
  - Reading a peer's whole chain and comparing it with our whole chain. Before, a peer's 100 newest blocks could replace a longer chain of ours.
  - What an adopted chain keeps: payloads and nonces. An adopted chain also replaces the pending copies of the transactions it holds. Two running nodes found that adopting the chain answered 500 otherwise.
- **Mining (ADR-0008).**
  - The unique height turns a race into a 409.
  - Reading the latest block before the mempool keeps a transaction out of two blocks.
  - The search runs in a thread, so the node keeps answering.
- **Architecture debt.** VLA-19 paid AR-02's (`httpx` left the use cases) and AR-09's (the mining and peer routes got their roles). Still pinned: AR-07 for VLA-25 and AR-15 for VLA-21.
- **CI and local machines run different Python patch releases.** `.python-version` says `3.12`, so CI uses the runner's CPython 3.12.3 while local machines have 3.12.10. It surfaced once: 3.12.3 takes `::ffff:224.0.0.1` for a public unicast address. Not decided yet, see the retro.

## Changes to the specification in this sprint

- **`docs(spec)` commits, one per story or part:**
  - the lookups (VLA-20) and the mempool list (VLA-33);
  - the nonce, and the transaction hash with replays (VLA-16);
  - the public reads (VLA-36) and an address's activity (VLA-34);
  - the `PeerClient` port, the permissions table, the peer token and adopting a chain, and the peer URLs (VLA-19);
  - the request flow of mining with its 409, then the Proof of Work off the event loop and the mining settings (VLA-17).
- **ARCHITECTURE_RULES.md:** AR-08 lists the public reads and pins the two peer routes. AR-02's and AR-09's debt is paid.
- **ADRs:** ADR-0004 records the nonce's range, the race constraint, the replay answer and the coinbase nonce. ADR-0008 is added.
- **`docs/signing-vectors.json`** is at version 2.
- **BACKLOG.md:**
  - VLA-17's criterion is corrected: ADR-0007 had already removed the orphan coinbase.
  - VLA-18 records what VLA-19 brought forward.
  - This PR fills in the PR numbers of every Sprint 2 story, five of which still said "To do" after merging, and marks VLA-09 done (#2).

## Carried into Sprint 3

- **Sprint 3's plan:** VLA-18, VLA-22, VLA-23, VLA-25 and VLA-35.
- **What the webapp waits for** (its session, 2026-10-21):
  - **VLA-35** (`POST /auth/demo`) blocks VLW-34. The webapp also needs to know how a demo account shows in `/auth/login` and `/auth/me`, where its expiry comes from, and the exact 429 messages.
  - **`docs/openapi.json`** blocks VLW-19b, the generated types. It belongs to VLA-30, in Sprint 4. Bringing it forward is for the product owner to decide.
- **The webapp checked this sprint's contracts while building its views and found no mismatch.** It checked the register 400 texts, resolve's `{message, replaced}`, the activity endpoint, the nonce 409 text and the `FAILED` status. Its tower already shows the new mining 409 as the API writes it.

## Retro

- **Went well:** tests that run the real thing found what reading the code would not. Two running nodes showed that adopting a chain broke on a pending copy. CI's other Python patch release caught an IPv4-mapped multicast address. Four simultaneous mines showed that the race happens on every run.
- **To improve:** five stories stayed "To do" in the backlog after they merged, and two said "this PR" for good. CI and local machines ran different Python patch releases.
- **To try:** the PR that closes a story writes its own number into the backlog right after it is opened. Pin Python to a patch release in `.python-version` and in CI, a small `chore` if the product owner agrees.
