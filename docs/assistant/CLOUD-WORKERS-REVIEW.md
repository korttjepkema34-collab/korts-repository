# Cloud execution workers — owner approved

## Before and after

| Before | Prepared change |
|---|---|
| Cloud only plans and reviews | Cloud also generates code candidates and substantive drafts |
| Execution always calls local Ollama | Planner selects a local specialist or cloud specialist |
| Worker model choice is not recorded per job | Successful execution records provider/model provenance |
| Cloud execution unavailable | Outage persists the job without local fallback or consuming a repair attempt |

## Behavior

Two editable profiles are added: `cloud-engineer` uses the `cloud-code` adapter for difficult
implementation; `cloud-analyst` uses `cloud-draft` for important reasoning and problem solving.
They support the existing personal/general, business and game scopes. The planner sees their
roles and chooses them for hard work; existing local specialists remain available for simpler jobs.

Cloud workers call the existing Claude Code adapter using configured qualified free routes,
current OpenRouter pricing checks, persisted call allowance and optional catalog ranking.
They cannot choose an arbitrary paid endpoint. Cloud drafts return structured JSON; cloud code
returns bounded file replacements. The controller applies code in the same private task/worker
workspaces as local code and runs trusted configured checks. Workers do not gain shell/MCP access.

A successful generation is awaiting_review, never self-approved. A separate cloud call reviews
it; code also passes integration and final combined checks/review. Separate calls can use the same
model; this is not guaranteed independent judgment from a different model family. Route records
identify the configured model, not an independently verified underlying provider implementation.

If no qualified route completes execution, the task waits for cloud. No local takeover occurs.
The next run retries that job; cloud allowance accounting still applies even though unavailable
execution does not consume the worker's repair budget. Backoff and independent-job scheduling
within an affected task remain part of the overnight-recovery work.

## Enable after approval and server setup

New initialization copies the two profiles automatically from `config/assistant/workers.json`.
For an existing installation, copy just `cloud-engineer` and `cloud-analyst` entries into the
private runtime's `workers.json`; preserve personal edits to other workers. Stop/restart the
runner when changing configuration. Never replace private config.json with the template.

Qualify the intended free route for actual coding/reasoning tasks, set its qualified flag and
configure the project's cloud-context permission. The existing smoke suite alone does not establish
production coding quality. For code, configure `code_projects[scope]` with source, allowed paths,
context files and trusted checks. The personal scope has no default code project; add it explicitly
for general side-project code. Without these settings execution blocks instead of guessing paths.

## Limits and review

Execution remains serial; this does not yet run local and cloud jobs simultaneously. Adaptive file
exploration, OS sandboxing, native media and richer capability-specific routing remain separate
work. No live model or home-PC qualification was possible here. The owner workflow requires
review before publishing this prepared change to GitHub.

## Observed verification

Full repository suite: **73 passed**, one existing Pillow deprecation warning. Assistant-only
suite: **59 passed**. Python compilation and diff whitespace checks passed. New tests exercise
cloud execution versus separate review, outage/resume without local fallback, malformed draft
rejection, project disclosure gating and real Git/check/integration behavior for cloud code.
Cloud replies are controlled fixtures; no actual model quality claim follows from these tests.

## Owner approval

Owner approved publication of this change to the existing GitHub PR. This does not merge
the PR into main or deploy the assistant to the home PCs.
