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
