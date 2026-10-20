# ADR-0006: Demo access with public reads and one-click temporary accounts

- **Status:** Accepted on 2026-10-20 (product owner)
- **Date:** 2026-10-20
- **Related:** VLA-35, VLA-36, VLA-29, VLA-19, VLA-24; ARCHITECTURE_RULES.md AR-08, AR-09; webapp VLW-34 and its DESIGN.md › Login and Shell

## Context

The public demo (VLA-27) has no way in for a visitor. Only an admin can create users (`POST /users`), and on 2026-10-20 that endpoint was found to save nothing (VLA-32). The audit already blocks sharing the admin password.

Most visitors come from a portfolio and stay a few minutes. Every extra step loses them.

## Options

1. **Admin-made accounts only.** No work, but someone must hand out credentials. A shared trader account lets anyone change the demo for everyone.
2. **Open sign-up** with email and password. Familiar, but it is friction for a two-minute visit, invites bots, and verifies nothing: there is no mail server in the plan.
3. **Public reads plus a shared trader account** shown on the login page. Little work; the shared account is still everyone's.
4. **Public reads plus one-click temporary accounts:** "Try the demo" creates an account with the trader role, no email, valid for 24 hours.

## Decision

Option 4.

- **Public reads (VLA-36).** Reading endpoints no longer need a token:
  - `GET /blocks`, `/blocks/full` and `/blocks/{block_hash}`;
  - `GET /transactions/{tx_hash}` and `/transactions?status=PENDING`;
  - `GET /nodes`.

  Every write still needs a token and the roles of SPEC › Permissions. AR-08's public list changes in the same PR as the code.
- **Demo accounts (VLA-35).** `POST /auth/demo` creates a user with:
  - the `trader` role;
  - a generated display name (`Guest 4F2A`);
  - no email or password;
  - an `expires_at` 24 hours ahead.

  It answers with a JWT that also expires then. Any request with an expired demo account answers 401.
- **What expiring means.** The demo account is deleted after 24 h by a scheduled `cli` command, the same in every environment. What it recorded on the chain stays: confirmed transactions and blocks are immutable, like on any ledger. Its wallet keys never were on the server (webapp ADR-0002).
- **Only in demo deployments.** `DEMO_MODE=true` enables the endpoint; elsewhere it answers 404.
- **Abuse limits** (with VLA-29):
  - 5 demo accounts per hour per IP;
  - at most 500 active demo accounts;
  - 10 mining requests per hour per demo account;
  - the existing per-sender transaction limit.

  Each answers 429 with a message the webapp shows.

## Consequences

- A visitor sees the tower without an account and mines or sends after one click.
- The demo chain only grows. If it ever becomes unwieldy, the operator can reset it with a runbook step (VLA-28): a fresh database and seed. That would also drop real accounts' data, so it is a deliberate operation, not automatic.
- Users gain an `expires_at` column and a nullable email; tests cover expired tokens, the 404 without `DEMO_MODE`, and each 429.
- Public reads widen what an anonymous client can fetch. Pagination limits (`limit ≤ 100`) and the rate limits protect the node.
