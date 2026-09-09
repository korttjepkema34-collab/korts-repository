# AI Workforce Consolidated Audit Plan

Date: 2026-09-09
Status: Owner approved the planning direction and preparation of documentation. Implementation, publication, and deployment remain separate review gates.

## Purpose and conclusion

Build a cloud-led assistant for business, game development, and general projects, with configurable local specialists and an animated browser office that accurately shows their work. Preserve the approved pixel-art style while protecting the existing hardware's inference capacity.

The next change should be documentation reconciliation against the newer assistant branch, followed by a small simulated office and then actual runtime integration. Do not implement the uploaded handoff against the legacy runtime unchanged. Do not turn every blueprint feature into an immediate requirement.

## Baseline and source status

Baseline: `assistant/cloud-led-memory-setup` at `137941d1e5993a215ec4c4b278b1635dcbb54812`, draft PR 1. Recheck the branch before implementation. This plan reconciles the owner-supplied product blueprint, older Live Workforce handoff, research excerpts and approved pixel-art reference. Private transcripts and the reference image are not included in this documentation change.

Repository inspection establishes code state, not live hardware performance. Model names remain candidates. The original handoff's legacy Redis integration instructions are superseded by [the revised handoff](LIVE-WORKFORCE-HANDOFF.md).

## Decisions to preserve

| Area | Preserved direction | Qualification |
| --- | --- | --- |
| Leadership | Qualified free cloud models plan, delegate, and provide final review; OpenRouter preferred | A local reviewer advises; it never becomes final cloud authority |
| Hardware | Windows server i7-10700K, 96 GB RAM, no discrete GPU; Windows gaming PC Ryzen 9 7900X, 32 GB RAM, RTX 3080 Ti 12 GB | No new hardware purchase planned |
| Work sections | Business, game, general/side projects | Preserve private memory and project boundaries |
| Specialists | Persistent editable role profiles, independent of model identity | Thirteen research roles are a bench, not thirteen simultaneous processes |
| Concurrency goal | Cloud work overlaps with one primary server inference workload and one GPU workload | Current runner is serial; concurrency is future implementation |
| GPU use | GPU LLMs and ComfyUI share exclusive ownership | Gaming, offline, waiting, loading, and failure are distinct states |
| Appearance | Approved detailed pixel-art office, characters, movement, expressions, and visible handoffs | Reference image is a design target, not a working screenshot |
| Controls | Human review before publication/deployment; no automatic paid fallback | Transcript options mentioning paid routes do not override current policy |
| Network | Private access through Tailscale | Browser never connects directly to model services or databases |

## Approved visual direction translated into requirements

Preserve the dark navy application frame, readable panel borders, warm interior lighting, pixel characters, city-window backdrop, connected rooms and walkways. Use a two-level office composition inspired by the supplied reference. The image contains both a proposed application and presentation panels showing character/theme examples; those demonstration panels should not all become permanent screen furniture.

Initial rooms: Cloud HQ, Server Room, GPU Studio, Creative Studio, World Room, Review Room, and Lounge. Rooms represent activities, not exclusive physical machines. Creative Studio and GPU Studio visibly share the same gaming-PC resource. A role's room does not hardcode its model's machine.

Initial visible identities: Atlas (orchestrator), Forge (coding), Pixel (UI/media), Scout (research), Scribe (lore), Judge (review). These are display names. Map them to actual specialist IDs, retaining distinct UI-inspection and media-generation profiles behind Pixel's initial visual grouping. Concurrent instances must remain distinguishable. All thirteen roles can later receive their own appearance without changing the runtime model.

Required initial behavior:

