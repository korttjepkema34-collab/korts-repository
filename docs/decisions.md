# Decision log

Append-only. One line per decision, newest at the bottom. Format: date, decision, reason.

| Date | Decision | Reason |
|---|---|---|
| 2026-09-02 | Build an AI game dev team for Godot 4 with one orchestrator and specialised workers | Owner's project goal. Orchestration pattern is mature; asset tools are all locally runnable. |
| 2026-09-02 | Two-machine layout: always-on CPU server is the studio, gaming PC is a pull-based GPU worker | Server has 96 GB RAM but no GPU; gaming PC has the only CUDA card but is not always available. |
| 2026-09-02 | Server never pushes to gaming PC; worker pulls from a Redis queue over Tailscale | Gaming PC is off or in use unpredictably. Pull model means the orchestrator never blocks. |
| 2026-09-02 | Communication over Tailscale only, no public exposure, ACL-restricted | Free, encrypted, stable IPs, already set up. |
| 2026-09-02 | Code in git (Forgejo on server, GitHub mirror), generated binaries in a Syncthing folder | Keeps the repo small; both machines see the same assets. |
| 2026-09-02 | File-based task board in `tasks/` | Readable by humans and every model; git history is the audit trail. |
| 2026-09-02 | Reviewer gates all assets and branches; nothing goes to `approved/` without a verdict | Consistency is the main failure mode of multi-worker generation. |
| 2026-09-02 | Orchestrator must be a mixture-of-experts model while the server is CPU-only | Dense models are 2-3 tok/s on DDR4; MoE ~15-20 tok/s. |
| 2026-09-02 | Buy a 12 GB Nvidia card (RTX 3060 12 GB preferred) for the server; not 6 GB, not Tesla P40 | Enables fast prompt processing via expert offload, a second asset lane, and a resident reviewer. 6 GB too small; P40 aging and losing framework support. |
| 2026-09-02 | Start with 3 workers (orchestrator, coder, 2D artist) plus reviewer; add audio and 3D at milestone 5 | Smaller debugging surface while proving the pipeline. |
| 2026-09-02 | Paid frontier models are escalation-only, via the OpenAI-compatible client config | Keeps the default free; keeps the door open for hard tasks. |
| 2026-09-02 | Model picks: Qwen MoE for orchestrator, Qwen3-Coder for coder, Qwen3-VL for reviewer, SDXL/ComfyUI for 2D, TRELLIS 2 for 3D, ACE-Step + Stable Audio Open for audio | Best free quality per GB with permissive licences. Tags need verifying. See docs/04-models.md. |
| 2026-09-02 | Game: 2D pixel-art online RPG. Story campaign playable solo or co-op on a persistent shared world. Built as a scope ladder (co-op campaign -> persistent world -> MMO) with server-authoritative architecture from day one | Owner's goal is an MMO RPG; the ladder gets there without betting the project on rung 3. See docs/10-game-design.md. |
| 2026-09-02 | Server stays on Windows. Ollama, Syncthing and orchestrator run natively; Redis and Forgejo in Docker Desktop | Native Ollama avoids the WSL2 RAM cap and gets the GPU later; wake-on-LAN and Syncthing host networking do not work from Docker Desktop containers. |
| 2026-09-02 | Godot MCP: Coding-Solo godot-mcp (run + errors) plus GDAI MCP (scene/script editing), both open source, side by side | Together they cover the edit-run-read-error loop for free. StraySpark is the paid upgrade path. Pending owner confirmation. |
| 2026-09-02 | Platform backend for accounts/chat/matchmaking: Nakama (open source, Docker, Godot SDK), introduced at scope rung 2; rung 1 stubs it with JSON saves | Keeps gameplay server and platform services separate so the MMO path is an addition, not a rewrite. |
| 2026-09-02 | Prototype pixel spec: 16x16 tiles, 640x360 base scaled 3x, 4-direction 4-6 frame sprites, modular body + equipment layers | Keeps art volume manageable for an RPG with equipment. |
| 2026-09-02 | Strictly free. No paid API, no escalation spend. Escalation = biggest local model that fits RAM (gpt-oss-120b) | Owner's decision. Unattended runs make slow-but-smart acceptable. |
| 2026-09-02 | Unattended operation is the primary mode: never wait for a human, cap and defer instead of block, self-generate backlog, daily reports and checkpoints | Owner will turn it on and return days later with no input. See docs/12-autonomy.md. |
| 2026-09-02 | Coder runs on the server with file tools and headless Godot, not through the gaming PC's editor/MCP | Code work must continue when the gaming PC is off. MCP stays an option for interactive polishing sessions. |
| 2026-09-02 | Orchestrator may fill style-bible TBDs itself with conventional defaults, logged "(auto)" | No human to ask; conventional choices are reversible. |
| 2026-09-02 | Drop the 3D artist role, model3d job kind and TRELLIS/Hunyuan3D tooling | It is a 2D game. Less to install, less to go wrong unattended. |
| 2026-09-02 | Coder gets eyes: windowed screenshots judged by the vision model, plus optional Godot MCP editor tools, all on the server using its Intel UHD iGPU | File tools stay as the always-available base; editor/render tools are additive. Corrects an earlier over-cautious file-only design. |
| 2026-09-02 | World: "Hollowmere", a drowned valley kingdom; hub Saltreach; first quest "Bring Up the Bell"; tone warm melancholy. Full world bible in docs/14-world-bible.md | Unattended runs need fixed creative constraints or output drifts. Made by the scaffold author on the owner's behalf; reversible. |
| 2026-09-02 | Fixed 16-colour palette, 2.5-head 16x24 characters, 16x16 tiles, 640x360 base. Style bible fully filled | Same reason. Palette PNG generated from the table. |
| 2026-09-02 | Backlog seeded with tasks 002-011 in dependency order covering the whole first prototype | Better first week than self-planning from zero; self-planning takes over when these are done. |
| 2026-09-02 | Model tags verified: qwen3.6:35b-a3b (orchestrator), qwen3.6:35b-a3b-coding (coder), qwen3-vl:8b (reviewer), gpt-oss:120b (escalation) | Confirmed against Ollama library listings via search. |
| 2026-09-02 | gdUnit4 installed by script on the server, not vendored; plugin pre-enabled in project.godot with a smoke test | Keeps the repo small; the scaffolding session could not download GitHub archives. |
| 2026-09-02 | Game renamed **Reaper's Relics**; Hollowmere retired | Owner's redesign, approved from docs/pitch/reapers-relics-pitch.html. |
| 2026-09-02 | Concept: Survivor.io night hordes + Stardew look and day loop + Elden Ring bosses/stamina/death + Minecraft-style Hold building, unified by a 12 min day / 6 min night clock | Approved (decisions 1, 5). |
| 2026-09-02 | Setting: near-future feudal dystopia, medieval cyberpunk. Tone bleak but not hopeless | Approved (decision 6). |
| 2026-09-02 | Names: the Keep, the Wired (Thrall, Courser, Herald), the Castellan, the Fallows, the Undercroft, Hearth, scythe/hook, Hesper the Reeve, Old Cutter. Rule: medieval words that describe the tech | Approved (decision 8). |
| 2026-09-02 | Palette replaced: ash, leather, dried blood, tarnished gold, one cold glow; Elden Ring register. Pixel layer only; lighting layer is free | Approved. |
| 2026-09-02 | Hordes capped at 150 per instance at rung 1, server-side flow field, compressed positions to clients | Approved (decision 2). |
| 2026-09-02 | Hold building: fixed plot per player inside the Keep at rung 1; free-build is rung 2 | Approved (decision 3). |
| 2026-09-02 | Scale: 32x32 tiles, 32x48 characters, 960x540 base scaled 2x, 30x17 tiles on screen, camera zoom for interiors/dialogue | Approved (decision 4). Stardew framing with double the detail per tile. |
| 2026-09-02 | Interiors on the same map: fading roofs, doors that open/lock/break, horde can enter | Approved (decision 7). |
| 2026-09-02 | 2.5D via 2D: Godot 2D lights with normal maps, particles, CanvasModulate clock, one post-process shader. True HD-2D 3D geometry deferred | Approved (decision 9). Keeps every tool in the studio. |
| 2026-09-02 | Night readability rule: every enemy identifiable at any distance; lamps light ground, not air | Scaffold author's pushback, accepted with approval. |
| 2026-09-02 | Mock frames saved as reviewer references; pitch page archived in docs/pitch | So the artist and reviewer have a fixed target from day one. |
| 2026-09-03 | Loop law: survival is a decision, never a dice roll. Distance from light is danger; Holdouts and wild Hearths are the prepared player's outs; bases are safe because built; breaches cost things | Owner's day-out/night-home loop, with the coin-flip pushback accepted. docs/15 §1. |
| 2026-09-03 | Decision 3 amended: Keep plot at rung 1, **Holdfasts** (party-claimed ruins, Palworld-style base) at rung 1.5, free-build rung 2 | Resolves shared hub vs personal base. docs/15 §3. |
| 2026-09-03 | Building: tile grid, pieces with cost/health/blocking, roofs need support, power by cable from a relic reactor, light attracts the horde | docs/15 §3, game/data/build.json. |
| 2026-09-03 | The Long Night every 7th night; wave pressure scales with light, noise, stored relics | Weekly rhythm; self-balancing difficulty. |
| 2026-09-03 | Weapons: 9 classes with distinct verbs, 25 base weapons, noise as a stat, guns are loud relics; rarities Scrap/Worn/Sound/Fine/Saint; workbench +1..+10; Reliquary socket deterministic and permanent | docs/15 §4. Volume is data, identity is animation. |
| 2026-09-03 | Armor: head/body/legs, light/medium/heavy weight classes, 12 sets with 2/3-piece bonuses and a side effect each, generated from 3 silhouettes per weight | docs/15 §5. |
| 2026-09-03 | Classes: 10 (Reaper, Warden, Gunner, Hunter, Shade, Wright, Linker, Cantor, Physician, Tinker); class = kit + signature relic + talent tree; all gear usable by all; everyone human; nothing is magic | docs/15 §6. Fantasy names reskinned to the world. |
| 2026-09-03 | Workers: robots are repaired relics (Mule, Maintenance drone, Sentry), humans are rescued survivors (Farmer, Smith, Guard, Scout); jobs are stations; 3 workers first | docs/15 §7. Full automation is rung 2. |
| 2026-09-03 | Items are generated from a stat budget by scripts/gen_items.py; JSON is never hand-edited | An unattended AI team cannot hand-balance 25x10x12. docs/15 §8. |
| 2026-09-03 | Weak-model support: engine class-reference search tool, code-built tile maps, written skeleton, mechanical palette/size checks and worker quantization, few-shot examples, JSON text tool-call fallback, gdtoolkit in the gate, repo skills for Claude Code | docs/17-helping-weak-models.md. |
| 2026-09-03 | Reviewer eval harness with 20 seed cases; IP-Adapter character workflow; failure-class escalation (3 in 24 h); normal maps from the worker | docs/17 rows 11-14. Seeds are synthetic and to be replaced with real assets. |
