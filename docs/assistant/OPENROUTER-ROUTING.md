# OpenRouter discovery, evaluation and switching design

Status: required design. Existing runtime validates pricing for configured routes and tries them
in order through Claude Code. It does NOT yet discover/rank all free models, dynamically switch
for task quality, or delegate execution to cloud workers.

## Discover and distinguish availability from suitability

Use `GET https://openrouter.ai/api/v1/models` to inventory models. Store fetch time, exact model ID,
pricing, advertised input/output modalities, context length, supported parameters and description.
The API documents these properties; it is not an authoritative strengths/weaknesses scorecard.
Source: [OpenRouter model API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties).

Refresh on startup, daily, and after a model disappears, with cached snapshots and bounded retry.
Inventory all zero-priced entries, but do not automatically authorize them. Current executable
policy admits explicit `:free` IDs with known zero pricing; other free offerings may be displayed
as unsupported candidates until their route policy is implemented and qualified. Catalog presence
is not proof the current account or harness can use a model. Do not log API keys.
Free variants: [official documentation](https://openrouter.ai/docs/guides/routing/model-variants/free).

## Maintain evidence cards in the private vault

Store model cards in `shared/models/` only if the results contain no private project material;
otherwise keep examples under the originating project and share aggregate scores only.
Each card records provider/model ID, observation date, advertised capabilities, qualification
status, measured strengths, measured weaknesses, task category, test size, pass/fail evidence,
latency, context limits observed, tool/JSON reliability, and confidence. Unknown is a valid value.
Keep vendor claims separate from independently observed behavior; do not invent benchmark scores.
Re-evaluate after provider/model changes or repeated regressions.

Qualification tasks should include dependency planning, detecting bogus evidence, debugging a
reproducible defect, bounded code changes with real tests, and tasks from each active work section.
Vision qualification must supply actual images through the intended adapter. A text-only result
cannot qualify image inspection. Important financial work requires factual sourcing and independently
recomputed arithmetic; this is not a model's self-assessed finance score.

## Route according to the job

Filter by verified free route, account/harness compatibility, modality, context, tool requirements
and project disclosure settings. Rank survivors by relevant measured quality, then availability
and latency. Leadership requires planning/review qualification; a model qualified for narrative
writing alone cannot become the brain. Prefer OpenRouter; use qualified included Ollama cloud as
an alternative. Leave work waiting if no appropriate free cloud route is available.

A cloud lead may select another qualified cloud model for hard work, critique or a second opinion.
The target switch operation persists a handoff packet: scope/subproject, goal, plan/dependencies,
current source revision, source notes, artifacts/hashes, real check results, failed approaches,
remaining acceptance criteria and reason for switching. Record old/new model and outcome.
Switch after supported quality failures, capability mismatch or availability errors; use bounded
attempts and cooldowns rather than bouncing indefinitely. Pin the model during a single request.

OpenRouter also documents a fallback `models` list. That API feature is not assumed to work
transparently through our Claude Code adapter; the current controller uses explicit ordered calls.
Any future direct API adapter must preserve free-only validation and report the actual model used.
Source: [model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks).

## Acceptance for implementation

Test a removed model, nonzero/unknown pricing, free but incompatible model, stale catalog,
rate-limit outage, failed-quality evaluation, vision request without vision support, and restart
mid-handoff. Demonstrate important work moving between two qualified free cloud models with
preserved evidence and no local/paid takeover. Display inventory, evidence cards, routing reason
and a per-task qualified-model override in the UI. These capabilities remain pending.
