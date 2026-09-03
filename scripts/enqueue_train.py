#!/usr/bin/env python3
"""Build a dataset from the studio's data and queue one training job for the GPU worker.

    python scripts/enqueue_train.py sdxl_lora
    python scripts/enqueue_train.py coder --base-model unsloth/Qwen2.5-Coder-7B-Instruct
    python scripts/enqueue_train.py reviewer
    python scripts/enqueue_train.py --dry-run coder      # just build the dataset and report counts

Run on the server from the repo root with server/.env present. The worker picks the job up
when the gaming PC is on and not in gaming mode; the result lands in assets/training/models/.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "server"))

env = REPO / "server" / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), re.split(r"\s+#", v, 1)[0].strip())
os.environ.setdefault("ORCHESTRATOR_MODEL", "unused")

from orchestrator import training  # noqa: E402
from orchestrator.state import State  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("recipe", choices=training.RECIPES)
ap.add_argument("--base-model", default=None)
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--extra", nargs="*", default=[], help="extra args for the recipe script, e.g. --steps 1200")
a = ap.parse_args()

print("signals:", training.signals(REPO))
extra = {}
if a.base_model:
    extra["base_model"] = a.base_model
if a.extra:
    extra["extra_args"] = a.extra
job = training.make_job(REPO, a.recipe, extra)
print(f"dataset: {job.spec['dataset']} ({job.spec['examples']} examples)")
if a.dry_run:
    sys.exit(0)
from shared import queue as q  # noqa: E402
r = q.connect()
st = State(REPO)
st.add_job(job.task_id, job.id, job.kind.value)
st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=1, attempt=1, task=job.task_id, kind=job.kind.value)
q.enqueue(r, job)
print("queued", job.id, "-> output", job.output_dir, "| depths:", q.queue_depths(r))
