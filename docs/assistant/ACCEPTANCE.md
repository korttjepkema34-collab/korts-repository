# Verification and implementation status

No checklist below is a substitute for running the actual machine/provider tests.

## Implemented in this branch

- Free-cloud-only route validation and explicit no-local-leader behavior.
- OpenRouter live model-price check, model alias pinning, persisted invocation budget.
- Claude Code cloud adapter and explicit qualification command.
- Persistent task state/events, dependency validation, bounded workers, cloud critique/repair.
- Private Markdown vault, status/provenance-aware FTS retrieval, task-pinned project/subproject
  boundaries, source hashes and read-only memory MCP.
- Editable worker definitions, draft artifacts and source/check evidence for isolated code candidates.
- Initial desktop interface, setup/start/test scripts, pull-only Git sync and morning reports.
- Legacy setup migration notices and disabled unsafe-for-current-policy unattended entry point.

## Required offline checks

Run `python -m unittest discover -s tests/assistant -v` and `python -m compileall -q assistant`.
The tests cover scope isolation/deletion, persistence, budgets, paid/local-leader rejection, malformed
plans/reviews, cloud outages, tampered artifacts, repair caps, code paths/checks and MCP scope.
Run the existing `pytest tests` after installing its separate requirements to detect regressions.
Record actual results in `VERIFICATION.md`; do not infer success from code inspection.

## Live core qualification — must happen on the PCs

- [ ] Version inventory, free disk and GPU driver recorded.
- [ ] Local 4B/9B requests measured; context fits and latency is useful.
- [ ] Tailscale + SSH forwarding survives normal reconnect; gaming pause works.
- [ ] Claude Code uses the intended free cloud route, all aliases and account activity checked.
- [ ] Cloud qualification report reviewed, including rejection of bad worker output.
- [ ] Corrected output passes cloud review; no missing evidence silently accepted.
- [ ] Server vault opens in Obsidian; scoped retrieval and memory MCP queried live.
- [ ] UI loads and its add/status/search/pause/report controls work on Windows.
- [ ] One real Godot candidate passes actual configured checks and visible behavior review.
- [ ] One business candidate passes the real project's tests in an isolated workspace.
- [ ] Interrupted runner resumes without losing results or becoming a local-led agent.
- [ ] Backup/restore reproduces a note, task and artifact.
- [ ] Overnight schedule, reboot/login, deadline and report inspected on the server.

## Explicit implementation gaps before the full requested system is complete

- [ ] Connect native image/sprite/audio adapters to this controller with actual artifact transport.
- [ ] Add actual screenshot/image/audio input to qualified cloud review where the task requires it.
- [ ] Shared GPU leases across LLM/media/game jobs, with health checks and crash recovery.
- [ ] Concurrent cloud planning and independent local work with ownership/dependency tests.
- [ ] Rich streaming chat, inline profile editor and artifact previews in the custom UI.
- [ ] Adaptive repository context/tool loop beyond fixed configured code input files.
- [ ] Cross-project PR creation/integration and combined tests behind explicit authority boundaries.
- [ ] Automated lessons/skill proposal review and versioned promotion UI.
- [ ] Qualify each business service connector and intended action.
- [ ] Long-run tests for hours of mixed real tasks, not only a simulated pipeline.

Current media profiles intentionally block. Current draft_ready means deliverables are prepared;
verified_candidate means configured checks and cloud review passed on that isolated candidate.
Neither label means published, fully integrated, or that every possible test was performed.

## Additional confirmed requirements (2026-09-09)

- [x] Free OpenRouter inventory, dated synthetic evaluation cards and opt-in evidence-gated route ordering.
- [ ] Task-specific capability benchmarks and live model qualification.
- [ ] Automatic qualified cloud switching with persistent handoff and actual-model audit trail.
- [x] Bounded cloud execution adapters (`cloud-code` and `cloud-draft`) implemented; live task/model qualification remains required. See CLOUD-WORKERS-REVIEW.md.
- [ ] General / side projects UI label and per-subproject context boundaries in all sections.
- [ ] Business finance/tax cloud-backed role and connected, verified calculation/source tools.
- [ ] Tool-aware skill assignment and evaluated memory-to-skill promotion.

Requirements: REQUIREMENTS.md. Routing design: OPENROUTER-ROUTING.md. Authored skills: SKILLS.md.

## Live Workforce delivery gates

Planning approved; no boxes below imply the office already exists.

- [ ] Stage B: labeled simulator, approved office style, walking/handoff, all key states, accessible details and narrow viewport verified without inference.
- [ ] Stage C: real `assistant/` transitions, scoped sanitized snapshots/events, ordering, restart/reconnect, stale evidence, bounded clients and failure isolation verified.
- [ ] Stage C: private gateway access and origin/session rules verified before real private data is exposed; mutations disabled.
- [ ] Stage C: gateway/browser CPU and RAM measured separately; comparable inference runs with office off/on recorded. Handoff budgets are targets, not results.
- [ ] Stage D: cloud/local overlap and exclusive GPU leases verified, including gaming, crash recovery, unload confirmation and duplicate-effect prevention.
- [ ] Stage E: controller-mediated authenticated commands, acknowledgments, permissions and audit verified.

Review each stage before starting the next. SQLite remains the first display source; legacy Redis integration is superseded for this feature. See LIVE-WORKFORCE-HANDOFF.md and WORKFORCE-PLAN.md.

## Approved studio authority implementation gates

Policy approved: [authority index](authority/README.md). Documentation approval does not close these gates.

- [x] Enforce knowledge status/provenance and per-subproject access boundaries. Offline tests cover
  sibling exclusion, path-owned scope, MCP pinning, task persistence and legacy database migration;
  actual Windows/Obsidian operation remains part of the live qualification checklist.
- [ ] Implement conflict-safe rule adoption and task revision pinning.
- [ ] Implement persistent private mailbox and revision-bound responses with duplicate-effect prevention.
- [ ] Generate scoped Obsidian reports and owner-only navigation from authoritative state.
- [ ] Enforce independent review and bounded repairs across model changes.
- [ ] Verify actual Windows vault operation and backup restore.

The early office simulator was accepted as a demo and privately published separately. It does not satisfy all Stage B animation requirements. Further office development is deferred in issue #2; real runtime integration is still pending.
