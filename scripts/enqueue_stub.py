#!/usr/bin/env python3
"""Push one stub job straight onto the queue, bypassing the LLM. For testing the worker.
Usage: from repo root, with server/.env sourced:  python3 scripts/enqueue_stub.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared import queue as q
from shared.jobs import Job, JobKind, Role, make_job_id

r = q.connect()
job = Job(id=make_job_id("000", "stub"), task_id="000", kind=JobKind.STUB, role=Role.ORCHESTRATOR,
          spec={"hello": "world"}, output_dir="assets/incoming/000-stub")
q.enqueue(r, job)
print("enqueued", job.id, "depths:", q.queue_depths(r))
