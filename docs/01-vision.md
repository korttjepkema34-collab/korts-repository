# 01 - Vision

## The pitch

**Reaper's Relics**: a 2.5D pixel-art online RPG. By day you scavenge and build; by night the Wired come in their hundreds. Design in `docs/10-game-design.md`, world in `docs/14-world-bible.md`.

Run a game studio where the staff are AI models. One orchestrator acts as studio lead and has a
handful of specialised workers under it, each possibly a different model, each with access to the
right generative tool for its job. The studio builds a game in Godot 4 with the human owner as
creative director and final QA.

## Why it is doable now

- Open-weight LLMs are good enough at planning, GDScript, and tool calling to act as workers.
- Godot MCP servers expose the editor and runtime to an agent (create scenes, edit scripts, run
  the game, read debug output). No copy-pasting from chat.
- Open image and audio generators (SDXL/FLUX, ACE-Step, Stable Audio Open) all run on a 12 GB
  consumer GPU and export formats Godot imports natively.
- Multi-agent orchestration is a well-understood pattern: planner, workers, reviewer, shared
  task board, shared memory.

## Where it is hard (be honest about these)

1. **Animation.** 2D sprite-sheet animation from diffusion models is inconsistent frame to
   frame. Mitigate with a fixed character reference sheet, a small frame count, and the reviewer
   comparing frames.
2. **Consistency.** Five workers produce five art styles unless every prompt carries the same
   style bible and reference images, and a reviewer rejects drift.
3. **VRAM.** 12 GB means one generative model resident at a time. Jobs are serialised.
4. **Stale Godot knowledge.** Smaller models write Godot 3 GDScript for Godot 4 projects. The MCP
   server helps because the agent can run the code and see the error.
5. **Licences.** Some generators are research-only or have revenue caps. Track them per asset.

## Milestones

| # | Milestone | Proves |
|---|---|---|
| 0 | Scaffold (this repo) | Shared understanding, queue, worker loop, role definitions |
| 1 | Server stack up, worker pulls a stub job over Tailscale | The two machines cooperate |
| 2 | Orchestrator turns a task file into jobs; coder creates a scene via Godot MCP | Planning + code loop |
| 3 | 2D artist generates a sprite that passes the reviewer and lands in `assets/approved/` | Art loop with QA |
| 4 | Playable prototype per docs/10-game-design.md: the Keep, the Fallows, the Undercroft, hordes, a Hold, the Castellan, two players on a dedicated server | End-to-end, including netcode and the lighting layer |
| 5 | Add audio worker and 2D animation pipeline | Full team |

Start with **three workers** (orchestrator, coder, 2D artist). Add audio once milestone 4 is
reached. Do not try to run all five on day one.
