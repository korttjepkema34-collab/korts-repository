"""Thin Redis helpers used by both sides. Reliable-queue pattern: claim with BRPOPLPUSH so a
crashed worker leaves the job in `jobs:<kind>:processing` for the orchestrator to reap."""
from __future__ import annotations

import os
from typing import Optional

import redis

from .jobs import RESULTS_KEY, Job, JobKind, Result, heartbeat_key, status_key


def connect() -> redis.Redis:
    return redis.Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD") or None,
        decode_responses=True,
        socket_keepalive=True,
    )


def enqueue(r: redis.Redis, job: Job) -> None:
    r.lpush(job.queue_key, job.to_json())


def claim(r: redis.Redis, kinds: list[JobKind], timeout_s: int = 30) -> Optional[Job]:
    """Block up to timeout_s for a job of any listed kind. Returns None on timeout."""
    for kind in kinds:
        raw = r.rpoplpush(f"jobs:{kind.value}", f"jobs:{kind.value}:processing")
        if raw:
            return Job.from_json(raw)
    # Nothing waiting: block on the first kind only (Redis has no multi-key BRPOPLPUSH).
    # The worker loops, so other kinds get checked every timeout_s.
    keys = [f"jobs:{k.value}" for k in kinds]
    popped = r.brpop(keys, timeout=timeout_s)
    if not popped:
        return None
    _, raw = popped
    job = Job.from_json(raw)
    r.lpush(job.processing_key, raw)
    return job


def complete(r: redis.Redis, job: Job, result: Result) -> None:
    r.lrem(job.processing_key, 1, job.to_json())
    r.lpush(RESULTS_KEY, result.to_json())


def next_result(r: redis.Redis, timeout_s: int = 30) -> Optional[Result]:
    popped = r.brpop([RESULTS_KEY], timeout=timeout_s)
    if not popped:
        return None
    return Result.from_json(popped[1])


def heartbeat(r: redis.Redis, worker: str, status: str, ttl_s: int = 90) -> None:
    r.set(heartbeat_key(worker), "1", ex=ttl_s)
    r.set(status_key(worker), status)


def worker_alive(r: redis.Redis, worker: str) -> bool:
    return r.exists(heartbeat_key(worker)) == 1


def queue_depths(r: redis.Redis) -> dict[str, int]:
    return {k.value: r.llen(f"jobs:{k.value}") for k in JobKind}
