"""GPU worker daemon for the gaming PC.

Pulls jobs from the server's Redis over Tailscale, dispatches to a handler per job kind, writes
outputs under assets/incoming/<job-id>/ (Syncthing carries them to the server), and posts a
Result. Sends a heartbeat every loop so the orchestrator knows whether to wake this machine.

Run: python worker.py   (from the worker/ directory, with config.yaml present)
"""
from __future__ import annotations

import logging
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `shared` imports from the repo root

from shared import queue as q  # noqa: E402
from shared.jobs import Job, JobKind, Result, ResultStatus  # noqa: E402

from handlers import HANDLERS  # noqa: E402

log = logging.getLogger("worker")


def load_config() -> dict:
    cfg_path = HERE / "config.yaml"
    if not cfg_path.exists():
        sys.exit("worker/config.yaml missing; copy config.example.yaml and edit it")
    return yaml.safe_load(cfg_path.read_text())


def gaming_mode(cfg: dict) -> bool:
    return (HERE / cfg.get("gaming_mode_file", "GAMING_MODE")).exists()


def run_job(job: Job, cfg: dict) -> Result:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    handler = HANDLERS.get(job.kind)
    if handler is None:
        return Result(job_id=job.id, status=ResultStatus.SKIPPED, worker=cfg["worker_name"],
                      started_at=started, error=f"no handler for kind {job.kind.value}")
    out_dir = Path(cfg["repo_root"]) / job.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        outputs, sidecar = handler.run(job, out_dir, cfg)
        return Result(job_id=job.id, status=ResultStatus.OK, worker=cfg["worker_name"],
                      started_at=started,
                      outputs=[Path(p).relative_to(cfg["repo_root"]).as_posix() for p in outputs],
                      sidecar=Path(sidecar).relative_to(cfg["repo_root"]).as_posix() if sidecar else None)
    except Exception as e:  # handlers raise on tool errors, OOM, timeouts
        log.exception("job %s failed", job.id)
        return Result(job_id=job.id, status=ResultStatus.ERROR, worker=cfg["worker_name"],
                      started_at=started, error=f"{type(e).__name__}: {e}")


def run_job_with_heartbeat(r, name: str, job: Job, cfg: dict) -> Result:
    """Jobs run for minutes (images) to hours (training); keep the heartbeat alive meanwhile so
    the orchestrator does not think the machine is off and send wake packets at it."""
    box: dict = {}
    t = threading.Thread(target=lambda: box.__setitem__("result", run_job(job, cfg)), daemon=True)
    t.start()
    while t.is_alive():
        q.heartbeat(r, name, f"busy:{job.kind.value}")
        t.join(timeout=30)
    return box["result"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    cfg = load_config()
    import os
    os.environ.setdefault("REDIS_HOST", str(cfg["redis"]["host"]))
    os.environ.setdefault("REDIS_PORT", str(cfg["redis"].get("port", 6379)))
    os.environ.setdefault("REDIS_PASSWORD", str(cfg["redis"].get("password", "")))
    r = q.connect()
    kinds = [JobKind(k) for k in cfg["kinds"]]
    name = cfg["worker_name"]
    log.info("worker %s up; kinds=%s", name, [k.value for k in kinds])

    current_kind: JobKind | None = None
    while True:
        if gaming_mode(cfg):
            if current_kind is not None:
                log.info("gaming mode on; freeing VRAM")
                for h in HANDLERS.values():
                    h.unload(cfg)
                current_kind = None
            q.heartbeat(r, name, "gaming")
            time.sleep(cfg.get("poll_timeout_s", 30))
            continue

        if r.exists("gpu:llm_lock"):  # the coder is using this GPU's LLM; do not load an image model on top of it
            if current_kind is not None:
                HANDLERS[current_kind].unload(cfg); current_kind = None
            q.heartbeat(r, name, "llm-lock")
            time.sleep(10)
            continue
        q.heartbeat(r, name, "idle")
        # Prefer the kind whose model is already loaded to avoid thrashing.
        order = ([current_kind] if current_kind else []) + [k for k in kinds if k != current_kind]
        job = q.claim(r, order, timeout_s=cfg.get("poll_timeout_s", 30))
        if job is None:
            continue
        if job.kind != current_kind and current_kind is not None:
            HANDLERS[current_kind].unload(cfg)
        current_kind = job.kind
        q.heartbeat(r, name, f"busy:{job.kind.value}")
        log.info("running %s (%s)", job.id, job.kind.value)
        result = run_job_with_heartbeat(r, name, job, cfg)
        q.complete(r, job, result)
        log.info("done %s -> %s", job.id, result.status.value)


if __name__ == "__main__":
    main()
