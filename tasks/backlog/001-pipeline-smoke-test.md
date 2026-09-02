# 001 Pipeline smoke test
priority: 1
roles: orchestrator

## Goal
Prove the server can enqueue a job, the gaming PC worker can pull it over Tailscale, and the
result and output file make it back.

## Acceptance
- A `stub` job is enqueued by the orchestrator.
- The worker on `gpu` runs it and `assets/incoming/001-*/stub.txt` appears on the server via Syncthing.
- A result line is appended to this task file.

## Notes
Emit exactly one job of kind `stub` with spec `{"hello": "world"}` and output_dir
`assets/incoming/001-smoke`.
