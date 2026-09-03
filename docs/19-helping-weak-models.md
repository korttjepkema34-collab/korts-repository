# 19 - Helping weaker models do a better job

What was done, in priority order, so a small local model can ship. Each item is live in the repo.

| # | Problem weak models have | What the repo does about it |
|---|---|---|
| 1 | Hallucinated Godot APIs | `search_godot_api` coder tool over the installed engine's own class reference (`scripts/dump_godot_docs`, `server/orchestrator/docsearch.py`). Exact version, no network. |
| 2 | Cannot write tile map / TileSet scene text | Convention: build tile sets and maps from code and JSON. Snippets in `docs/18-godot4-cookbook.md`. |
| 3 | Bad starts from an empty project | Skeleton written: `Config`, `Net`, `Clock` autoloads, server/client/solo split, two tests. Task 003 verifies instead of creates. |
| 4 | Palette and size drift in art | Worker `postprocess.py` quantizes to the 16 colours, downsamples, cuts backgrounds. Orchestrator `checks.py` auto-rejects off-palette, wrong size, missing transparency before the vision model looks. |
| 5 | Follow examples, not rules | Worked examples in `agents/orchestrator.md` (a full plan) and `agents/reviewer.md` (verdicts). |
| 6 | Fumbled tool calls | Coder accepts a JSON block in plain text as a tool call. |
| 7 | Sloppy GDScript | `gdformat` auto-fix and `gdlint` in the merge gate (gdtoolkit, free). |
| 8 | Godot 3 habits | Pattern scan in the gate; trap list in the cookbook. |
| 9 | Guessing scenes look right | `visual_check` renders the scene and the vision model describes it. |
| 10 | Losing the thread | Everything on disk: task files, state JSON, daily reports, decision log. |

## For interactive Claude Code sessions on this repo

Skills in `.claude/skills/`: `studio-status`, `godot-check`, `asset-review`, `new-task`, `act-as`.
Recommended MCP: a Godot MCP server (`docs/11-godot-mcp-options.md`) for live editor work; set
`GODOT_MCP_CMD` and the coder loop picks it up too. No other connector is needed; everything the
studio uses is local.

## Setup additions (server)

- `pip install -r server/orchestrator/requirements.txt` now includes `pillow` and `gdtoolkit`.
- Run `scripts/dump_godot_docs.ps1` once after installing Godot (and again after upgrading it).
- `pip install -r worker/requirements.txt` on the gaming PC now includes `pillow`.

| 11 | Reviewer changes are felt, not measured | `eval/reviewer/` + `scripts/eval_reviewer.py`: 20 labelled cases, accuracy and misses per run. Replace seeds with real assets over time. |
| 12 | Characters drift between generations | `worker/workflows/character_sheet.json`: pixel-art LoRA + IP-Adapter on the `REFERENCE` image. `tileset.json` for tiles. |
| 13 | Same API mistake three times | Orchestrator tracks failure classes; after 3 in 24 h every code job goes to the escalation model until the class stops recurring. |
| 14 | Flat lighting on sprites | `worker/normalmap.py` writes `<name>.n.png` when a job asks for `postprocess.normal_map`; cookbook shows `CanvasTexture`. |

| 15 | Holistic verdicts are unreliable | Reviewer answers 8 yes/no rubric questions; verdict computed by rule; candidates upscaled nearest-neighbour first |
| 16 | Planner over-thinks mechanics | Asset-type templates fill workflow, sizes, postprocess, references; code jobs get boilerplate acceptance; validation errors go back once (repair loop) |
| 17 | Same mistake next week | `docs/lessons.md` auto-distilled from failure-then-success, fed to the coder |
| 18 | Success claimed from a clean compile | `proof_run` tool and post-merge proof check: replayed input, per-second screenshots, vision judgement |
| 19 | CPU coder too weak | GPU routing to `qwen3.6:27b` on the gaming PC when online, with a VRAM lock the worker respects |
| 20 | Setup is the real blocker | `scripts/bootstrap_server.ps1`, `scripts/bootstrap_gpu.ps1` |

## What would help next (not done)

- Real eval cases from the first week of output, replacing the synthetic seeds.
- A second reviewer pass for animation frames (frame-to-frame consistency), once task 018 exists.
