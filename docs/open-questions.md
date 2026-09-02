# Open questions

Nothing here blocks the studio. It runs unattended and makes conservative choices on its own
(`docs/12-autonomy.md`). This file is for the owner to read on return. Deferred tasks in
`tasks/deferred/` are the more urgent list.

## Owner may want to override on return

- [ ] The world and style the scaffold chose for you: `docs/14-world-bible.md` and
      `style/style-bible.md`. Change anything before the first run; after that, changes mean
      regenerating approved art.
- [ ] Style choices the orchestrator made automatically during the run: "(auto)" lines in
      `docs/decisions.md`.
- [ ] Godot MCP choice for interactive sessions (docs/11-godot-mcp-options.md). Not needed for
      unattended runs.
- [ ] Buy the RTX 3060 12 GB for the server now or after milestone 4?

## Needs verifying (setup time, see docs/13-before-you-walk-away.md)

- [ ] Exact Ollama tags for the Qwen MoE, Qwen3-Coder, Qwen3-VL and gpt-oss picks.
- [ ] Whether the vision reviewer model handles 4 candidate images plus 2 references in one call
      on CPU in reasonable time. If not, lower to 2 candidates in `reviewer.py`.
- [ ] Stable Audio Open version and licence.
- [ ] Server case clearance and PSU headroom for a full-size GPU.

## Not started

- [ ] Audio review (currently auto-approved on existence).
- [ ] Audio API wrapper (`worker/services/`).
- [ ] Nakama compose entry for scope rung 2.
- [ ] Dedicated game server launch as a service on the Windows server.
- [ ] Dashboard.
