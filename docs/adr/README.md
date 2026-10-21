# Architecture Decision Records

One technical decision per file: context, options, decision and consequences. Any decision not covered by [SPEC.md](../SPEC.md) is recorded here with the next free number (`NNNN-title.md`). Decisions the webapp depends on (the signed message, the deployment) are recorded here and referenced from `veriledger-webapp/docs/adr/`.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-layered-fastapi-service.md) | One FastAPI service in five layers with ports in the domain | Accepted (retroactive) |
| [0002](0002-postgres-everywhere-sqlite-for-unit-tests.md) | PostgreSQL wherever the app runs; SQLite only for unit tests | Proposed |
| [0003](0003-ed25519-signatures-and-sha256-proof-of-work.md) | Ed25519 signatures and SHA-256 Proof of Work | Accepted (retroactive) |
| [0004](0004-canonical-signed-message.md) | One canonical signed message, shared with the webapp, with a nonce | Proposed |
| [0005](0005-deploy-on-one-server-behind-caddy.md) | Deploy the API and the webapp on one server, behind Caddy, on one hostname | Proposed |
| [0006](0006-demo-access.md) | Demo access with public reads and one-click temporary accounts | Accepted |
| [0007](0007-one-transaction-per-request.md) | One database transaction per request, committed before the response; broadcasts after it | Accepted |

Statuses: Proposed → Accepted → (Superseded by ADR-NNNN | Deprecated). "Retroactive" means the decision was taken in code on July 28–29, 2026 and written down on October 20, 2026.
