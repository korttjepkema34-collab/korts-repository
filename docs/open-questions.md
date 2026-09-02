# Open questions

Things that need the human's decision or that nobody has verified yet. Remove lines when
resolved and add the outcome to `decisions.md`.

## Needs the human

- [ ] **What game are we making?** Genre, 2D or 3D, art style. The style bible is a template
      until this is answered. Suggest starting 2D pixel-art: cheapest to generate, easiest to
      keep consistent, and the 3D/animation workers are the weakest anyway.
- [ ] Server OS: Linux + Docker assumed. Confirm.
- [ ] Gaming PC OS: Windows assumed. Confirm.
- [ ] Which Godot MCP server to standardise on (open-source GDAI / godot-ai vs commercial).
- [ ] Is a small monthly spend on a paid API for escalation acceptable, or strictly free only?
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
- [ ] Headless Godot test container.
- [ ] Dashboard.
