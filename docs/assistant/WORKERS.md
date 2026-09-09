# Editable workers

`config/assistant/workers.json` contains 13 specialist profiles. The cloud orchestrator and reviewer
have separate prompt files in the same directory. Profiles are not separately loaded models.

| Worker | Current adapter | Deliverable |
|---|---|---|
| UI | code-sandbox | Isolated source candidate, configured checks and cloud review |
| Backend | code-sandbox | Same, business scope |
| Game coder | code-sandbox | Same, Godot scope |
| Operations / personal helper | ollama-draft | Administrative/personal drafts |
| Narrative / level designer | ollama-draft | World-consistent text/layout proposals |
| Debugger / optimizer | ollama-draft | Evidence-based diagnosis or measured optimization proposal |
| Visual QA | ollama-draft | QA plan/evidence analysis; screenshot ingestion integration still required |
| Environment / sprites / audio | unconfigured-media | Blocks until native asset adapter is integrated and qualified |

The private `workers.json` created by initialization is the active editable version. Change name,
model, endpoint, context size, project list, instructions and skill references there. Do not broaden
project visibility merely to make retrieval easier. The cloud brain selects among profiles eligible
for the task's project. Duplicate a role only when evaluation supports a useful difference.

`skills` is a list of repository-relative Markdown paths, such as
`.claude/skills/godot-check/SKILL.md`. The controller injects their instructions as worker context;
it does not execute arbitrary bundled scripts. Existing interactive Claude Code skills remain
available through their normal project setup, but active tool availability must be tested in that
session. Reading a skill and having the tools to perform it are separate checks.

Feedback loop: symptom → evidence → repair → verification → scoped lesson → proposed skill →
regression examples → reviewed promotion. A worker cannot change its own authority. Keep revisions
of private profile changes and deliberately publish only reusable, nonprivate template changes.

Morning reports include goal, status, attempts, blockers, review, proposed prevention and artifact
paths. A root cause can remain unknown. Code marked verified_candidate passed only its configured
checks and cloud review, not every possible acceptance test or a live deployment.
