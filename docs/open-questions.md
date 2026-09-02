# Open questions

Things that need the human's decision or that nobody has verified yet. Remove lines when
resolved and add the outcome to `decisions.md`.

## Needs the human

- [ ] Fill in the style bible palette, character proportions, and mood (game is decided:
      2D pixel-art online RPG, see docs/10-game-design.md). Drop a palette swatch and a mood
      reference in `style/references/`.
- [ ] Confirm the Godot MCP recommendation in docs/11-godot-mcp-options.md (two open-source
      servers side by side) or pick StraySpark (paid).
- [ ] Is a small monthly spend on a paid API for escalation acceptable, or strictly free only?
      See docs/04-models.md "Why not just use a frontier cloud model" for what it changes.
- [ ] Gaming PC OS: Windows assumed. Confirm.
- [ ] Netcode design review before the coder builds it (docs/10-game-design.md).
- [ ] Buy the RTX 3060 12 GB for the server now or after milestone 4?

## Needs verifying

- [ ] Exact Ollama tags for the Qwen MoE, Qwen3-Coder, and Qwen3-VL picks in `docs/04-models.md`.
- [ ] Whether Hunyuan3D's texture stage fits in 12 GB with current optimisations.
- [ ] Which Stable Audio Open version is current and its licence terms for shipped assets.
- [ ] Hunyuan3D Studio's rigging pipeline as an animation option.
- [ ] Server case clearance and PSU headroom for a full-size GPU.

## Not started

- [ ] TRELLIS FastAPI wrapper (`worker/services/trellis_api.py`).
- [ ] ComfyUI workflow JSONs in `worker/workflows/`.
- [ ] Reviewer implementation in the orchestrator (vision call + file move + sidecar update).
- [ ] Coder dispatch: orchestrator launching an agent session against the Godot MCP server.
- [ ] Headless Godot test runner using GODOT_BIN on the Windows server (Linux Dockerfile kept as alternative).
- [ ] Nakama docker-compose entry for scope rung 2.
- [ ] Dashboard.
