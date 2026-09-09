---
name: measure-performance
description: "Identify and verify a performance bottleneck using comparable measurements."
---

# Measure Performance

Assigned roles: Optimizer.

## Tools and readiness

Proposed browser/Godot profiler and benchmark runner; measurements can be supplied as artifacts now.

These instructions do not install tools or grant tool access. If required evidence cannot be
obtained with the connected adapter, mark it missing and return a bounded plan or blocker.

## Workflow

Capture workload, hardware, build, baseline metric and variability. Identify the measured bottleneck before editing. Compare the same workload after one change and check correctness regressions. Report sample count, before/after values and uncertainty; distinguish faster measured performance from theoretical optimization.
