# Fix 1: dependent code integration — owner approved

## Before and after

| Before | Prepared change |
|---|---|
| Each job clones the original source | One private task integration branch pins the source revision |
| Downstream jobs see earlier patches only as text | New worker branches contain all previously integrated approved code |
| Individually approved jobs can be marked ready | Combined code must pass configured checks and a final cloud review |
| No stale-base gate for integration | Outdated workers block for rework and renewed testing/review |

## Implementation

The controller uses serial integration. Each worker starts at the latest private task revision;
this includes earlier approved changes even if the jobs were logically independent. It still runs
in its own clone. Actual check results and cloud review precede the durable awaiting_integration
state. Integration commits the exact reviewed diff and fast-forwards the private task branch.
An interrupted commit/fetch/fast-forward can be retried without duplicating that candidate.
Source repositories and GitHub branches are not changed by the runtime integration operation.

After all jobs finish, configured checks run again against combined code. The cloud reviews the
combined diff, job acceptance criteria and check evidence. Failure blocks completion; success
means ready for owner review, not approval to publish. Integration is serial; parallel merge
resolution, autonomous rebasing and whole-plan repair remain separate work.

Existing in-flight legacy candidates without integration evidence are blocked instead of silently
claimed as integrated. Recreate those tasks from reviewed source. The new branch pins committed
source; uncommitted source edits are not included. This remains a Git workspace boundary, not an
OS security sandbox. Fixed context-file selection and host execution are unchanged limitations.

## Owner workflow skill

Created and validated plan-execute-test-review, referenced by AGENTS.md and available locally.
It requires a proportionate plan, execution, meaningful verification, and a concrete review
handoff before publication, deployment or merging. Routine local work does not require repeated
approval. The owner approved publication of the skill and fix to the existing GitHub PR.

## Verification

Real temporary Git repositories exercise inherited code, unchanged original source, pinned task
revision, stale candidates, tampered artifacts, unapproved candidates, repeat integration and
interruption after commit. Pipeline tests exercise two dependent workers, combined evidence,
combined check failure and final cloud rejection. Models are simulated in these tests; live
Windows/Godot/provider qualification still needs the user's PCs.

Observed: `python -m pytest tests -q` — **68 passed**, one existing Pillow deprecation warning.
Assistant-only suite: **54 passed**. Python compilation, diff whitespace checks and workflow skill
format validation passed. No live home-PC test or GitHub publication was performed for this fix.

## Owner decision

Owner approved this fix and workflow skill for publication to the existing PR. This approval
does not merge the PR into main or deploy the assistant to the home PCs.
