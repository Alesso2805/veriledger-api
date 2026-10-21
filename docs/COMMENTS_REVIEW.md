# Comment review (VLA-14)

Oct 21, 2026 · @Alessandro David

The inventory of every comment and docstring in `backend/app` and `backend/tests`, with the action proposed for each. Nothing changes in the code until the product owner approves this document; the cleanup then follows it, one commit per module.

## Brief

A comment stays only if it says **why**: a decision, a constraint, a consequence the code cannot show, or the ADR or story that explains it.

- **Remove** comments that restate the code, narrate the author's thinking ("Wait, …"), or label a step the next line already names.
- **Rewrite** comments that carry a real reason in the wrong words, or that state something no longer true. When the truth is a defect, the new text names the story that fixes it instead of hiding it.
- **Keep** comments that already say why.
- Docstrings follow the same rule: they stay when they state a contract the signature does not show (what a tuple holds, what is raised).
- **Out of scope:** the Alembic migrations (generated history) and `# noqa` / `# type:` pragmas, which are instructions to tools.
- **No behaviour change.** Only comments and docstrings move. Ruff, Mypy strict, `lint-imports` and the tests stay green after each commit.

## Summary

96 comments and docstrings: **32 remove, 10 rewrite, 54 keep.** Most of the 54 were written in Sprint 1 (VLA-11 to VLA-15) under this brief.

## For the product owner's decision

Three rewrites state a defect that the current comment hides or gets wrong. Confirm them, or say which ones to remove instead:

1. **The duplicate check in `submit_transaction.py`** says it stops an infinite gossip loop. It cannot: the transaction hash includes a fresh `id` and `timestamp`, so a resubmitted body never matches (ADR-0004 › Context). VLA-16 hashes the signed fields.
2. **The peer broadcast in `submit_transaction.py`** is eight lines of the author thinking aloud. The fact they circle around: peers require a JWT the call does not send, so the broadcast fails between authenticated nodes until VLA-19.
3. **`total` in `GET /blocks`** is "simplified": it counts the page, not the chain. VLA-20 returns the real count.

## Inventory

### application

| Where | Now | Action | Proposed |
| --- | --- | --- | --- |
| `dto/transaction.py:12` | The same 8-decimal strings that were signed (ADR-0004), so neither side formats a float | Keep | |
| `use_cases/ledger/mine_block.py:35` | Get pending transactions | Remove | |
| `mine_block.py:38` | Calculate total fees from pending txs | Remove | |
| `mine_block.py:43` | Create Coinbase transaction | Remove | |
| `mine_block.py:56` | Save coinbase tx | Remove | |
| `mine_block.py:62` | Get latest block to find previous hash | Remove | |
| `mine_block.py:65` | A stored block always has its hash; only a block being mined has none | Keep | |
| `mine_block.py:70` | Genesis block | Keep | Names what the `else` branch is |
| `mine_block.py:82` | Mine the block (find nonce and hash) | Remove | |
| `mine_block.py:83` | We use a difficulty of 4 for testing purposes | Rewrite | `Fixed difficulty until VLA-17 makes it a setting` |
| `mine_block.py:88` | Save the block | Remove | |
| `mine_block.py:91` | Update coinbase block_id | Remove | |
| `mine_block.py:95` | Update pending transactions to CONFIRMED and link to this block | Remove | |
| `mine_block.py:101` | Read the peers now: broadcast_block runs after the response, … | Keep | |
| `mine_block.py:123` | Trigger peers to resolve conflicts with our new chain | Keep | Why the broadcast is a resolve request, not the block |
| `use_cases/ledger/submit_transaction.py:32` | Check if transaction signature and contents generate a known hash to avoid infinite loops in gossip | Remove | Misplaced; its point moves to line 60 |
| `submit_transaction.py:33` | Wait, we need to generate the hash first to check if we already have it. | Remove | |
| `submit_transaction.py:60` | Check if already exists (avoid infinite gossip loop) | Rewrite (decision 1) | `Meant to stop a broadcast echoing between peers, but the hash includes a fresh id and timestamp, so a resubmission never matches; VLA-16 hashes the signed fields` |
| `submit_transaction.py:65` | Check if sender has enough balance | Remove | |
| `submit_transaction.py:74` | Read the peers now: broadcast_transaction runs after the response, … | Keep | |
| `submit_transaction.py:89` | We do not pass auth tokens for P2P sync in this MVP, | Rewrite (decision 2) | `Peers require a JWT this call does not send, so the broadcast fails between authenticated nodes until VLA-19 adds a peer token` |
| `submit_transaction.py:90–96` | but if the remote node requires it, it might fail. … Wait, our /transactions requires auth! … but we didn't. (7 lines) | Remove | Replaced by the line above |
| `use_cases/network/resolve_conflicts.py:15` | Docstring: Polls all registered peers, finds the longest valid chain, and replaces ours if needed. Returns True if our chain was replaced. | Keep | States the return value |
| `resolve_conflicts.py:40` | We found a longer valid chain. Replace ours. | Remove | |
| `resolve_conflicts.py:47` | Docstring: Validate the new chain hashes and proof of work. For MVP, we just do a simple structural check. | Rewrite | `Only checks that the blocks link up. SPEC › Valid chain lists the full rules, which VLA-18 implements.` |
| `resolve_conflicts.py:56` | Verify previous hash (Note: assuming chain is ordered oldest to newest, wait, our get_all returns newest first) | Rewrite | `/blocks/full lists newest first, so each block's previous_hash must be the next item's block_hash` |
| `resolve_conflicts.py:57` | Actually get_all_blocks returns offset ordered by DESC. So items[0] is the NEWEST block. | Remove | Merged into line 56 |
| `resolve_conflicts.py:58` | So items[i] should have previous_hash == items[i+1].block_hash | Remove | Merged into line 56 |

