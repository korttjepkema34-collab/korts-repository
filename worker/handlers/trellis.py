"""TRELLIS / Hunyuan3D handler for `model3d` jobs.

Expects a small local API (worker/services/trellis_api.py, not written yet) that accepts
POST /generate {image_path | prompt, texture: bool} and returns {"glb": "<path>", "polys": N}.
Until that exists this handler raises so the orchestrator sees a clear error.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import requests

from shared.jobs import Job, Sidecar


def run(job: Job, out_dir: Path, cfg: dict) -> tuple[list[str], str | None]:
    base = cfg["tools"]["trellis"].rstrip("/")
    spec = job.spec
    payload = {"texture": spec.get("texture", False), "target_polys": spec.get("target_polys", 5000)}
    if spec.get("image"):
        payload["image_path"] = str(Path(cfg["repo_root"]) / spec["image"])
    else:
        payload["prompt"] = spec["prompt"]
    try:
        r = requests.post(f"{base}/generate", json=payload, timeout=spec.get("timeout_s", 1200))
    except requests.ConnectionError as e:
        raise RuntimeError("TRELLIS API not running; see worker/services/ (todo)") from e
    r.raise_for_status()
    data = r.json()
    dst = out_dir / f"{job.id}.glb"
    shutil.copy2(data["glb"], dst)
    sc = out_dir / f"{job.id}.json"
    Sidecar(generator="trellis", model=data.get("model", "trellis-2"), licence="MIT",
            prompt=spec.get("prompt"), job_id=job.id,
            extra={"source_image": spec.get("image"), "polys": data.get("polys"),
                   "textured": payload["texture"]}).write(sc)
    return [str(dst)], str(sc)


def unload(cfg: dict) -> None:
    base = cfg["tools"]["trellis"].rstrip("/")
    try:
        requests.post(f"{base}/unload", timeout=30)
    except requests.RequestException:
        pass
