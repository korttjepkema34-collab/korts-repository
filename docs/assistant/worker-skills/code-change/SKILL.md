---
name: code-change
description: "Produce a bounded code change with reproducible verification in an isolated project workspace."
---

# Code Change

Assigned roles: Backend / general coding / game coding.

## Tools and readiness

Existing code-sandbox adapter and owner-configured checks; adaptive file discovery and cloud execution are pending.

These instructions do not install tools or grant tool access. If required evidence cannot be
obtained with the connected adapter, mark it missing and return a bounded plan or blocker.

## Workflow

Read supplied source and acceptance criteria. Respect allowed paths; return full replacements in the adapter JSON schema. Tests come from trusted configuration, not commands invented by a worker. Use actual check output for repair, identify missing context, and submit the exact candidate diff for cloud review. A passing import is not proof of behavior; no self-approval or implied deployment.
