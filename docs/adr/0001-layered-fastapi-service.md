# ADR-0001: One FastAPI service in five layers with ports in the domain

- **Status:** Accepted (retroactive)
- **Date:** 2026-07-28, written down on 2026-10-20
- **Related:** SPEC.md › Architecture; ARCHITECTURE_RULES.md AR-01 to AR-05; commit `dc450f3`

## Context

VeriLedger is maintained by one person and is meant to be read: the README promises "Clean Architecture and Domain-Driven Design". The ledger has a few concepts (users, transactions, blocks, peers) and several technical concerns that should be swappable or testable alone: the database, the signature scheme, the hash, the consensus and the HTTP calls to peers.

## Options

1. **A flat FastAPI app** (routers that talk to SQLAlchemy). Least code, but every rule of the ledger would be tested through HTTP and a database.
2. **Several services** (ledger, network, identity). Far more operations than one person and one demo need.
3. **One service in layers,** with the domain defining ports (abstract classes) that the infrastructure implements.

## Decision

Option 3, with five layers under `backend/app`: `core`, `domain`, `application`, `infrastructure`, `presentation`.

- `domain` holds entities as `dataclasses` and ports as `abc.ABC` (repositories and services: hashing, signature, wallet, consensus, security). It imports only the standard library.
- `application` holds one use case per file with an `execute` method, and the Pydantic DTOs. Use cases receive their ports in the constructor.
- `infrastructure` implements the ports: SQLAlchemy models and repositories, `SHA256HasherImpl`, `Ed25519ServiceImpl`, `ProofOfWorkServiceImpl`, `JWTTokenService`, `PasswordHasherImpl`.
- `presentation` wires implementations into use cases inside each router and maps `ValueError` to HTTP errors.

## Consequences

- Use cases are unit-tested with mocks of the ports, without a database (17 unit tests on 2026-10-20).
- The wiring is repeated in every router; a composition root in `presentation/dependencies` would remove the repetition (proposed rule in ARCHITECTURE_RULES.md, not adopted).
- **What the code does differently today** (audit 2026-10-20): three use cases import `httpx` to call peers, and the seed in `infrastructure` imports a use case. VLA-19 adds a `PeerClient` port and VLA-13 moves the seed to `backend/app/cli/`; AR-02 and AR-03 check both.
- "Domain-Driven Design" in the README is not a verifiable claim: there are no aggregates or bounded contexts beyond the folders of `use_cases`. ARCHITECTURE_RULES.md proposes how to make it concrete or drop it.
