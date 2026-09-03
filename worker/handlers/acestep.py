"""Audio handler for `music` (ACE-Step) and `sfx` (Stable Audio Open) jobs.

Both are expected behind one small local API at cfg.tools.acestep:
  POST /music {prompt, duration_s, bpm?, lyrics?, seed?} -> {"files": [...], "model": "..."}
  POST /sfx   {prompt, duration_s, count?, seed?}         -> {"files": [...], "model": "..."}
That wrapper is worker/services/audio_api.py (start it with run-audio-api.ps1). This handler
fails clearly if it is not running.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import requests

from shared.jobs import Job, JobKind, Sidecar


def run(job: Job, out_dir: Path, cfg: dict) -> tuple[list[str], str | None]:
    base = cfg["tools"]["acestep"].rstrip("/")
    spec = job.spec
    endpoint = "music" if job.kind == JobKind.MUSIC else "sfx"
    try:
        r = requests.post(f"{base}/{endpoint}", json=spec, timeout=spec.get("timeout_s", 900))
    except requests.ConnectionError as e:
        raise RuntimeError("audio API not running; see worker/services/ (todo)") from e
    r.raise_for_status()
    data = r.json()
    outputs = []
    for i, f in enumerate(data["files"]):
        dst = out_dir / f"{job.id}-{i:02d}{Path(f).suffix}"
        shutil.copy2(f, dst)
        outputs.append(str(dst))
    sc = out_dir / f"{job.id}.json"
    licence = "Apache-2.0" if endpoint == "music" else "Stability Community (verify)"
    Sidecar(generator="acestep" if endpoint == "music" else "stable-audio-open",
            model=data.get("model", endpoint), licence=licence, prompt=spec.get("prompt"),
            seed=spec.get("seed"), job_id=job.id,
            extra={"duration_s": spec.get("duration_s"), "loop_points": data.get("loop_points")}).write(sc)
    return outputs, str(sc)


def unload(cfg: dict) -> None:
    base = cfg["tools"]["acestep"].rstrip("/")
    try:
        requests.post(f"{base}/unload", timeout=30)
    except requests.RequestException:
        pass
