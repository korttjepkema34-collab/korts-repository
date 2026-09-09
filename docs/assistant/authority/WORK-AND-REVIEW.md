> Owner approved version 0.2 for publication on 2026-09-09. This is governing policy/design, not evidence that runtime controls are implemented. Proposed defaults in the reviewed text are adopted as design defaults; task-specific budgets still require configuration.

# Document 2 — Work and Review Rules

## W1. Task intake

Record: task ID, project ID, owner's outcome, scope, authorized sources/tools, excluded actions, base revision, relevant rule versions, acceptance criteria, dependencies, sensitivity, resource requirements, budget and desired reporting time. Missing minor details may use documented reversible assumptions; missing facts that determine correctness must be resolved or flagged.

The orchestrator selects qualified specialist profiles by task capabilities. A model swap retains the task ID, evidence, rule versions, remaining budget and unresolved questions. It does not reset attempts or broaden permissions.

## W2. Investigate and plan

Reproduce the symptom before editing where possible. Record expected versus observed behavior and affected surfaces. Inspect existing checks and nearby code. Separate established cause from hypothesis.

Write a short task graph: deliverables, owners, dependencies, check plan and review requirements. Independent jobs may overlap only when supported by verified scheduling and isolated workspaces. Shared-file changes require coordinated ownership and serial integration checks.

## W3. Implement and verify

Work in isolated branches or candidates. Preserve the baseline and a reviewable diff. Make changes proportionate to the outcome. Do not turn an admin UI fix into an unrelated redesign.

Choose required checks before accepting implementation:

| Change | Required evidence appropriate to scope |
|---|---|
| Calculation bug | Approved expected examples; regression reproducing the defect; boundary/rounding cases; totals consistency; relevant integration checks |
| Admin UI | Before/after views; narrow-screen and desktop checks; keyboard/form/error behavior; data-to-display consistency |
| Shared or high-impact code | Relevant full suite; integration/contract checks; failure paths; migration/rollback evidence where applicable |
| Research or rules | Traceable evidence where claims need it; assumptions and contradictions reviewed; examples that exercise the proposed rules |

For a reproducible code bug, show the regression failing against the baseline and passing against the candidate where feasible. Explain when that comparison is unavailable. Tests added by the author need reviewer inspection of their expected results. Do not remove or weaken a failing test just to obtain a green result; a genuinely obsolete expectation requires documented justification and independent review.

Unrelated baseline failures remain reported. Do not claim the entire suite passed if only selected checks ran. Changes to the candidate after checks invalidate affected evidence; rerun those checks and any required integration gate.

## W4. Independent review

The reviewer receives the task and criteria, governing rules, exact diff/artifacts, source evidence, test commands/results, known limitations and unresolved assumptions. Review must examine correctness, scope, regressions, privacy, maintainability and relevant visual behavior.

Allowed verdicts: accept with stated evidence; request specific changes; or blocked pending information/verification. A material correctness uncertainty cannot be disguised as “accepted with caveats.” Minor follow-ups may be recorded only if the present acceptance criteria are met.

The orchestrator reconciles findings and directs repairs. Reviewer disagreement needs evidence or mailbox escalation; do not keep switching reviewers until one agrees. Final cloud technical acceptance is separate from Kort's authorization to integrate or publish.

## W5. Bounded repair — proposed default

Allow two repair rounds after the initial review failure. Each must test a new, evidence-supported hypothesis. Repeating the same failure without new evidence triggers earlier escalation. The count follows the task across worker and model changes.

A task also needs explicit wall-clock and provider-call caps configured before unattended execution. The two-round limit never overrides a lower resource cap. No universal numeric time/call cap is approved in this draft; record proposed values in the task plan for owner review before enabling unattended operation.

On exhaustion, persist the candidate and evidence, create or update one mailbox item, pause dependent work, and continue independent approved tasks. A blocked worker must release resources safely; it must not hold the GPU while waiting for a human.

## W6. Completion and morning report

Proposed logical statuses: investigating → planned → implementing → verifying → specialist review → cloud acceptance → ready for Kort. Repairs return to implementing. Blocked tasks retain their previous stage and dependency information. Existing runtime status names may map to these; do not create a competing task store.

The morning report contains:
- Requested outcome and short result.
- Exact artifacts/revision and before/after evidence when useful.
- Checks run, outcomes, environments and checks not performed.
- Reviewer findings, repairs and cloud acceptance state.
- Remaining risks and mailbox decisions.
- What is ready for owner review and what remains unpublished.

Delivery of a morning report does not mark unresolved tasks complete. For non-publishing tasks, completion follows their actual acceptance criteria; do not invent a deployment step.
