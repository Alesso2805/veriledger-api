# Security policy

The VeriLedger API is a portfolio project, and its public demo runs a ledger whose coins are worth nothing. Even so, if you find a vulnerability, please report it privately rather than in a public issue or pull request.

## How to report

Use GitHub's private vulnerability reporting: the repository's **Security** tab, then **Report a vulnerability**. Say what you found, how to reproduce it and what an attacker could do with it.

You will get an answer within a week. Fixes go to `main`, and the public demo is redeployed from it.

## In scope

- A transaction accepted without a valid signature of its sender, or accepted twice.
- Coins created or moved outside the rules: a reward without its block, a balance below zero, a fee that is not paid.
- A peer's chain adopted although a block or a transaction in it is invalid.
- Reaching the server's own network through a peer's address.
- Forging or reusing a session token, or acting beyond your role, such as a trader or a visitor using an admin's endpoint.
- A demo account that outlives its 24 hours, or a way around the limits on sign-ins, transactions and mining.
- Secrets in the repository or its history.

## Out of scope

- The demo accounts and the public reads: they are open on purpose.
- The demo's ledger and its coins: they have no value.
- Denial of service against the demo server, and load tests against it.
- Reports from automated scanners without a way to exploit the finding.
- The webapp's own vulnerabilities: report them in [veriledger-webapp](https://github.com/Alesso2805/veriledger-webapp/security).

Please do not access data that is not yours.
