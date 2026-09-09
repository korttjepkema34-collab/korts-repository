# Live Workforce implementation handoff

Status: Approved planning direction; implementation has not started.

## Read first

Read `AGENTS.md`, [WORKFORCE-PLAN.md](WORKFORCE-PLAN.md), [UI-DESIGN.md](UI-DESIGN.md), [ACCEPTANCE.md](ACCEPTANCE.md), and [DECISIONS.md](DECISIONS.md). Inspect current `assistant/core.py`, `assistant/run.py`, `assistant/models.py`, `assistant/catalog.py`, and `config/assistant/workers.json` before choosing exact hooks.

This supersedes the owner-supplied older handoff's instructions to build against `server/orchestrator/main.py`, the legacy Redis task queues and `worker/worker.py`. Preserve legacy code as migration material. Do not reactivate it to make a visual demo appear live.

## First implementation scope after authorization

Build Stage B only: a browser office driven by deterministic simulator fixtures. Use the approved pixel-art direction, six initial identities, connected rooms, a fixed waypoint graph, task-carrying animation, detail panel, reduced motion and small-screen layout. Label the whole demo Simulated. Do not call models, run ComfyUI or connect private task state.

Suggested source paths: `ui/live-workforce/` and frontend tests alongside it. Select dependencies after inspecting repository conventions. React/TypeScript with PixiJS is a candidate, not a compulsory framework. Keep rendering separate from state reduction so Canvas 2D remains an option. No Node production server is required by the design.

Fixture sequence: Atlas plans; Forge receives a task, walks, reads, codes and tests; Forge hands off to Judge; Judge rejects once; Forge repairs; Judge accepts; Pixel waits for a simulated GPU slot and generates; Scout researches; Scribe writes; one agent requests user attention; jobs finish. Include simulated gaming, offline and reconnect scenarios. Concurrent activity in fixtures demonstrates future behavior, not implemented concurrency.

Acceptance: browser-visible transitions and handoffs; keyboard-accessible agent details; reduced motion; narrow viewport usability; bounded event/history queues; no model or provider requests; no fabricated actual work. Capture screenshots and document observed failures. Run relevant frontend checks and verify that existing code remains unchanged. Stop for owner review.

## Second implementation scope after Stage B review

Add `assistant/workforce/` with a versioned safe display contract, read-only SQLite projection, gateway and WebSocket delivery. Essential lifecycle state belongs to task persistence; delivery failure cannot stop execution. Add minimum real transitions in `assistant/run.py` and, if needed, transactional event records in `assistant/core.py`. Use existing profile IDs rather than introduce a parallel specialist database.

Do not expose raw task JSON, event detail, prompts, outputs, credentials or private file paths. Allow only bounded safe fields. Scope every snapshot, event and detail response to the selected authorized project. A project selector is not itself authorization. Bind to loopback; use private Tailscale access and verify allowed origins even for read-only WebSockets. Establish trusted session/project access before exposing real private state; never assume Tailscale membership alone grants every project.

Make snapshot/cursor consistency explicit. After a gap, refresh from authoritative state; deduplicate events and distinguish stale evidence from offline machines. Missing instrumentation means unknown, not idle. Real media states stay unavailable until adapters exist. Slow viewers receive resynchronization rather than unbounded buffers.

Run assistant unit tests, full `pytest tests`, compilation and applicable frontend checks. Test sanitization, project isolation, restart/reconnect, cursor ordering, stale evidence, bounded memory and gateway failure isolation. Measure gateway and browser separately, plus inference with the view off/on. Record actual Windows/Tailscale/hardware verification separately from fixtures. Stop for owner review.

## Later work

Stage D supplies shared GPU leases, native media and safe concurrent execution. Stage E supplies authenticated commands and richer configuration. No visual action directly controls a worker. Commands go through controller policy and return acknowledgments. Walking is never a dependency of execution.

Never mark a draft or simulated result deployed. Never activate a candidate model solely because it appears in the catalog. No automatic paid route, local leadership fallback, public hosting or theme/pet editor is included.
