"""Per-task job bookkeeping, persisted to tasks/.state.json so restarts do not lose track."""
from __future__ import annotations

import json
from pathlib import Path


class State:
    def __init__(self, repo: Path):
        self.path = repo / "tasks" / ".state.json"
        self.data: dict = json.loads(self.path.read_text()) if self.path.exists() else {"tasks": {}, "jobs": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2))

    # jobs ------------------------------------------------------------
    def add_job(self, task_id: str, job_id: str, kind: str, attempt: int = 1) -> None:
        self.data["jobs"][job_id] = {"task": task_id, "kind": kind, "status": "pending", "attempt": attempt}
        self.data["tasks"].setdefault(task_id, {"jobs": [], "planned_at": None, "coder_runs": 0})
        if job_id not in self.data["tasks"][task_id]["jobs"]:
            self.data["tasks"][task_id]["jobs"].append(job_id)
        self.save()

    def set_job(self, job_id: str, status: str, **extra) -> None:
        j = self.data["jobs"].setdefault(job_id, {})
        j["status"] = status
        j.update(extra)
        self.save()

    def job(self, job_id: str) -> dict:
        return self.data["jobs"].get(job_id, {})

    def task_jobs(self, task_id: str) -> list[dict]:
        ids = self.data["tasks"].get(task_id, {}).get("jobs", [])
        return [dict(id=i, **self.data["jobs"][i]) for i in ids if i in self.data["jobs"]]

    def in_flight(self) -> int:
        return sum(1 for j in self.data["jobs"].values() if j.get("status") in ("pending", "running"))

    def task_terminal(self, task_id: str) -> bool:
        jobs = self.task_jobs(task_id)
        return bool(jobs) and all(j["status"] in ("approved", "failed", "ok") for j in jobs)

    def task_succeeded(self, task_id: str) -> bool:
        return all(j["status"] in ("approved", "ok") for j in self.task_jobs(task_id))

    def mark_planned(self, task_id: str, when: str) -> None:
        self.data["tasks"].setdefault(task_id, {"jobs": [], "coder_runs": 0})["planned_at"] = when
        self.save()
