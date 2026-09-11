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

## Persistent runtime, dashboard and operations branch — 2026-09-11

- `python -m unittest discover -s tests/assistant -v`: **126 passed** (Linux sandbox).
- `python scripts/synthetic_e2e.py`: **12/12** checks passed (real runner process; fake Claude Code
  executable and fake Ollama; includes kill -9 recovery and clean-folder restore).
- Headless Chromium render of the dashboard at 1400 px and 390 px with synthetic data: no console errors.
- `python -m compileall -q assistant scripts`, `git diff --check`, `scripts/check_private_leak.py` over all tracked files: passed.
- Not run: legacy `pytest tests` (package index unavailable in the sandbox; legacy code unchanged),
  anything on Windows, Tailscale, real Ollama/OpenRouter/Claude Code, real vault. See OVERNIGHT-2026-09-11.md.

## Integrated Windows runtime and dashboard — 2026-09-11

The overnight runtime was integrated with the existing direct OpenRouter and Windows-safe path
work, then repaired where review found false GPU cancellation and missing required cloud audit
evidence. Current Windows results:

- Assistant unittest suite: **129 passed**, with one symlink-privilege skip.
- Full repository pytest suite: **142 passed**, with one symlink-privilege skip and the existing Pillow
  deprecation warning.
- Synthetic runner/recovery pipeline: **12/12 passed**.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Automated Edge checks at desktop and phone sizes found zero console errors and zero failed
  requests. Preview issued zero write requests; keyboard agent selection, all navigation pages,
  authorized project filtering, contained phone panning and lack of page overflow were verified.
- Desktop office, worker details, preview, tasks, system, inbox, and phone captures were visually
  inspected. Defects found during rendering were fixed and the affected checks repeated.

Detailed scope and corrections: DASHBOARD-IMPLEMENTATION-2026-09-11.md. These are disposable local
runtime results; server nginx/systemd and Tailscale access remain a separate live deployment check.

## Published commit Ubuntu preflight — 2026-09-11

Commit `48a32fa2c346d61818a8b5873da792625b376cb1` was pushed to
`assistant/server-web-integration` and extracted from the server repository into an isolated
temporary Ubuntu directory. The production runtime, systemd units, and nginx configuration were
not used or changed. In that extracted tree:

- Assistant unittest discovery passed **129 tests**, with one expected skip.
- Every extracted file passed `scripts/check_private_leak.py`.
- Python compilation and `sh -n scripts/deploy-dashboard-wsl.sh` passed.
- `scripts/synthetic_e2e.py` passed **12/12** recovery and workflow checks.
- The temporary tree was removed after verification.

The live deployment was deliberately left pending explicit owner authorization. The production
source checkout was restored cleanly to `a95221f`; the existing assistant service remained active,
the new runner remained inactive, and the Tjepkema homepage returned HTTP 200.

## Passwordless live deployment — 2026-09-11

At the owner's explicit request, the Tjepkema deployment was changed to open access as local owner
`kort`. Focused tests proved anonymous reads and owner controls while rejecting mutations with a
missing CSRF token or an unapproved Origin. The complete suite then passed **130 tests** with one
expected skip, and the synthetic workflow passed **12/12**.

The first production probe exposed two live-only deployment defects. `systemctl enable --now` did
not restart the already-active legacy process after its unit changed, and nginx reload retained the
old read-only bind-mounted configuration inode after `install` replaced the host file. The services
were explicitly restarted and only the dashboard nginx container was recreated. The deployment
script now performs those operations itself and validates the replacement nginx file before the
container is recreated.

Observed after repair: both assistant services active; Tjepkema homepage HTTP 200;
`/assistant.html` HTTP 302 to `/assistant/`; dashboard and JavaScript HTTP 200; `/assistant/api/me`
reported signed-in owner `kort`, all three projects, and open access enabled.

A second restart-style check explicitly restarted both systemd services and recreated the dashboard
container. The dashboard again opened without credentials, the runner reported `running` with a
fresh heartbeat, and an authenticated-by-network pause/resume round trip through nginx left the
runtime resumed. The homepage and `/assistant/` both returned HTTP 200 afterward. This check did
not create a task or read, write, or execute any game project file.

The live LAN address returned the reviewed HTML, JavaScript, and API state, but the Codex in-app
browser's separate network sandbox could not reach the LAN address and blocked its localhost
alias. Visual review therefore remains the earlier real-browser desktop and phone render of these
same committed static assets; no claim is made that a new screenshot was captured after install.

The owner's first real Edge visit used `http://127.0.0.1/assistant/` and exposed one additional
proxy boundary: the backend allowed `127.0.0.1:8772` for direct access but not the portless
`Host: 127.0.0.1` forwarded by nginx. The response correctly failed closed with HTTP 421 instead
of serving an unapproved host. The private runtime and deployment script now include the portless
loopback and localhost origins. The exact page, passwordless owner API, and same-origin control
request then returned HTTP 200 through nginx using `Host: 127.0.0.1`.
