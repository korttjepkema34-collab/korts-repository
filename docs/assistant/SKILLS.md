# Worker skill catalog

Twelve original skills are authored here for the home assistant. They are reusable instructions,
not installed services or executable tool adapters. Each names required tools, readiness and the
proof needed for completion. They have not been behaviorally qualified with live worker models.

| Worker | Skill |
|---|---|
| Orchestrator / cloud reviewer | [cloud-route](worker-skills/cloud-route/SKILL.md) |
| Every worker | [knowledge-recall](worker-skills/knowledge-recall/SKILL.md) |
| Backend / general coding / game coding | [code-change](worker-skills/code-change/SKILL.md) |
| UI / visual QA | [ui-inspection](worker-skills/ui-inspection/SKILL.md) |
| Debugger / cloud problem solver | [debug-regression](worker-skills/debug-regression/SKILL.md) |
| Optimizer | [measure-performance](worker-skills/measure-performance/SKILL.md) |
| Game coder / level designer | [godot-level-check](worker-skills/godot-level-check/SKILL.md) |
| Environment artist / sprite animator | [game-art](worker-skills/game-art/SKILL.md) |
| Audio worker | [game-audio](worker-skills/game-audio/SKILL.md) |
| Narrative worker | [lore-consistency](worker-skills/lore-consistency/SKILL.md) |
| Business finance/tax specialist (planned cloud-backed role) | [business-money-review](worker-skills/business-money-review/SKILL.md) |
| General helper / operations | [research-and-operations](worker-skills/research-and-operations/SKILL.md) |

## Assigning skills

All workers should use knowledge-recall when retrieving project context. Assign additional skills
by task, not the entire catalog to every model. In the existing private `workers.json`, a worker's
`skills` array can contain repository-relative paths such as
`docs/assistant/worker-skills/code-change/SKILL.md`. The current runtime reads these Markdown files
into that worker's prompt. This does not enable a browser, generator, financial account or MCP.
Existing initialized profiles are not overwritten by this documentation update.

Skills live here to avoid automatically loading unqualified procedures into Claude Code sessions.
A future skill registry should show worker assignments, tool availability, versions and evaluation
results. The planner/reviewer currently loads its own prompt files, not this catalog automatically.
Cloud-route therefore remains guidance for the upcoming routing implementation.

## Learn from mistakes

Record a lesson in the originating private Obsidian project: reproduction, actual cause or unknown,
failed approaches, repair, check evidence and proposed skill change. The cloud reviewer evaluates
whether it generalizes, then proposes a versioned Git change containing only shareable guidance.
Test on the original failure and a nearby different task before promotion. Preserve previous skill
versions for rollback. Never copy customer/tax documents or credentials into public skill files.
Automatic lesson promotion and tool-aware skill selection remain implementation tasks.
