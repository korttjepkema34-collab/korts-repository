# Confirmed assistant requirements — 2026-09-09

These are owner requirements, not optional ideas. Keep them visible when implementing or changing
architecture. This document supplements DECISIONS.md; implementation status is in ACCEPTANCE.md.

## Leadership and delegation

A capable cloud orchestrator breaks the user's goal into specialist jobs, assigns context, tools,
dependencies and acceptance criteria, diagnoses problems, directs repair, and reviews results.
Cloud models handle important reasoning, difficult implementation and problem solving as well as
planning/review. Local models do bounded work; they never take over leadership during an outage.
Workers are customizable roles, not necessarily separate model downloads. The same model may fill
multiple roles, and a role may use different qualified models for different tasks.

OpenRouter is the PRIMARY cloud source because the owner already has the 1,000-free-request/day
allowance. Ollama included cloud usage is an alternative. No new inference spending, paid fallback,
subscription or GPU purchase. Preserve capacity for important work; do not artificially restrict
use to tiny quotas. Measure the account's actual activity and availability.

The target must discover free OpenRouter models, maintain evidence of strengths and weaknesses,
and switch qualified cloud models for capability, quality, outages or availability. A permanent
hardcoded model is not the final design. See OPENROUTER-ROUTING.md.

## Three visible work sections

| UI section | Internal scope | Includes |
|---|---|---|
| Game development | game | Godot, game code, art, sprites, audio, lore, levels and playtesting |
| General / side projects | personal (existing ID retained) | Personal assistant, research, random projects, experiments and nongame coding |
| Business | business | Website, operations, bookkeeping, taxes, money analysis and business projects |

Each section needs its own profile, goals, project folders, tools, memory and task history. Add
subproject IDs/folders so unrelated side projects or business projects do not blend together.
Share only intentionally shared knowledge. Existing runtime separates the three broad scopes;
finer subproject retrieval boundaries and friendly UI labels still need implementation.
Business tax/money work needs a specialist skill and cloud reasoning, with source-grounded rules,
explicit jurisdiction/year and reproducible calculations. This is not authorization to file taxes,
move money, or modify financial accounts.

## Obsidian is the chosen knowledge interface

Use Obsidian to record, edit, link and reference the assistant's private Markdown knowledge.
The assistant should retrieve relevant notes before work, cite source notes, and propose updates
from completed work and mistakes. GitHub holds code, skills, setup and shareable decisions; the
private vault holds actual personal/business facts and project evidence. SQLite holds task state
and the rebuildable search index. Obsidian is chosen even though the file format stays portable.

Keep facts distinct from hypotheses and proposals; record sources, timestamps, confidence and
superseded decisions. Promote lessons only with evidence and review. Failed attempts must remain
available so another model does not repeat them after a handoff. See MEMORY.md and SKILLS.md.

## Overnight work and model handoff

Persist plan, source revision, artifacts, tool results, acceptance criteria, attempts and review.
Switching cloud models transfers this evidence, not an unsupported summary of success. Reports
must say what finished, what failed, known causes versus hypotheses, repair attempts, prevention
and suggested skills, and remaining owner decisions. Continue independent useful work when a
job blocks. Cloud absence never grants a local model approval authority.

## Scope of this update

This update records requirements and authors reusable skill instructions. It does not claim that
automatic catalog discovery, capability-based switching, cloud execution workers, subproject
isolation or all described tools have been implemented. Track those in ACCEPTANCE.md.