### domain

| Where | Now | Action | Proposed |
| --- | --- | --- | --- |
| `ports/services/consensus.py:9` | Docstring: Mines a block using Proof of Work. Returns: tuple[int, str]: … (nonce, block_hash) | Keep | What the tuple holds |
| `ports/services/security.py:22` | Docstring: Returns the payload if valid, raises exception otherwise | Rewrite | `Returns the token's claims; raises ValueError if the token is invalid or expired.` (what `JWTTokenService` raises and `get_current_user` catches) |
| `ports/services/wallet.py:7` | Docstring: Generates a new key pair. Returns: tuple[str, str]: (public_key_hex, private_key_hex) | Keep | The order of the pair |
| `signed_message.py:4–5` | Exactly 8 decimals and no leading zeros, so an amount has one spelling; … (ADR-0004) | Keep | |
| `signed_message.py:12` | Docstring: The canonical message a transaction's signature covers (ADR-0004); … | Keep | |
| `signed_message.py:14` | fullmatch: with match, "$" would also accept a trailing newline | Keep | |

### infrastructure

| Where | Now | Action | Proposed |
| --- | --- | --- | --- |
| `consensus/pow_service.py:15` | We use the hasher service to calculate the hash for the current nonce | Remove | |
| `database.py:22` | One transaction per request: if the endpoint raises, the commit is skipped … | Keep | |
| `repositories/block_repository_impl.py:72` | 1. Delete all blocks (this will set block_id to NULL for txs if no cascade, so we delete txs too) | Rewrite | `Confirmed transactions belong to the blocks being replaced; pending ones stay in the mempool` |
| `block_repository_impl.py:78` | 2. Re-insert the new chain | Remove | |
| `block_repository_impl.py:79–80` | Note: We process them from oldest to newest if the list is newest first, wait. Usually list from /blocks is newest first (desc). … | Remove | The insertion order does not matter within one flush |
| `repositories/transaction_repository_impl.py:71` | Received amounts (where status is CONFIRMED) | Remove | |
| `transaction_repository_impl.py:79` | Sent amounts + fees (where status is PENDING or CONFIRMED to avoid double spend in mempool) | Keep | Why pending sends count |
| `security/ed25519_service.py:36` | Hex decoding errors or verification failure | Keep | Where the caught `ValueError` comes from |
| `security/sha256_hasher.py:11` | Create a deterministic dictionary representing the transaction | Remove | |
| `sha256_hasher.py:21` | Dump to JSON with sorted keys to ensure determinism | Keep | |

### presentation

| Where | Now | Action | Proposed |
| --- | --- | --- | --- |
| `api/block_router.py:26` | A block read from the database always has its hash; … | Keep | |
| `block_router.py:56` | Simplified total for now | Rewrite (decision 3) | `Counts this page, not the chain; VLA-20 returns the real row count` |
| `block_router.py:130` | Background tasks run after the response, so peers only hear of the block once it is committed | Keep | |
| `api/transaction_router.py:36` | Background tasks run after the response, … | Keep | |
| `api/wallet_router.py:15` | Docstring: Utility endpoint for testing. … The private key should ideally never leave the client's device, but we provide this for testing purposes. | Rewrite | `Development helper. The private key travels over the network, so production answers 404 (VLA-21) and the webapp generates keys in the browser (VLW-16).` |
| `dependencies/database.py:8–10` | scope="function" closes the session, and so commits, before the response is sent; … | Keep | |

### cli and core

| Where | Now | Action | Proposed |
| --- | --- | --- | --- |
| `cli/seed.py:23` | Check if admin exists | Remove | |
| `core/config.py:9` | Override in production | Rewrite | `Development default; VLA-21 makes production refuse it` |

### tests

All 34 comments in `backend/tests` are kept except three in `unit/application/use_cases/network/test_resolve_conflicts.py`, which restate the mock on the next line:

| Where | Now | Action |
| --- | --- | --- |
| `test_resolve_conflicts.py:27` | Our chain has length 5 | Remove |
| `test_resolve_conflicts.py:30` | Remote chain has length 3, so we won't replace | Keep: why the result is False |
| `test_resolve_conflicts.py:47` | Our chain has length 5 | Remove |
| `test_resolve_conflicts.py:50` | Remote chain has length 10 | Remove |

The 30 others say why and stay: the architecture tests (11), the integration tests (9), `test_mine_block.py` (2: what the count of 2 is, and why `execute` only reads the peers), `test_submit_transaction.py` (1), `test_settings.py` (1), `test_block_repository_impl.py` (3), `test_database.py` (2) and `test_signing_vectors.py` (1).

## How this inventory was made

A script read every `.py` file under `backend/app` and `backend/tests` with Python's `tokenize` (so a `#` inside a string is not a comment) and `ast` (for docstrings), and skipped pragmas; it is in the PR description. Run again after the cleanup, it lists 66 comment lines: the 64 entries kept or rewritten here, two of whose rewrites (`submit_transaction.py`, decisions 1 and 2) take two lines to stay within 120 columns.

## Cleanup plan, once approved

On `chore/comment-cleanup`, one commit per module (application, domain, infrastructure, presentation, cli and core, tests), with Ruff, Mypy strict, `lint-imports` and the tests run after each.
