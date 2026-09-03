# 08 - Job schema

Source of truth: `shared/jobs.py` (pydantic models) and `shared/schema/job.schema.json`.

## Job

```json
{
  "id": "007-player-idle-sprite-a1b2c3",
  "task_id": "007",
  "kind": "image",
  "role": "artist-2d",
  "priority": 5,
  "created_at": "2026-09-02T12:00:00Z",
  "attempt": 1,
  "max_attempts": 3,
  "spec": {
    "prompt": "pixel art idle pose of the player character ...",
    "negative_prompt": "blurry, photo, text",
    "workflow": "sdxl_pixelart_ipadapter",
    "references": ["style/references/player-concept.png"],
    "width": 512,
    "height": 512,
    "seed": null,
    "count": 4
  },
  "output_dir": "assets/incoming/007-player-idle-sprite",
  "notes": "Reviewer rejected attempt 1: colours too saturated vs palette."
}
```

`kind` decides which Redis list the job goes on (`jobs:image`) and which handler runs it.

| kind | handler | spec fields |
|---|---|---|
| `stub` | `handlers/stub.py` | anything; echoes back. For testing the pipeline. |
| `image` | `handlers/comfyui.py` | prompt, negative_prompt, workflow, references, width, height, seed, count |
| `music` | `handlers/acestep.py` | prompt, duration_s, bpm, lyrics (optional), seed |
| `sfx` | `handlers/acestep.py` (Stable Audio) | prompt, duration_s, seed, count |
| `train` | `handlers/train.py` | recipe (sdxl_lora, coder, reviewer), dataset (assets/training/datasets/<name>), base_model, extra_args, stale_after_s |
| `code` | not a worker job; the orchestrator dispatches the coder agent directly | spec, branch, files |
| `review` | not a worker job; orchestrator runs the reviewer model on the server | path, criteria |

## Result

```json
{
  "job_id": "007-player-idle-sprite-a1b2c3",
  "status": "ok",
  "worker": "gpu",
  "started_at": "...",
  "finished_at": "...",
  "outputs": ["assets/incoming/007-player-idle-sprite/0001.png", "..."],
  "sidecar": "assets/incoming/007-player-idle-sprite/0001.json",
  "error": null
}
```

`status` is `ok`, `error`, or `skipped` (worker does not handle this kind).

## Sidecar JSON (one per generated file)

```json
{
  "generator": "comfyui",
  "model": "sdxl-1.0 + pixelart-lora-v3",
  "licence": "CreativeML OpenRAIL++",
  "prompt": "...",
  "negative_prompt": "...",
  "seed": 123456,
  "job_id": "...",
  "review": null
}
```

The reviewer fills `review` with `{"verdict": "approved|rejected", "reason": "...", "by": "qwen3-vl"}`.

## Redis keys

| Key | Type | Purpose |
|---|---|---|
| `jobs:<kind>` | list | Pending jobs, JSON strings. `LPUSH` to add, `BRPOPLPUSH` to claim. |
| `jobs:<kind>:processing` | list | Claimed jobs. Removed on completion. Reaped by orchestrator if stale. |
| `results` | list | Result JSON strings. Orchestrator `BRPOP`s. |
| `worker:<name>:heartbeat` | string with TTL | Set every 30 s. Missing means the worker is offline. |
| `worker:<name>:status` | string | `idle`, `busy:<kind>`, `gaming`. |
