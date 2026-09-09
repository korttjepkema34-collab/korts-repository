---
name: plan-execute-test-review
description: Apply the owner's plan, execute, test, and review workflow when creating or changing work, including assistant fixes and project deliverables.
---

# Plan, execute, test, review

1. State the intended outcome, scope, approach and what will establish correctness. Use a brief plan for small work and explicit checkpoints for substantial work.
2. Execute the authorized work to a concrete, reviewable result. Resolve routine implementation choices without repeatedly asking for permission.
3. Verify the result with meaningful checks suited to the deliverable. Fix observed failures and repeat affected checks. Distinguish passing tests from untested assumptions and unavailable live validation.
4. Present what changed, the evidence, limitations and the actual result for the owner's review. Provide a before/after comparison when useful.
5. Wait for the owner's review before publishing, deploying or merging this result. Apply requested edits and retest affected behavior. An explicit instruction to publish the reviewed result authorizes that action; do not ask again.

Local edits, tests and local Git checkpoints are preparation, not publication. Do not interpret a request to begin a fix as approval to publish its finished result. This workflow does not require approval of the initial plan unless the owner asks for it.
