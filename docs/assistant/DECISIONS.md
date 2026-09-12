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

## Media workers deferred — 2026-09-11

The owner decided to **skip media work entirely for now**, until the rest of the system is finished
and fine-tuned. Image, sprite, audio, video and ComfyUI adapters stay on the `unconfigured-media`
adapter and keep reporting **unavailable**; their jobs block rather than pretending to succeed.
No media tool, endpoint or credential is to be selected or wired up until the owner reopens this.
Revisit only after local/cloud routing, consent, execution boundaries, backup and the reboot and
overnight acceptance runs are settled. This supersedes the media items in ACCEPTANCE.md's gap list
for scheduling purposes; it does not mark them complete.

## Cloud context granted for all projects — 2026-09-11

The owner reviewed per-project cloud scoping, kept the mechanism, and chose to enable cloud models
for **every** project rather than a subset. Both required switches are now set for `personal`,
`business` and `game`: the audited runtime grant (`assistant.run consent <project> --grant`) and
the `allow_cloud_context` flag in the private `config.json`. Project notes and task context for all
three scopes may therefore be sent to qualified zero-cost OpenRouter routes. Per-project revocation
remains available and audited; the two-key design is unchanged.

## Why cloud leadership looked unreliable — 2026-09-11

Measured against the live catalog, not inferred. Cloud calls were never broken; two defects and one
misconfiguration made the strongest routes look unusable, so leadership stayed pinned to the
smallest model that happened to pass first.

- The private `config.json` carried `cloud_timeout_seconds: 60` while the shipped template uses
  `600`. Raised to 600.
- OpenRouter intermittently answers with HTTP 200 and an envelope containing neither `usage` nor any
  `finish_reason` — an unfinished generation, reproduced repeatedly on a cold route and absent once
  warm. `openrouter_ask` reported that as `rejected_cost_missing`, a policy rejection carrying the
  1800 s cooldown that doubles to the 3600 s cap. With one configured route this removed cloud
  leadership for 30–60 minutes after a single blip. It is now an ordinary outage on the 60 s
  backoff; the answer is still refused, because its cost was never verified.

Live seven-case results afterwards, zero reported cost throughout and no substituted models:
`nemotron-3-ultra-550b-a55b:free` 5/7 (2.5–7.7 s, no transient failures once the classification was
fixed), `nemotron-3-super-120b-a12b:free` 5/7 (0.7–7.7 s), `ling-3.0-flash-vl:free` 5/7,
`nex-n2.5-pro:free` 5/7. `thinkingmachines/inkling:free` returns hard HTTP 403 because OpenRouter
restricts it to approved agentic harnesses — not to be worked around. `gemma-4-31b-it:free` returned
HTTP 429 on every attempt and is treated as saturated.

Across every randomized reconciliation problem, Ultra answered 4 of 5 correctly; Super, Ling and
nex each answered 0. No free route is dependable at money arithmetic, so Charter C5 stands: business
figures must be recomputed independently and never taken from a model's own output.

## Leadership promoted to Nemotron Ultra — 2026-09-11

Owner approved promoting `nvidia/nemotron-3-ultra-550b-a55b:free` to the primary route with
`inclusionai/ling-3.0-flash-vl:free` retained as fallback. Both are marked qualified from live
evidence recorded in the private runtime under `models/`. Verified after the change: the primary
served a real request, and with the primary deliberately broken the call fell through to the
fallback, both at zero reported cost with no substituted model.

The three free Ling variants were compared over one 10-case run (the suite plus three extra
reconciliation problems). `-fin`, `-sante` and `-vl` each scored 5/10 with money arithmetic 0/5,
passing every judgment case and failing every arithmetic one at 0.7-1.4 s. They are interchangeable
for this system's purposes; keep `-vl` and ignore the others. Notably `-fin` is finance-branded and
still answered none correctly, with plausible near-miss figures — domain tuning is not evidence of
arithmetic reliability.

## Specialists are routed by strength; arithmetic is not a model job — 2026-09-11

The owner's design intent is a team: a weaker orchestrator is acceptable when another specialist
covers that gap, and roles should be assigned to strengths rather than seeking one model that is
best at everything. That holds for reasoning, drafting, review and code.

It does not extend to money arithmetic, because no tested free model is dependable there and the
best observed was 4/5. The specialist for a financial figure is deterministic code, not another
model. Any finance role must recompute through a calculation tool and treat model output as a
proposal to check, which is what Charter C5 already requires.

## Tjepkema dashboard access — 2026-09-11

The owner explicitly chose passwordless access for the Tjepkema Server page. The deployed runtime
uses `assistant.web access open --user kort`: every visitor who can reach the private page receives
owner scope, while allowed Host/Origin checks, CSRF validation, audit records, response redaction,
strict browser headers, and the Tailscale-only backend bind remain enforced. Password access stays
available as a reversible configuration mode.
