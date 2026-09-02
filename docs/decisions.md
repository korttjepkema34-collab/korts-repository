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
