# Qualification reliability candidate

Task: qualification-reliability. Base: `d174dd7`. Branch: `codex/qualification-reliability`.
Owner scope: continue assistant reliability work; leave Claude's sprites/characters alone.
Candidate lives in an isolated checkout. No artwork, media configuration or static frontend files changed.

## Result

- Benchmark and production requests now share the same request builder, including endpoint checks,
  persona, thinking setting, context/output limits, and timeout. Benchmark-only forced JSON and
  temperature settings were removed rather than silently changing production behavior.
- Reports and promoted qualifications carry a fingerprint of the effective request plus adapter,
  device and skill references. Promotion rejects old/mismatched evidence. When qualification is
  required, the runner waits if the profile has changed. The dashboard reports the same effective
  qualification and does not show a stale idle worker as available.
- Cloud qualification and catalog reports save the exact synthetic question on success and failure.
  Randomized arithmetic questions can therefore be independently recomputed from retained evidence.
- Benchmark age uses an explicitly UTC timestamp and rejects future dates.

## Verification

**VERIFIED offline:** Before implementation, the four new regression tests reproduced the defects:
request mismatch, acceptance of changed personas, reuse of stale qualification at execution, and
missing synthetic questions in saved reports. They produced eleven assertion failures across
subtests and one missing-field error. After implementation, all five regression tests pass,
including the additional dashboard qualification test.

**VERIFIED offline:** The initial complete assistant suite ran 136 tests: 135 passed, one skipped.
After the dashboard correction, all 13 HTTP dashboard tests passed.

**VERIFIED final repository gate:** `python -m pytest tests -q` passed with 150 passed, one skipped,
and ten passing subtests. One existing Pillow deprecation warning remains in a validator test;
no artwork or validator implementation was changed. Candidate leak scan, including new files,
reported no findings; `git diff --check` passed.

**VERIFIED independent review:** A separate reviewer requested the dashboard correction, then
independently ran all five new regression tests and accepted the corrected candidate with the
stated migration and evidence limits. This is code review acceptance, not live model qualification.

**VERIFIED server baseline:** WSL reports source revision `d174dd7` and all four assistant/Ollama
services active. Doctor passes with the service environment loaded. Stored health reports were
healthy, with individual timestamps; they are not all new probes.

Live CPU-only acceptance is recorded in the handoff session entry when complete.
No GPU inference is part of this candidate's acceptance probe.

## Rollout and rollback

This candidate is prepared for owner review, not deployed or published. Before integration, compare
against Claude's current branch and apply only the assistant reliability changes; the small
`assistant/web.py` change is backend status reporting and must be reconciled if Claude edits that file.

Existing private qualifications have no fingerprint and will no longer authorize local jobs when
`require_qualified_workers` is enabled. Run fresh benchmarks with the candidate against the exact
private profiles, then qualify only passing roles. Do not copy a fingerprint onto old evidence or
turn off the qualification requirement to avoid the migration. Coordinate GPU benchmarks with
Claude/gaming before starting them. Until then, preserve the deployed version.

Take a private runtime backup before an approved rollout. Rollback must restore the pre-rollout
source and matching private worker configuration together, rather than mixing evidence formats.

## Evidence limits

This is a synthetic request/format smoke qualification, not proof of production task competence.
The fingerprint tracks profile settings and skill references, not the contents of skill files,
mutable model weights, Ollama versions, or job-specific prompts. Those changes still require
appropriate live checks. Runtime fingerprint matching does not introduce a new automatic expiry
policy; the seven-day age check applies when promoting a benchmark.

The prior Ling comparison measured equal scores on one small test run. It does not establish that
the variants are generally interchangeable. No route promotions or financial calculation tools
are implemented by this change.
