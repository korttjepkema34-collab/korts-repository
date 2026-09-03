"""Train handler for `train` jobs: runs one of the recipes in training/ on this GPU.

spec:
  recipe:      sdxl_lora | coder | reviewer
  dataset:     path relative to repo root (assets/training/datasets/<name>), built on the server
  base_model:  optional override of the recipe's default base model
  extra_args:  optional list of extra CLI args for the recipe script
  stale_after_s: how long the orchestrator waits before assuming the job died (hours for training)

The recipe scripts live in training/ and run in their own venv (cfg.tools.training_python), not
the worker's, because torch/unsloth/kohya are heavy and version-sensitive. Outputs land in
job.output_dir (assets/training/models/<name>) and Syncthing carries them to the server.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from shared.jobs import Job, Sidecar

SCRIPTS = {
    "sdxl_lora": "training/train_sdxl_lora.py",
    "coder": "training/train_coder.py",
    "reviewer": "training/train_reviewer.py",
}


def _python(cfg: dict) -> list[str]:
    t = cfg.get("tools", {})
    cmd = t.get("training_cmd")  # e.g. ["wsl", "-e", "/home/me/train/.venv/bin/python"]
    if cmd:
        return list(cmd)
    py = t.get("training_python")  # e.g. C:/studio/training/.venv/Scripts/python.exe
    return [py] if py else [sys.executable]


def run(job: Job, out_dir: Path, cfg: dict) -> tuple[list[str], str | None]:
    spec = job.spec
    recipe = spec.get("recipe")
    if recipe not in SCRIPTS:
        raise ValueError(f"unknown recipe {recipe!r}; known: {sorted(SCRIPTS)}")
    repo = Path(cfg["repo_root"])
    # Path of the repo as the training interpreter sees it (WSL: /mnt/c/studio). Defaults to the same.
    repo_for_trainer = cfg.get("tools", {}).get("training_repo_root") or str(repo)
    script = f"{repo_for_trainer}/{SCRIPTS[recipe]}"
    args = _python(cfg) + [script, "--repo", repo_for_trainer, "--dataset", spec["dataset"],
                           "--out", job.output_dir, "--tools", json.dumps(cfg.get("tools", {}))]
    if spec.get("base_model"):
        args += ["--base-model", spec["base_model"]]
    args += [str(a) for a in spec.get("extra_args", [])]
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "train.log"
    started = time.time()
    with log_path.open("w", encoding="utf-8") as logf:
        logf.write(" ".join(args) + "\n\n")
        logf.flush()
        p = subprocess.run(args, stdout=logf, stderr=subprocess.STDOUT, cwd=str(repo),
                           timeout=int(spec.get("timeout_s", 12 * 3600)))
    if p.returncode != 0:
        tail = log_path.read_text(errors="ignore")[-3000:]
        raise RuntimeError(f"{recipe} training failed (exit {p.returncode}):\n{tail}")
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        raise RuntimeError(f"{recipe} finished but wrote no manifest.json; see {log_path}")
    m = json.loads(manifest.read_text())
    outputs = [str(out_dir / f) for f in m.get("files", [])] + [str(manifest), str(log_path)]
    sc = out_dir / f"{job.id}.json"
    Sidecar(generator=f"training/{recipe}", model=m.get("base_model", "?"), licence=m.get("licence", "see base model"),
            prompt=None, job_id=job.id,
            extra={"dataset": spec["dataset"], "examples": spec.get("examples"),
                   "minutes": round((time.time() - started) / 60, 1), "metrics": m.get("metrics", {})}).write(sc)
    return outputs, str(sc)


def unload(cfg: dict) -> None:
    pass  # each training run is its own process; VRAM is freed when it exits
