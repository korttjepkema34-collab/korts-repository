"""Orchestrator v0.

What it does today:
  1. Watches tasks/backlog/. Moves the highest-priority task to tasks/in-progress/.
  2. Asks the orchestrator model (agents/orchestrator.md as system prompt) to turn the task into
     a JSON list of jobs, and enqueues them.
  3. Consumes results from Redis and appends a log line to the task file.
  4. Sends wake-on-LAN when jobs are waiting and the GPU worker heartbeat is missing.

What it does not do yet (see docs/open-questions.md): run the reviewer, dispatch the coder
against the Godot MCP server, run headless tests, merge branches, or reap stale processing jobs.
Those are the next milestones and each is a small, separate function to add here.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import time
from pathlib import Path

from shared import queue as q
from shared.jobs import Job, JobKind, Role, make_job_id

from . import llm, wake

log = logging.getLogger("orchestrator")
REPO = Path(os.environ.get("REPO_ROOT", ".")).resolve()
BACKLOG = REPO / "tasks" / "backlog"
IN_PROGRESS = REPO / "tasks" / "in-progress"
WORKER = os.environ.get("GPU_WORKER_NAME", "gpu")


def task_priority(path: Path) -> int:
    m = re.search(r"^priority:\s*(\d+)", path.read_text(), re.M)
    return int(m.group(1)) if m else 5


def pick_task() -> Path | None:
    tasks = sorted(BACKLOG.glob("*.md"), key=lambda p: (task_priority(p), p.name))
    return tasks[0] if tasks else None


def plan_jobs(task_path: Path) -> list[Job]:
    system = llm.load_role(REPO, "orchestrator")
    context = "\n\n".join([
        "## Task\n" + task_path.read_text(),
        "## Style bible\n" + (REPO / "style" / "style-bible.md").read_text(),
        "## Job schema (shared/jobs.py)\n" + (REPO / "shared" / "jobs.py").read_text(),
        "Respond with a JSON object: {\"jobs\": [ ... ]}. Each job needs kind, role, spec, "
        "output_dir (under assets/incoming/), and a short slug. Omit id and task_id; they are filled in.",
    ])
    task_id = task_path.stem.split("-")[0]
    data = llm.chat_json(system, context)
    raw_jobs = data["jobs"] if isinstance(data, dict) else data
    jobs: list[Job] = []
    for rj in raw_jobs:
        slug = rj.pop("slug", "job")
        rj.pop("id", None)
        rj.pop("task_id", None)
        jobs.append(Job(id=make_job_id(task_id, slug), task_id=task_id, **rj))
    return jobs


def append_log(task_path: Path, line: str) -> None:
    with task_path.open("a") as f:
        f.write(f"\n- {time.strftime('%Y-%m-%d %H:%M')} {line}")


def run_once(r) -> None:
    # 1. Plan new work
    task = pick_task()
    if task:
        dest = IN_PROGRESS / task.name
        shutil.move(str(task), dest)
        log.info("planning %s", dest.name)
        try:
            jobs = plan_jobs(dest)
        except Exception as e:  # keep the loop alive; humans read the task file
            append_log(dest, f"BLOCKED: planning failed: {e}")
            log.exception("planning failed")
            return
        for job in jobs:
            q.enqueue(r, job)
            append_log(dest, f"enqueued {job.kind.value} job {job.id}")
        log.info("enqueued %d jobs for %s", len(jobs), dest.name)

    # 2. Consume results
    while (res := q.next_result(r, timeout_s=1)) is not None:
        task_id = res.job_id.split("-")[0]
        matches = list(IN_PROGRESS.glob(f"{task_id}-*.md"))
        line = f"result {res.status.value} for {res.job_id}: {res.outputs or res.error}"
        for m in matches:
            append_log(m, line)
        log.info(line)
        # TODO: on OK for asset kinds, dispatch reviewer; on error, retry up to max_attempts.

    # 3. Wake the GPU box if needed
    depths = q.queue_depths(r)
    queued = sum(depths.values())
    if wake.maybe_wake(queued, q.worker_alive(r, WORKER)):
        log.info("sent wake-on-LAN to %s (%d jobs queued)", WORKER, queued)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    r = q.connect()
    log.info("orchestrator up; repo=%s model=%s", REPO, os.environ.get("ORCHESTRATOR_MODEL"))
    while True:
        try:
            run_once(r)
        except Exception:
            log.exception("loop error")
        time.sleep(10)


if __name__ == "__main__":
    main()
