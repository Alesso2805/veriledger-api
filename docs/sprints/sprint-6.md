# Sprint 6 — The repository ready to be public (VLA-39)

**Status as of 2026-10-22:** planned for January 4 – 17, 2027; it starts early. 2 points. Sprint 5 had no API stories: the webapp moved to design C, in English and Spanish and in light and dark themes, on this API as it is.

**Why this sprint exists** (product owner, 2026-10-22). Both repositories are to be presented as Willay's is: a README for visitors, a license, a security policy, and only what a visitor needs in version control.

**The webapp's counterpart:** VLW-49, the same story for `veriledger-webapp`, and VLW-26, its 1.0.0 with screenshots of design C from the deployed instance.

## What was delivered

| Story | PRs | Result | Verification |
| --- | --- | --- | --- |
| VLA-39 | this PR | The repository ready to be public, as Willay's is (its VIG-45). It adds an MIT license, and a `SECURITY.md` with GitHub's private vulnerability reporting, now turned on. The README is for visitors: the live demo, `/api/docs` and `/api/health`, highlights, the audit's result, tests and CI, then how to run and develop it as before. `CLAUDE.md`, `.claude/`, `docs/AUDIT.md` and `docs/COMMENTS_REVIEW.md` are out of version control. The repository has a description, a website and topics, and no wiki. VLA-27 is marked done: live since 2026-10-22 | GitHub shows the license, the security policy and the About box; the README's links open; `git ls-files` no longer lists the four local files |

## Sprint decisions

- **The repository was already public** (found on 2026-10-22). Its history was searched for secrets. GitHub's scanning had no open alert. A search for passwords, keys and tokens found only test vectors, CI values and the development admin password, which the seed refuses in production (VLA-24). Taking the internal files out of version control hides them from now on; their history stays.
- **Other clones lose `CLAUDE.md` on their next pull,** because the pulled commit deletes it from the index. `git show 80d9cdb^:CLAUDE.md > CLAUDE.md` gets it back, and the same works for the two internal notes.

## Changes to the specification in this sprint

- The repository's tree: `LICENSE` and `SECURITY.md`; the agent's instructions and the internal notes stay local (VLA-39).

## Retro

- **Went well:** —
- **To improve:** —
- **To try:** —