- Idle, walk, work, wait, needs-user, error, review, handoff, and completion states.
- Characters carry a visible task object along a small fixed waypoint graph, including stairs.
- Task assignment and receipt trigger handoff animation. Backend work never waits for animation completion.
- Rapid events collapse to the latest truthful state; critical alerts stay visible.
- Speech bubbles contain short safe operational summaries, not fabricated agent dialogue or hidden reasoning.
- Expressions represent display state, not actual model emotions.
- Click or keyboard-select a character to inspect task, role, model, machine, last activity, and review state.
- Project selector filters both the scene and details. Cross-project private content must not appear through global activity panels.
- Small screens show a scrollable or zoomable office plus a readable accessible list; do not shrink every panel to fit the desktop reference.
- Reduced-motion mode replaces walking with immediate position updates and status changes. Sound is off by default.

Defer configurable weather, day/night cycles, room themes, furniture editor, animated pet, elaborate social interactions, and extra decorative effects. A polished static room background and reusable sprite sheets can deliver the approved atmosphere without a large simulation engine.

## Reconciliation with the code

| Topic | Evidence in newer branch | Planned correction |
| --- | --- | --- |
| Runtime authority | `assistant/run.py` coordinates cloud planning, execution, review, and integration | Instrument this runtime; do not reactivate `server/orchestrator/main.py` |
| State | `assistant/core.py` stores tasks and events in SQLite | Build a sanitized projection of authoritative state |
| Cloud workers | `cloud-code` and `cloud-draft` execution exist | Correct stale acceptance entries instead of rebuilding these features |
| Models | `assistant/catalog.py` discovers free candidates and performs preliminary evaluations | Extend qualification later; no unsupported intelligence ranking |
| UI | `assistant/desktop.py` is an initial desktop shell | Add browser office without rebuilding every desktop control immediately |
| Media and GPU | Shared leases and native media integration remain gaps | Keep simulated media clearly labeled until real adapters and ownership are verified |
| Concurrency | Current execution is serial | Treat parallel scheduling as a separate milestone |
| Old handoff | Assumes Redis stream and legacy worker instrumentation | Preserve visual intent; revise transport and integration sections |

## Proposed runtime and event design

Use SQLite as the authoritative task store for the first integration. Add a read-only browser gateway and a versioned display-event contract under `assistant/`. Prefer a bounded incremental read of committed event records plus current snapshots for the initial implementation. Redis is not required solely to animate the office. A future worker transport can use Redis behind an adapter if distributed scheduling justifies it; it must not become a second task authority.

Persist essential lifecycle state with the task update. UI delivery is best-effort and isolated from execution. Do not broadcast existing event `detail` or task `data` wholesale: those fields can contain private material.

Display fields should be explicitly allowed: schema version, event cursor, project/task/job/run IDs, specialist and instance IDs, safe activity code, state, machine/resource ID, model ID, approved short summary, and timestamp. Progress remains unknown unless measurable; never invent percentages.

Recovery requirements:

- Snapshot and cursor must describe the same logical point in state; subsequent updates start after that cursor.
- Deduplicate repeated events and reject stale state changes for completed runs.
- On missing history or restart, rebuild from current authoritative records rather than assume retained events contain everything.
- Distinguish disconnected viewer, stale machine evidence, machine offline, and inactive specialist.
- Bound client queues and history; slow viewers receive a fresh snapshot rather than grow memory without limit.
- A UI failure cannot interrupt model execution. A storage failure affecting task integrity remains a runtime error, not something to hide as an observability issue.
- No mutation endpoints in the first office release. Later commands require authentication, origin protection, acknowledgments, and the controller's policy checks.

## Model registry and evaluation plan

Retain the transcript's model names as research candidates, not installed or qualified defaults.

