> Owner approved version 0.2 for publication on 2026-09-09. This is governing policy/design, not evidence that runtime controls are implemented. Proposed defaults in the reviewed text are adopted as design defaults; task-specific budgets still require configuration.

# Document 4 — Kort’s Mailbox Rules

## M1. Purpose and storage

The mailbox is a durable private queue of decisions, blockers and review-ready results. The pixel office will display it later; mailbox correctness must not depend on animations or the browser being open. Persist records through the authoritative assistant store, not a separate decorative inbox.

## M2. When to create an item

Create an item for missing business rules, unresolved conflicting evidence, exhausted repair/budget, unavailable required review, missing permission or an action awaiting Kort's approval. Routine reversible choices do not require mail. Aggregate routine completion updates into the morning report; preserve important decisions as individually actionable records.

Proposed priorities:
- **Urgent:** suspected active harm such as data corruption or exposed secrets. Stop affected activity and preserve evidence. External alerts need a separately authorized destination and channel; the office mailbox alone cannot guarantee immediate notice.
- **Blocked:** an answer is needed to resume specific work. Continue unrelated approved jobs.
- **Review:** a concrete result awaits Kort's review or publication decision.
- **FYI:** useful progress or a proposed improvement with no immediate decision required.

## M3. Required item fields

Stable item ID; project/task IDs; priority; concise subject; creation/update times; current status; blocked action and impact; facts versus assumptions; attempts and evidence references; recommended option and alternatives; exact question or approval requested; artifact revision; applicable rule versions; dependent tasks; originating specialist; sensitivity; owner response and resolution history.

Use idempotent creation keyed to task plus decision type so retries do not spam the mailbox. Update an existing unresolved item when new evidence concerns the same decision. Preserve the historical record.

## M4. Decision lifecycle

Open → owner answered → validating response → resolved, deferred or reopened. Reading an item is not approval. Silence is not approval. A defer response keeps the affected action paused. Store the exact response with its scope and timestamp.

Before resuming, verify the answer resolves the question, the candidate revision remains current, permissions still apply, dependencies are valid and relevant checks still pass. An approval for an old candidate does not authorize a materially changed one. If new evidence invalidates the decision basis, reopen with an explanation.

Consume a decision once for its intended action. Use a persistent action ID and reconcile uncertain outcomes before retrying external effects. A restart must not repeat a deployment or communication merely because the mailbox still contains an approval.

## M5. Example — hypothetical business blocker

Subject: Calculation rule needed before completing invoice fix.
Priority: Blocked.
Finding: The displayed total and recorded total disagree for a supplied test example; the intended order of discount and tax operations has not been established.
Tried: Reproduced the discrepancy, traced both paths, located conflicting assumptions, prepared failing regression examples. No legal or business-policy conclusion has been made.
Recommendation: Confirm the authoritative calculation specification and representative expected examples before changing shared totals logic.
Question for Kort: Which approved rule/source should govern this calculation?
Paused: calculation candidate and dependent reports. Continues: unrelated, isolated admin layout work.
Evidence: private references to reproduction and candidate; no customer data copied into public GitHub.
