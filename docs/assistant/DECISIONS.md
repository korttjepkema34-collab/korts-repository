# Current decisions and continuity record

Confirmed from this conversation, 2026-09-09:

- Build a personal assistant, business helper and video game team, with separate project context.
- Own custom interface and Claude Code skill/MCP familiarity are priorities.
- No new subscriptions or paid inference. Existing $10 OpenRouter purchase enables the higher free
  allowance; it is not a paid-model budget.
- Strong free cloud models lead, decompose, delegate, diagnose, review and direct repairs.
- Local workers never take over leadership or approve themselves. Cloud loss pauses decisions.
- User's heavy daily OpenRouter usage has reached about 600; assume 1,000/day is workable initially.
- Two Windows PCs via Tailscale; server i7-10700K/96 GB/no dedicated GPU; gaming PC
  Ryzen 9 7900X/32 GB/RTX 3080 Ti 12 GB. There is no additional or planned purchased GPU.
- Godot is preferred. Existing repository already contains Reaper's Relics Godot 4 design/code,
  world bible, style references, gameplay systems and tests; preserve them.
- Overnight work needs evidence, repair attempts, honest blockers and morning reports.
- Learning means useful memory and proposed skills, not uncontrolled self-modification.
- Correct GitHub account is korttjepkema34-collab; current repository is public.
- Server uses GitHub as a versioned source of code/setup/knowledge, with private live memory locally.

Implementation decisions for this setup revision:

- SQLite FTS5 plus Markdown/Obsidian vault; no mandatory vector database or paid Sync.
- Standard-library Python controller and native desktop shell to keep installation simple/free.
- Cloud planning/review calls run through Claude Code without arbitrary tools; local workers get
  explicit bounded input. Advanced interactive MCP/tool flows are separate qualification work.
- Code candidates live in isolated clones and require configured checks plus cloud review.
- Legacy unattended loop disabled because local leadership/auto-approval contradicts current policy.
- Media adapters, visual evidence transport and cross-project integration are tracked gaps, not
  described as completed. No live device/model tests claimed without access.

Open details needed during setup: free disk; actual installed versions; eligible Ollama cloud models;
OpenRouter candidate behavior; private business checkout; pinned Godot/add-on versions; GPU gaming
schedule; final UI taste; authenticated service connections; actual overnight recovery behavior.

## Owner clarification — 2026-09-09

OpenRouter is primary for important cloud work; discover free models and evaluate/switch by task.
Three sections are game, general/side projects (existing personal scope), and business including
website, tax and money work. Obsidian is the chosen private knowledge interface. Add worker skills
with explicit tool requirements. See REQUIREMENTS.md and SKILLS.md; pending capabilities remain
listed in ACCEPTANCE.md.

## Catalog implementation — 2026-09-09

Added catalog inventory/cache, six-case synthetic evaluations, private model cards and opt-in
ordering of explicitly qualified routes using fresh matching evidence. All passing candidates
meet the same screening threshold; latency breaks ties and is not an intelligence score.
Task-specific quality routing and automatic promotion remain excluded pending real evaluations.

## Owner approved workforce planning direction — 2026-09-09

Owner approved the consolidated plan and documentation preparation. Preserve existing hardware, qualified free cloud leadership, private project scopes and replaceable specialist profiles. The browser office follows the approved pixel-art reference with connected rooms, character movement, expressions and real event-driven handoffs. Use the newer assistant runtime and SQLite-first display projection; do not reactivate the legacy studio loop or add Redis solely for animation.

Deliver simulator, real read-only view, safe parallel scheduling and interactive controls in separately reviewed stages. Keep model choices as candidates until qualified. Pause affected cloud decisions when privacy/free-route requirements cannot be met; no paid/local-leader fallback. Weekly roster reporting remains planned and inactive. This approval permits preparing documentation; publication and feature implementation remain separate gates. See WORKFORCE-PLAN.md.

## Owner-approved authority and Obsidian rules — 2026-09-09

The owner approved publication of the version 0.2 authority package. See authority/README.md. It formalizes mandatory independent review, cloud technical judgment, owner publication approval, bounded repairs, a persistent private mailbox, and Obsidian/GitHub knowledge ownership. It supersedes the legacy “never wait” instruction. Runtime enforcement and live qualification remain pending; do not infer new permissions or activated profiles from documentation alone.

## Persistent runtime and private dashboard candidate — 2026-09-11

Prepared on branch `assistant/overnight-runtime` for owner review (not merged): persistent runner
with leases, retries and task dependencies; audited per-project cloud consent in addition to
config; OpenRouter cost evidence by key-usage delta and rejection of substituted models; exclusive
GPU lease and gaming mode; authenticated loopback/Tailscale-only dashboard with audited controls;
conversations, plan confirmation and clarifying questions; backups, health monitoring, benchmarks,
patch export with rollback points and a connector policy gate. Live qualification remains required.
See OPERATIONS.md and OVERNIGHT-2026-09-11.md.

## Private dashboard and pixel office candidate — 2026-09-11

The dashboard opens on a real-state pixel office named The Night Shift, with the task, inbox,
knowledge and system tools in one responsive shell. Callsigns, room assignments and named character
palettes live in the private runtime's `office.json`, seeded from `config/assistant/office.json` and
included in backups. Project filtering is enforced from the authenticated server projection.

Simulation is an explicit browser-only preview with a persistent label and no controller calls.
Arbitrary configured CSS is disallowed so the existing `style-src 'self'` policy stays intact.
Actual mutations continue through authenticated controller endpoints and the audit log. See
DASHBOARD-IMPLEMENTATION-2026-09-11.md for the implementation and verification record.
