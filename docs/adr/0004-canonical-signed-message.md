# ADR-0004: One canonical signed message, shared with the webapp, with a nonce

- **Status:** Proposed
- **Date:** 2026-10-20
- **Related:** SPEC.md › Signing and hashing contract; ADR-0003; VLA-15, VLA-16; webapp VLW-15, VLW-18 and its ADR-0002

## Context

The API verifies a signature over `json.dumps(fields, sort_keys=True)`; the webapp signs `JSON.stringify` of the same fields with sorted keys. The two strings differ:

```text
Python:     {"amount": 10.0, "fee": 0.0, "receiver_address": "bob", "sender_address": "…"}
JavaScript: {"amount":10,"fee":0,"receiver_address":"bob","sender_address":"…"}
```

Python's default separators add spaces, and it writes `10.0` where JavaScript writes `10`. On 2026-10-20 a transfer signed exactly as `Transaction.tsx` does was rejected by `Ed25519ServiceImpl.verify_signature`, and accepted when verified against the compact string. No transaction made in the webapp can enter the mempool.

The message also has no nonce or timestamp: the server adds `id` and `timestamp` after verifying, so a captured request can be submitted again, and each copy gets a new hash, passes the duplicate check and spends again while the balance allows it.

## Options

1. **Make Python mimic `JSON.stringify`** (`separators=(",", ":")` and integers for whole floats). Fragile: number formatting differs between languages at the edges (exponents, `0.1 + 0.2`), and it couples the contract to two serializers' quirks.
2. **RFC 8785 (JSON Canonicalization Scheme).** A standard, but it needs a library on the Python side and still serializes amounts as IEEE-754 numbers.
3. **A small explicit format:** sorted keys, no whitespace, UTF-8, amounts as decimal strings with exactly 8 decimals, and a per-sender nonce, pinned by golden vectors that both repositories test.

## Decision (proposed)

Option 3.

```json
{"amount":"10.00000000","fee":"0.10000000","nonce":1,"payload":"<hex>","receiver_address":"<hex>","sender_address":"<hex>"}
```

- Keys sorted by code point; no whitespace; `payload` omitted when absent; strings JSON-escaped; the whole message UTF-8 encoded before signing.
- `amount` and `fee` are strings with 8 decimals (the precision of the `numeric(18, 8)` columns), so neither side formats a float.
- `nonce` is an integer, one more than the sender's last accepted nonce; `GET /wallets/{address}/nonce` returns the next one. A reused or skipped nonce answers 409 (VLA-16).
- One function per repository builds the message: `build_signed_message` in the API, `buildSignedMessage` in the webapp's `src/lib/signing.ts`.
- `docs/signing-vectors.json` in this repository holds the vectors (private key, fields, message, signature). The webapp copies the file in its tests; a change to the file is a change to this ADR.
- The transaction hash covers the signed fields plus `signature` (VLA-16), so two different signatures are two transactions and the same signed body is the same transaction.

## Consequences

- Breaking change for any client: the API accepts only the new format from VLA-15, and the nonce from VLA-16. There are no deployed clients yet, so there is no migration.
- Amount strings make the next step to `Decimal` (VLA-31) a local change.
- Chains synced from peers must carry the same fields, which VLA-18 validates.
