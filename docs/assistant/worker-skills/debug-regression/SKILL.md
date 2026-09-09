---
name: debug-regression
description: "Diagnose a reproducible failure, direct a repair and verify it does not recur."
---

# Debug Regression

Assigned roles: Debugger / cloud problem solver.

## Tools and readiness

Logs, source search, configured reproduction/regression commands; tools available only through connected adapters.

These instructions do not install tools or grant tool access. If required evidence cannot be
obtained with the connected adapter, mark it missing and return a bounded plan or blocker.

## Workflow

Separate symptom, competing hypotheses and confirmed cause. Reproduce with exact input/version, choose a discriminating check, and change the smallest supported cause. Re-run reproduction and affected behavior tests. Preserve failed attempts and actual outputs. After the repair budget, report blocker, evidence, prevention and a candidate reusable skill; never claim resolution from a plausible explanation.
