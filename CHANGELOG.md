# Changelog

Every notable change to the VeriLedger API. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Story ids (VLA-NN) point to [docs/BACKLOG.md](docs/BACKLOG.md).

## [Unreleased]

## [1.0.0] - 2026-10-21

### Added

- **Signed transactions.**
  - Signatures cover one canonical message, shared with the webapp, with golden vectors in `docs/signing-vectors.json`. Amounts travel as 8-decimal strings (VLA-15, ADR-0004).
  - A nonce per sender: a used or skipped nonce answers 409, and a byte-identical replay answers the stored transaction (VLA-16).
- **The reads the webapp's views need:**
  - a block by hash, with its transactions' hashes;
  - a transaction by hash, with its block;
  - the mempool, and an address's activity.

  They are public, and every page holds at most 100 items (VLA-20, VLA-33, VLA-34, VLA-36, ADR-0006).
- **One-click demo accounts.** 24-hour traders named `Guest XXXX`, a cleanup command, and limits per address, on active accounts and on mining (VLA-35, ADR-0006).
- **Peers** call each other through a port, with a shared `PEER_TOKEN`, and only at public addresses unless `ALLOW_PRIVATE_PEERS` is set (VLA-19).
- **Chain validation.** A peer's chain is adopted only when every block and every transaction in it is valid (VLA-18).
- **`docs/openapi.json`,** generated, and checked for staleness in CI (VLA-37).
- **Images and stacks:**
  - a reproducible, non-root image published to GHCR for amd64 and arm64 (VLA-22);
  - `docker compose up` migrates, seeds the admin, then starts (VLA-23);
  - `docker-compose.ghcr.yml` runs the published image (VLA-38).
- **Deployment, prepared and rehearsed without a server:** Caddy in front of the webapp and the API on one hostname, with runbooks for deploying, backing up and restoring, and rotating secrets. CI rehearses them on every pull request (VLA-27, VLA-28).
- **Readiness and logs.** `/health` reports the database and answers 503 without it; every request gets an id, and production logs are JSON (VLA-26).
- **Abuse limits** on sign-ins, on transactions per sender, and one mining request at a time (VLA-29).
- **CI** blocks a pull request on lint, format, types, the architecture rules, the tests on PostgreSQL, the image, Compose, and the rehearsal (VLA-10, VLA-12, VLA-13, VLA-25).

### Changed

- **One database transaction per request,** committed before the response; broadcasts run after it (VLA-32, ADR-0007).
- **Mining.**
  - It is atomic, and a height already taken answers 409.
  - The Proof of Work runs in a worker thread, and `MINING_DIFFICULTY` and `MINING_REWARD` are settings (VLA-17, ADR-0008).
- **Roles.** Mining needs the trader or admin role, and managing peers needs the admin role (VLA-19).
- **Platform.** Python is pinned to 3.12.13, and PostgreSQL 16 is used everywhere.

### Fixed

- `POST /users` saves the user (VLA-32).
- **Adopting a peer's chain:**
  - it read only one page of 100 blocks;
  - it broke on pending copies of the transactions it held;
  - it lost their payloads and nonces (VLA-19, VLA-18).
- **The database** refuses a negative amount or fee, and the migrations go down without leaving an enum behind (VLA-25).

### Security

- **Production refuses unsafe settings:** a missing, example or short `SECRET_KEY`, and an empty or development admin password. Browser origins come from `CORS_ORIGINS` (VLA-21, VLA-24).
- `POST /wallets/generate`, whose private key would cross the network, answers 404 outside development (VLA-21).

## [0.1.0] - 2026-07-29

### Added

- **The baseline:**
  - a FastAPI service in layers, with users and roles;
  - Ed25519 transfers and notarizations;
  - Proof-of-Work mining, with rewards and fees;
  - peers, and longest-chain resolution (VLA-01 to VLA-08).

[Unreleased]: https://github.com/Alesso2805/veriledger-api/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Alesso2805/veriledger-api/releases/tag/v1.0.0
