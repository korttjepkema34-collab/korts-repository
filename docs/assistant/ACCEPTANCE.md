# Verification and implementation status

No checklist below is a substitute for running the actual machine/provider tests.

## Implemented in this branch

- Free-cloud-only route validation and explicit no-local-leader behavior.
- OpenRouter live model-price check, model alias pinning, persisted invocation budget.
- Claude Code cloud adapter and explicit qualification command.
- Persistent task state/events, dependency validation, bounded workers, cloud critique/repair.
- Private Markdown vault, project-scoped FTS retrieval, source hashes, read-only memory MCP.
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
