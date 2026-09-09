# GitHub and server memory

Correct project: `korttjepkema34-collab/korts-repository`. This repository is public.
The setup branch is `assistant/cloud-led-memory-setup`; use the setup PR for review and integration.
Do not confuse it with the earlier planning document in the business account.

GitHub holds source, setup, public templates and existing game design. The server keeps a local
clone, so it can consult these files offline. The private vault, runtime SQLite, credentials,
customer information, transcripts and generated artifacts stay outside the checkout.

## Start of a future work session

Read `AGENTS.md`, `docs/assistant/DECISIONS.md`, `SETUP.md` and `ACCEPTANCE.md`. Inspect current
private status/report locally. Confirm origin/branch and don't overwrite uncommitted work.
Use the game/world/style bibles for game work. Use a separately authorized checkout for business code.

## Updating

Stop the runner. `python -m assistant.sync` verifies origin, requires a clean checkout, fetches and
fast-forwards the current branch. It does not merge conflicts, change branches, push, or auto-restart.
Run checks and inspect changed instructions before restarting. Keep a record of the last working
commit. If an update fails, preserve logs and return to the known-good version in a separate clone.

## Publishing knowledge deliberately

Private memories are not automatically committed. To publish a reusable skill/procedure later:
review its content, copy only nonprivate material into an explicit repository path, inspect the diff,
commit the named file on a branch, then review the PR. Never use broad auto-add of a private vault.
If private note history in Git is desired, create a separate private destination and verify its
visibility/access before syncing it. This repository is not that destination.

The first earlier planning document remains in its original repository/branch; this setup captures
the confirmed decisions and uses the personal repository going forward. No private source was
copied out of the business repository during this change.