| Role | Candidate from transcript | Proposed location |
| --- | --- | --- |
| Orchestrator | Nemotron 3 Ultra; Nex-N2.5-Pro; Inkling; MiniMax M3; temporary Dots3 candidate | Cloud |
| Tool execution | Nemotron 3.5 Lightning 30B-A3B Q4 | Server |
| Deep coding | Qwen3-Coder 30B-A3B Q4 | Server |
| Fast coding | Qwen2.5-Coder 14B Q4 | Gaming GPU |
| UI inspection | Qwen3-VL 4B Q6 | Gaming GPU |
| Independent local review | Gemma 4 12B Q4 | Gaming GPU |
| QA investigation | GLM-4.7-Flash 30B-A3B Q4 | Server |
| Lore | Qwen3 14B Q4 | Server |
| Research | Mistral Small 3.2 24B Q4 | Server |
| Administration | Small Gemma/Qwen candidate | Server |
| Retrieval | Exact embedding and reranker artifacts unresolved | Server, with bounded supporting resource budget |
| Images | Exact FLUX-family ComfyUI workflow unresolved | Gaming GPU |
| Video | Wan2.2 TI2V-5B workflow candidate | Gaming GPU |

Each record needs an exact provider ID or artifact revision/checksum, license, runtime/version, quantization, tested context, modalities, tools, machine eligibility, measured RAM/VRAM and latency, privacy eligibility, fallback list, evaluation evidence, and qualification date. A downloaded file size is not peak memory. Advertised context is not a recommended deployment setting.

Evaluate a small first roster, retaining the full bench as backlog. Use 15–20 repeatable orchestration cases covering dependency planning, hardware assignment, GPU contention, gaming interruption, unavailable cloud, privacy restrictions, invalid results, failed tests, review disagreements, recovery, and switching with preserved evidence. Evaluate actual image inputs separately from text descriptions of images. Different model families are useful review diversity, not proof of correctness.

Record vendor claims separately from observed results. The transcript's 9.x/10 fit scores are opinions. Model availability and telemetry are dated observations. Exact free endpoints require rechecking; broad model family names cannot authorize a paid variant.

## Approved scheduling and policy direction

1. Preserve free-cloud-only leadership. If no privacy-compatible qualified free route is available, pause the affected decision; do not silently use paid inference or a local leader.
2. Initially disable automatic paid escalation and treat discovery as inventory only. New models require qualification and owner-reviewed activation.
3. Add daily runtime catalog freshness checks when routing needs them, plus a weekly human-facing roster summary as a later automation. Do not schedule it as part of this planning task.
4. Reserve cloud budget for review and recovery. Track application estimates separately from account-wide usage; CLI invocations may not equal provider requests. Coordinate rate limiting across cloud lead, workers, and reviewers, with bounded retries and cooldowns.
5. Parallelize independent approved work only after ownership, dependency, and resource-lease rules are implemented. Use isolated code workspaces and serial reviewed integration.
6. GPU lease design must include owner/run ID, renewal, expiry, crash recovery, gaming preemption rules, unload acknowledgment, and actual free-memory checks. Lease expiry alone must not authorize a second model while the first process is still using VRAM.

## Staged implementation and review gates

| Stage | Scope | Required evidence before progressing |
| --- | --- | --- |
| A — Documentation | Reconcile decisions, status, visual requirements, registry and event design | Owner audits this plan and proposed documentation diff |
| B — Office simulator | Browser scene, six characters, fixed routes, safe event fixtures, details and reduced motion | Visible task assignment, walk, handoff, review, error, needs-user and completion; clearly marked simulated mode; no inference calls |
| C — Real read-only view | New assistant runtime instrumentation, SQLite projection, snapshots and gateway | Real task transitions; restart/reconnect; no private payload leakage; UI failure isolation; no misleading media activity |
| D — Resource-aware execution | Parallel cloud/server work, GPU worker ownership and media adapter integration | Independent work overlaps; conflicting work serializes; gaming/offline/crash recovery; no duplicate job effects |
| E — Controls and expansion | Authenticated commands, richer model/specialist forms, project UI, media presets | Policy enforcement, command audit, cancel/pause semantics and end-to-end tests |

Stop after each stage for owner review. Stage B proves appearance and event behavior; it does not establish runtime concurrency or production readiness. Stage C can honestly show the existing serial runner. Do not delay visual feedback until the entire scheduling system exists.

