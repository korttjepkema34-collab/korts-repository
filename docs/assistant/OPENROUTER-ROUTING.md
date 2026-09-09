# OpenRouter discovery, evaluation and switching design

Status: catalog discovery, cached refresh, six-case smoke evaluation, private model cards and
opt-in evidence-gated ordering of configured cloud routes are implemented in `assistant/catalog.py`.
Run the commands below. Capability-specific benchmarks, quality-triggered mid-task switching,
UI inventory and cloud execution workers remain pending. Do not confuse smoke results with
comprehensive model qualification.

## Use on the server

From the repository, using its Python environment:

```powershell
python -m assistant.catalog refresh
python -m assistant.catalog list
python -m assistant.catalog evaluate "EXACT-MODEL-ID:free"
python -m assistant.catalog rank
```

Replace the placeholder with an ID from the refreshed inventory. `refresh` makes a catalog HTTP
request, not an inference request. `evaluate` makes six synthetic Claude Code calls to that model
and consumes the existing allowance. It requires the configured Claude Code installation and
OpenRouter key. It never changes qualification or enables a model automatically.

Evaluation covers simple dependency ordering, a larger dependency graph, rejection of false test
success, cloud authority, a debugging response and exact monetary arithmetic. Responses, latency,
failures and unknown capabilities are saved under the private runtime's `models/` directory.
Synthetic-only model cards are also written to `vault/shared/models/` for Obsidian and retrieval.
Each evaluation is retained; the latest card is used for routing. No private project inputs enter
this shared evaluation suite. Cards describe observations, not universal strengths/weaknesses.

After inspecting the card and completing the real qualification steps in MODELS.md, add the model
to private config.json `cloud_routes` with provider `openrouter` and `qualified: true`. Set
`catalog_routing: true` to enable evidence-gated routing. Existing configurations remain unchanged
until enabled. Stop/restart the runner after changing config. `rank` previews the eligible order.

Enabled routing requires a matching catalog fingerprint, passing current smoke suite and evidence
less than 30 days old. Among models that pass the same suite, average observed latency breaks the
tie; this is not a claim that the fastest model is smartest. Qualified included Ollama routes follow
OpenRouter. If the catalog cannot refresh after 24 hours, routing waits instead of trusting stale
data. Every OpenRouter invocation also rechecks current free pricing. A failed invocation tries
the next eligible configured cloud route with the same prompt; existing task evidence persists.
Unlisted/unqualified models never become leadership candidates solely through discovery.

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
and a per-task qualified-model override in the UI. The richer switching/GUI scenario remains pending; basic catalog and routing failure paths have offline tests.

## Approved workforce extension requirements

The existing catalog and ordered fallback calls remain as implemented. The following are planned requirements, not new runtime guarantees:

- Apply price, capability, qualification and project/provider privacy eligibility before routing. When no eligible free cloud leader exists, persist and pause affected decisions; never silently choose paid inference or local leadership.
- Qualify real modalities and tool behavior through the actual harness. A provider supporting images does not establish that the current text adapter delivers images.
- Coordinate minute/day budgets across planning, execution and review; reserve capacity for review/recovery, honor retry hints and use bounded backoff/cooldowns. Application invocation estimates are not account-wide provider request counts.
- Preserve task/run IDs, source revision, accepted artifacts and remaining criteria across model switches. Discovery alone never activates a model.
- Plan a weekly human-facing roster summary alongside runtime freshness checks. No automation is created by this documentation. Reports recommend changes; they never activate routes automatically.

See [WORKFORCE-PLAN.md](WORKFORCE-PLAN.md) for staged delivery. The free endpoint privacy restrictions cannot be solved by dropping a `:free` suffix or letting a local specialist approve itself.
