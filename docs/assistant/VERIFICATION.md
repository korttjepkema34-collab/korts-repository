# Verification record — 2026-09-09

## Observed in the repository workspace

- `python -m unittest discover -s tests/assistant -v`: **33 passed**.
- `python -m pytest tests -q`: **47 passed**, including the existing studio tests. One existing
  Pillow `getdata` deprecation warning in `tests/test_validators.py`; no failures.
- `python -m compileall -q assistant`: passed.
- All new JSON configuration templates parsed successfully.
- Real CLI smoke run in a temporary private runtime: initialize, index seeded game bibles,
  retrieve Keep references, create personal task, run once with cloud sharing disabled,
  inspect the correctly blocked task, generate a report. All commands exited successfully.
- Real temporary Git repositories exercised clone isolation, removal of publication remote,
  scoped file replacement, actual passing and failing subprocess checks, and rejection of
  staged/unstaged changes made after test evidence was recorded.
- Memory MCP dispatch exercised initialization, read-only discovery/call behavior, and fixed
  project scope. This is an offline protocol test, not a real Claude Code MCP session.
- Cloud/worker integration tests use controlled responses. They exercise repair/review/outage
  behavior, but are not model quality benchmarks.

## Not verified here

No authenticated home-PC connection, provider keys, live Claude Code route, Ollama daemon, GPU,
Godot installation or business project was available. No model was downloaded or benchmarked on
the user's PCs. Tkinter imports here, but no graphical display/Windows runtime was available;
the desktop UI and PowerShell scripts require the live checks in `ACCEPTANCE.md`.

The full overnight multimedia workflow is not complete. Native media adapters, modality-aware
cloud review and other outstanding implementation are itemized in `ACCEPTANCE.md`. Do not treat
passing unit tests as evidence that these absent integrations work.

Required next gate: follow `SETUP.md`, qualify a free cloud route, then run one real bounded task
on the two PCs and inspect its artifact, actual test evidence, cloud review and morning report.

## OpenRouter discovery/evaluation update — 2026-09-09

Full repository suite: **58 passed**, one existing Pillow deprecation warning. Eleven new catalog
checks cover pricing filters, unsupported IDs, cache freshness, failed refresh, removal, evaluation
artifacts, qualification/fingerprint/expiry gates and adapter integration. Python compilation passed.
A real catalog fetch returned 21 zero-priced entries, 18 explicit supported `:free` IDs. Counts are
an observation, not a permanent inventory. No live inference evaluation was run: this environment
has no configured home Claude Code/OpenRouter credentials. Synthetic test fixtures validate the
pipeline; they do not establish any actual model's quality. Use the documented server evaluation
command before enabling catalog routing.

## Knowledge status and subproject isolation candidate — 2026-09-10

- `python -m unittest discover -s tests/assistant -v`: **68 passed**.
- `python -m pytest tests -q`: **82 passed** with the same existing Pillow deprecation warning.
- `python -m compileall -q assistant`: passed; `git diff --check`: passed.
- A clean temporary runtime completed initialization, a task created with the persisted
  `reapers-relics` subproject, a subproject-pinned search and status inspection.
- New checks cover knowledge status/provenance, approved-first ordering, hidden superseded history,
  path-owned scope conflicts, sibling exclusion, task restart persistence, old database migration,
  MCP process pinning and end-to-end cloud/worker prompt isolation.

These are local Linux/offline results on the review branch. Windows, the real private Obsidian
vault and a live Claude Code MCP session remain unverified. This slice does not implement controlled
rule adoption, knowledge promotion or the persistent owner mailbox.