## Performance and verification

Use client-side sprites at approximately 30 FPS, with hidden-tab throttling and a static background. No model call, server frame loop, video renderer, or ComfyUI operation may drive normal office animation. If viewed on the server itself, browser CPU and integrated graphics still consume local resources and must be measured separately.

Retain the handoff's provisional gateway targets: roughly 1% idle CPU, 3% simulated busy CPU, 200 MB RAM, and typical events below 2 KB. These are targets, not guarantees. Define measurement duration and process/system CPU normalization before recording them. Compare representative inference latency and throughput with the UI off and on under the same workload; proposed acceptable median slowdown is at most 5%, with variability reported. Optimize or revise scope if the measured impact is material.

At implementation time run the existing assistant unit suite, `pytest tests`, compilation, relevant frontend checks, and browser verification. Add meaningful tests for event sanitization, ordering, snapshot consistency, stale evidence, reconnect, bounded buffers, project filtering, and disabled mutations. Hardware inference, Windows operation, Tailscale, and GPU lease behavior require the actual PCs. Do not claim those from fixtures.

## Documentation change scope

The paths below define this prepared documentation change. Runtime implementation remains pending; the files have not been published.

| Path | Intended change |
| --- | --- |
| `docs/assistant/WORKFORCE-PLAN.md` | Consolidated architecture, stages, and source provenance |
| `docs/assistant/LIVE-WORKFORCE-HANDOFF.md` | Revised handoff targeting `assistant/`; supersession notice for older instructions |
| `docs/assistant/UI-DESIGN.md` | Approved visual direction, reference filename, accessible responsive behavior |
| `docs/assistant/MODELS.md` | Candidate bench, exact artifact requirements, qualification status |
| `docs/assistant/OPENROUTER-ROUTING.md` | Privacy eligibility, budget, handoff, and evaluation requirements |
| `docs/assistant/ACCEPTANCE.md` | Correct stale cloud-worker status and add staged workforce acceptance |
| `docs/assistant/DECISIONS.md` | Approved decisions only; unresolved proposals labeled |
| `AGENTS.md` | Point future implementers to current workforce plan without reactivating legacy runtime |
| `docs/decisions.md` | Cross-reference newer decisions to prevent contradictory authority |

Keep original research identifiable, and do not upload private transcripts to the public repository. Use a reviewed public-safe summary. Reference-image inclusion in GitHub is a separate packaging choice; no remote upload of the image is included in this task.

Proposed future code locations: `assistant/workforce/` for display schemas, projection and gateway; `ui/live-workforce/` for browser assets; `config/assistant/` for display mappings; `tests/assistant/` for backend tests. These are provisional until implementation dependency review. Keep the renderer replaceable; React/TypeScript with PixiJS is a candidate, while Canvas 2D is acceptable if it meets the visual target more simply.

## Approval and remaining execution inputs

The owner approved this plan's direction and documentation preparation. The office, model scheduling and browser controls remain unimplemented. Review the prepared documentation diff before publishing. Before live qualification, record SSD/NVMe free space, installed runtimes, exact model artifacts, network setup and representative tasks. Additional art references can refine the look but do not block architecture work.

## Source links for previously checked model claims

- Nemotron free endpoint: https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free
- Nex free endpoint: https://openrouter.ai/nex-agi/nex-n2.5-pro:free
- Inkling free endpoint and usage notice: https://openrouter.ai/thinkingmachines/inkling:free
- OpenRouter limits: https://openrouter.ai/docs/api/reference/limits
- Google Gemma model card: https://huggingface.co/google/gemma-4-12B
- NVIDIA Lightning artifact: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4
- ComfyUI Wan guidance: https://docs.comfy.org/tutorials/video/wan/wan2_2

These references substantiate portions of the earlier research; they do not establish local performance, universal model ranking, or compatibility with this assistant. Recheck exact routes and artifacts before qualification.
