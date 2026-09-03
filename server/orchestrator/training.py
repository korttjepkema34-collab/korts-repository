"""Self-improvement scheduling. The studio's own outputs become training data
(server/orchestrator/traces.py); this module decides when there is enough new data to be worth a
GPU run, builds the dataset on the server (CPU work), and queues a `train` job for the GPU
worker. Off unless AUTO_TRAIN=1. Thresholds are env vars. See docs/15-training.md.

Manual path: `python scripts/enqueue_train.py sdxl_lora` does the same on demand.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path

from shared.jobs import Job, JobKind, Role, make_job_id

from . import traces

log = logging.getLogger("training")

RECIPES = ("sdxl_lora", "coder", "reviewer")
TRAIN_TASK_ID = "train"


def _state_path(repo: Path) -> Path:
    return repo / "data" / "training" / "state.json"


def load_state(repo: Path) -> dict:
    p = _state_path(repo)
    return json.loads(p.read_text()) if p.exists() else {"last": {}, "models": {}}


def save_state(repo: Path, st: dict) -> None:
    p = _state_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=2))


def _builder(repo: Path):
    """Import training/build_datasets.py from the repo root without needing it on sys.path."""
    src = repo / "training" / "build_datasets.py"
    spec = importlib.util.spec_from_file_location("build_datasets", src)
    mod = importlib.util.module_from_spec(spec)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def approved_image_count(repo: Path) -> int:
    d = repo / "assets" / "approved"
    return sum(1 for p in d.rglob("*") if p.suffix.lower() in (".png", ".webp") ) if d.exists() else 0


def signals(repo: Path) -> dict[str, int]:
    c = traces.counts(repo)
    return {"sdxl_lora": approved_image_count(repo), "coder": c["coder_passed"], "reviewer": c["overrides"]}


def thresholds() -> dict[str, tuple[int, int]]:
    """(minimum total, minimum growth since last train) per recipe."""
    e = os.environ.get
    return {
        "sdxl_lora": (int(e("AUTO_TRAIN_MIN_IMAGES", "40")), int(e("AUTO_TRAIN_IMAGE_GROWTH", "20"))),
        "coder": (int(e("AUTO_TRAIN_MIN_CODER_PASSES", "150")), int(e("AUTO_TRAIN_CODER_GROWTH", "75"))),
        "reviewer": (int(e("AUTO_TRAIN_MIN_OVERRIDES", "100")), int(e("AUTO_TRAIN_OVERRIDE_GROWTH", "50"))),
    }


def make_job(repo: Path, recipe: str, extra_spec: dict | None = None) -> Job:
    """Build the dataset for `recipe` into assets/training/datasets/ (Syncthing carries it to the
    GPU box) and return the queue job. Raises if the dataset is empty."""
    if recipe not in RECIPES:
        raise ValueError(f"unknown recipe {recipe}; choose from {RECIPES}")
    stamp = time.strftime("%Y%m%d-%H%M")
    name = f"{recipe}-{stamp}"
    dataset_rel = f"assets/training/datasets/{name}"
    n = _builder(repo).build(repo, recipe, repo / dataset_rel)
    if n == 0:
        raise RuntimeError(f"no training examples for {recipe}; nothing to train on yet")
    stale = int(os.environ.get("TRAIN_STALE_SECONDS", str(12 * 3600)))
    spec = {"recipe": recipe, "dataset": dataset_rel, "examples": n,
            "stale_after_s": stale,            # orchestrator gives up after this
            "timeout_s": max(600, stale - 600)}  # worker kills the run a little earlier, so the two agree
    spec.update(extra_spec or {})
    # Ordering note: the queue is FIFO per kind; train jobs go last because `train` is last in the
    # worker's `kinds` list, not because of Job.priority (which nothing reads yet).
    return Job(id=make_job_id(TRAIN_TASK_ID, recipe), task_id=TRAIN_TASK_ID, kind=JobKind.TRAIN,
               role=Role.TRAINER, max_attempts=1, spec=spec,
               output_dir=f"assets/training/models/{name}")


def auto_jobs(repo: Path, state) -> list[Job]:
    """Called once a day by the orchestrator. Returns 0 or 1 jobs (one GPU run per day at most)."""
    if os.environ.get("AUTO_TRAIN", "0") != "1":
        return []
    for j in state.data["jobs"].values():
        if j.get("kind") == "train" and j.get("status") in ("pending", "running"):
            return []  # one at a time
    st = load_state(repo)
    sig = signals(repo)
    for recipe, (min_total, min_growth) in thresholds().items():
        have = sig[recipe]
        last = st["last"].get(recipe, {}).get("count", 0)
        if have >= min_total and have - last >= min_growth:
            try:
                job = make_job(repo, recipe)
            except Exception as e:
                log.warning("auto-train %s skipped: %s", recipe, e)
                continue
            st["last"][recipe] = {"count": have, "job": job.id, "at": time.strftime("%Y-%m-%d %H:%M")}
            save_state(repo, st)
            return [job]
    return []


def on_trained(repo: Path, spec: dict, outputs: list[str], ev) -> None:
    """A train job finished. Record where the model landed. Activation is deliberate and manual
    (or via scripts/activate_model.py): a bad fine-tune must never silently replace a good model."""
    st = load_state(repo)
    recipe = spec.get("recipe", "?")
    st["models"].setdefault(recipe, []).append({"outputs": outputs, "spec": spec, "at": time.strftime("%Y-%m-%d %H:%M")})
    save_state(repo, st)
    latest = repo / "data" / "training" / "latest.json"
    latest.write_text(json.dumps(st["models"], indent=2))
    ev(f"training finished for {recipe}: {outputs[:2]} (activate with scripts/activate_model.py {recipe})")
    try:
        with (repo / "docs" / "decisions.md").open("a") as f:
            f.write(f"| {time.strftime('%Y-%m-%d')} | (auto) trained {recipe} on {spec.get('examples')} examples -> {outputs[0] if outputs else '?'} ; not yet activated | studio self-improvement, docs/15-training.md |\n")
    except OSError:
        pass
