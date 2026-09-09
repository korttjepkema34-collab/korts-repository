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
