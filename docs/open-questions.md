# Open questions

Nothing here blocks the studio. It runs unattended and makes conservative choices on its own
(`docs/12-autonomy.md`). This file is for the owner to read on return. Deferred tasks in
`tasks/deferred/` are the more urgent list.

## Owner may want to override on return

- [ ] Style choices the orchestrator made automatically during the run: "(auto)" lines in
      `docs/decisions.md`.
- [ ] Godot MCP choice for interactive sessions (docs/11-godot-mcp-options.md). Not needed for
      unattended runs.
- [ ] Buy the RTX 3060 12 GB for the server now or after milestone 4?

## Needs verifying (setup time, see docs/13-before-you-walk-away.md)

- [ ] Confirm `gpt-oss:120b` loads alongside the reviewer within 96 GB; else use `gpt-oss:20b`.
- [ ] Whether the vision reviewer model handles 4 candidate images plus 2 references in one call
      on CPU in reasonable time. If not, lower to 2 candidates in `reviewer.py`.
- [ ] Stable Audio Open version and licence.
- [ ] Server case clearance and PSU headroom for a full-size GPU.

## Training (docs/16-when-you-get-home.md has the checklist)

- [ ] Unsloth on native Windows: does `import unsloth` work in `training\.venv` after `setup.ps1`? If not, WSL2 route.
- [ ] Confirm `unsloth/Qwen3-VL-4B-Instruct` is supported by the installed Unsloth; else keep the Qwen2.5-VL-3B default.
- [ ] Verify the gdquest repo in `training/collect_godot4_code.py` still exists and is MIT; add more MIT Godot 4 repos.
- [ ] Run the coder baseline eval before any fine-tune so `reports/eval-coder.md` has a first row.

## Not started

- [ ] Normal-map generation for sprites and tiles (a ComfyUI workflow or a small script) so 2D lights have direction.
- [ ] Post-process shader (vignette, glow, edge blur) as a reusable `.gdshader`.

- [ ] Audio review (currently auto-approved on existence).
- [ ] Verify `worker/services/audio_api.py` against the installed ACE-Step and stable-audio-tools versions (call signatures drift).
- [ ] Nakama compose entry for scope rung 2.
- [ ] Dedicated game server launch as a service on the Windows server.
- [ ] Dashboard.
