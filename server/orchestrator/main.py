"""Orchestrator: the unattended studio loop.

Designed to run for days with no human input. Every cycle:
  1. Reap stale GPU jobs (worker died mid-job) back onto the queue.
  2. Consume results: review assets, retry failures with notes, mark jobs terminal.
  3. Run code jobs in-process (file-based coder + headless Godot gate + merge).
  4. Close tasks whose jobs are all terminal: done/ on success, deferred/ on failure.
  5. Plan the next backlog task if there is capacity.
  6. If the backlog is empty, generate new tasks from the design doc.
  7. Once a day: retry deferred tasks with the escalation model, write the report, commit.
  8. Wake the gaming PC if GPU jobs are waiting and it is silent.

Rails: per-job attempt cap, per-task coder-run cap, in-flight cap, daily task-generation cap,
disk-space floor, and every decision written to the task file so the human can read the story.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import time
from pathlib import Path

from shared import queue as q
from shared.jobs import Job, JobKind, ResultStatus

from . import checks, coder, gitops, planner, report, reviewer, wake
from .state import State

log = logging.getLogger("orchestrator")
REPO = Path(os.environ.get("REPO_ROOT", ".")).resolve()
T = REPO / "tasks"
BACKLOG, IN_PROGRESS, DONE, DEFERRED = T / "backlog", T / "in-progress", T / "done", T / "deferred"
WORKER = os.environ.get("GPU_WORKER_NAME", "gpu")
MAX_INFLIGHT = int(os.environ.get("MAX_INFLIGHT_JOBS", "12"))
MAX_CODER_RUNS_PER_TASK = int(os.environ.get("MAX_CODER_RUNS_PER_TASK", "3"))
MAX_GENERATED_TASKS_PER_DAY = int(os.environ.get("MAX_GENERATED_TASKS_PER_DAY", "10"))
STALE_JOB_S = int(os.environ.get("STALE_JOB_SECONDS", "5400"))
MIN_FREE_GB = float(os.environ.get("MIN_FREE_GB", "20"))
LOOP_S = int(os.environ.get("LOOP_SECONDS", "20"))

EVENTS: list[str] = []
_generated_today = {"day": "", "n": 0}
_last_daily = 0.0


def ev(msg: str) -> None:
    log.info(msg)
    EVENTS.append(f"{time.strftime('%H:%M')} {msg}")


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def append_log(task_path: Path, line: str) -> None:
    with task_path.open("a") as f:
        f.write(f"\n- {stamp()} {line}")


def task_file(task_id: str) -> Path | None:
    for d in (IN_PROGRESS, BACKLOG, DEFERRED, DONE):
        m = list(d.glob(f"{task_id}-*.md"))
        if m:
            return m[0]
    return None


def task_priority(path: Path) -> int:
    m = re.search(r"^priority:\s*(\d+)", path.read_text(), re.M)
    return int(m.group(1)) if m else 5


def free_gb() -> float:
    return shutil.disk_usage(REPO).free / 1e9


# ---------------------------------------------------------------- 1. reap
def reap_stale(r, st: State) -> None:
    now = time.time()
    for kind in JobKind:
        key = f"jobs:{kind.value}:processing"
        for raw in r.lrange(key, 0, -1):
            job = Job.from_json(raw)
            started = st.job(job.id).get("claimed_at") or now
            if now - started > STALE_JOB_S:
                r.lrem(key, 1, raw)
                if job.attempt < job.max_attempts:
                    job.attempt += 1
                    job.notes = (job.notes or "") + " | previous attempt timed out on the worker"
                    q.enqueue(r, job); st.add_job(job.task_id, job.id, job.kind.value, job.attempt)
                    ev(f"re-queued stale job {job.id} (attempt {job.attempt})")
                else:
                    st.set_job(job.id, "failed", error="stale after max attempts")
                    ev(f"failed stale job {job.id}")
    # mark claimed_at for anything in processing we have not seen
    for kind in JobKind:
        for raw in r.lrange(f"jobs:{kind.value}:processing", 0, -1):
            j = Job.from_json(raw)
            if not st.job(j.id).get("claimed_at"):
                st.set_job(j.id, "running", claimed_at=now)


# ---------------------------------------------------------------- 2. results
def handle_results(r, st: State) -> None:
    while (res := q.next_result(r, timeout_s=1)) is not None:
        job_meta = st.job(res.job_id)
        task_id = job_meta.get("task", res.job_id.split("-")[0])
        tf = task_file(task_id)
        spec = job_meta.get("spec", {})
        if res.status == ResultStatus.OK and job_meta.get("kind") in ("image", "music", "sfx"):
            verdict, reason = "approved", ""
            if job_meta.get("kind") == "image":
                for rel in res.outputs:
                    ok, why = checks.check_image(REPO, REPO / rel, spec)
                    if not ok:
                        verdict, reason = "rejected", f"auto-check {Path(rel).name}: {why}"
                        break
            if verdict == "approved":
                verdict, reason = reviewer.review_result(REPO, res, spec)
            moved = reviewer.file_verdict(REPO, res, verdict, reason)
            if verdict == "approved":
                st.set_job(res.job_id, "approved", outputs=moved)
                if tf: append_log(tf, f"APPROVED {res.job_id}: {reason} -> {moved[:3]}")
            else:
                _retry_or_fail(r, st, res.job_id, job_meta, f"reviewer: {reason}", tf)
        elif res.status == ResultStatus.OK:
            st.set_job(res.job_id, "ok", outputs=res.outputs)
            if tf: append_log(tf, f"ok {res.job_id}: {res.outputs}")
        else:
            _retry_or_fail(r, st, res.job_id, job_meta, res.error or res.status.value, tf)


def _retry_or_fail(r, st: State, job_id: str, meta: dict, why: str, tf: Path | None) -> None:
    attempt = meta.get("attempt", 1)
    job_json = meta.get("job")
    if job_json and attempt < meta.get("max_attempts", 3):
        job = Job.from_json(job_json)
        job.attempt = attempt + 1
        job.notes = ((job.notes + " | ") if job.notes else "") + why[:400]
        st.set_job(job_id, "failed", error=why)  # old id closes
        st.add_job(job.task_id, job.id + f"-r{job.attempt}", job.kind.value, job.attempt)
        job.id = job.id + f"-r{job.attempt}"
        st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=job.max_attempts, attempt=job.attempt, task=job.task_id, kind=job.kind.value)
        q.enqueue(r, job)
        if tf: append_log(tf, f"RETRY {job.id} (attempt {job.attempt}): {why[:200]}")
    else:
        st.set_job(job_id, "failed", error=why)
        if tf: append_log(tf, f"FAILED {job_id}: {why[:300]}")


# ---------------------------------------------------------------- failure classes
FAIL_SIG_THRESHOLD = int(os.environ.get("FAIL_SIG_THRESHOLD", "3"))
FAIL_SIG_WINDOW_S = int(os.environ.get("FAIL_SIG_WINDOW_S", "86400"))


def failure_signature(msg: str) -> str:
    """Collapse an error into a class: the first line that names a script error, parse error,
    invalid call or missing member, with numbers and paths stripped."""
    for line in msg.splitlines():
        l = line.strip()
        if any(k in l for k in ("SCRIPT ERROR", "Parse Error", "Invalid call", "Nonexistent function", "not found in base", "Cannot find member", "gdlint", "Godot 3 pattern")):
            l = re.sub(r"res://\S+|\d+", "", l)
            return l[:120]
    first = (msg.strip().splitlines() or [""])[0]
    return re.sub(r"\d+", "", first)[:120]


def note_failure(st: State, msg: str) -> None:
    sig = failure_signature(msg)
    if not sig:
        return
    sigs = st.data.setdefault("failure_sigs", {})
    entry = sigs.setdefault(sig, {"count": 0, "last": 0})
    if time.time() - entry["last"] > FAIL_SIG_WINDOW_S:
        entry["count"] = 0
    entry["count"] += 1; entry["last"] = time.time()
    st.save()
    if entry["count"] == FAIL_SIG_THRESHOLD:
        ev(f"failure class repeated {FAIL_SIG_THRESHOLD}x, escalating code jobs: {sig}")


def should_escalate(st: State) -> bool:
    now = time.time()
    return any(e["count"] >= FAIL_SIG_THRESHOLD and now - e["last"] < FAIL_SIG_WINDOW_S for e in st.data.get("failure_sigs", {}).values())


# ---------------------------------------------------------------- 3. code jobs
def run_code_jobs(st: State, escalate: bool = False) -> None:
    for jid, meta in list(st.data["jobs"].items()):
        if meta.get("kind") != "code" or meta.get("status") != "pending":
            continue
        task_id = meta["task"]
        runs = st.data["tasks"].get(task_id, {}).get("coder_runs", 0)
        tf = task_file(task_id)
        if runs >= MAX_CODER_RUNS_PER_TASK:
            st.set_job(jid, "failed", error="coder run cap reached")
            if tf: append_log(tf, f"FAILED {jid}: coder run cap ({MAX_CODER_RUNS_PER_TASK}) reached")
            continue
        st.data["tasks"][task_id]["coder_runs"] = runs + 1; st.save()
        st.set_job(jid, "running")
        escalate = escalate or bool(meta.get("escalate")) or should_escalate(st)
        ev(f"coder start {jid}" + (" (escalation model)" if escalate else ""))
        try:
            ok, msg = coder.run_code_job(REPO, task_id, jid, meta.get("spec", {}), meta.get("notes"), escalate)
        except Exception as e:
            ok, msg = False, f"coder crashed: {e}"
            log.exception("coder crashed")
        if ok:
            st.set_job(jid, "ok", summary=msg)
            if tf: append_log(tf, f"MERGED {jid}: {msg[:300]}")
        else:
            note_failure(st, msg)
            st.set_job(jid, "pending", notes=msg[:1500]) if runs + 1 < MAX_CODER_RUNS_PER_TASK else st.set_job(jid, "failed", error=msg[:1500])
            if tf: append_log(tf, f"CODER FAIL {jid} (run {runs + 1}): {msg[:300]}")
        return  # one coder run per cycle; they are long


# ---------------------------------------------------------------- 4. close tasks
def close_tasks(st: State) -> None:
    for tf in list(IN_PROGRESS.glob("*.md")):
        task_id = tf.stem.split("-")[0]
        if not st.task_terminal(task_id):
            continue
        if st.task_succeeded(task_id):
            append_log(tf, "DONE: all jobs approved/merged")
            shutil.move(str(tf), DONE / tf.name); ev(f"task done {tf.name}")
        else:
            failed = [j["id"] for j in st.task_jobs(task_id) if j["status"] == "failed"]
            append_log(tf, f"DEFERRED: failed jobs {failed}. Will retry with the escalation model in the daily pass.")
            shutil.move(str(tf), DEFERRED / tf.name); ev(f"task deferred {tf.name}")


# ---------------------------------------------------------------- 5. plan
def plan_next(r, st: State, escalate: bool = False, source: Path = None) -> None:
    if st.in_flight() >= MAX_INFLIGHT:
        return
    src = source or BACKLOG
    tasks = sorted(src.glob("*.md"), key=lambda p: (task_priority(p), p.name))
    if not tasks:
        return
    task = tasks[0]
    dest = IN_PROGRESS / task.name
    shutil.move(str(task), dest)
    task_id = dest.stem.split("-")[0]
    try:
        jobs = planner.plan_jobs(REPO, dest, escalate=escalate)
    except Exception as e:
        append_log(dest, f"DEFERRED: planning failed: {e}")
        shutil.move(str(dest), DEFERRED / dest.name); ev(f"planning failed for {dest.name}: {e}")
        return
    st.mark_planned(task_id, stamp())
    for job in jobs:
        st.add_job(task_id, job.id, job.kind.value)
        st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=job.max_attempts,
                   attempt=1, task=task_id, kind=job.kind.value, notes=job.notes, escalate=escalate)
        if job.kind != JobKind.CODE:
            q.enqueue(r, job)
        append_log(dest, f"planned {job.kind.value} job {job.id}")
    ev(f"planned {len(jobs)} jobs for {dest.name}")


# ---------------------------------------------------------------- 6. backlog
def refill_backlog() -> None:
    day = time.strftime("%Y-%m-%d")
    if _generated_today["day"] != day:
        _generated_today.update(day=day, n=0)
    if list(BACKLOG.glob("*.md")) or _generated_today["n"] >= MAX_GENERATED_TASKS_PER_DAY:
        return
    if list(IN_PROGRESS.glob("*.md")):
        return  # finish what is open first
    try:
        created = planner.generate_backlog(REPO, count=3)
        _generated_today["n"] += len(created)
        ev(f"generated backlog: {[p.name for p in created]}")
    except Exception as e:
        ev(f"backlog generation failed: {e}")


# ---------------------------------------------------------------- 7. daily
def daily(r, st: State) -> None:
    global _last_daily
    if time.time() - _last_daily < 86400:
        return
    _last_daily = time.time()
    # retry one deferred task with the escalation model
    deferred = sorted(DEFERRED.glob("*.md"), key=task_priority)
    if deferred:
        plan_next(r, st, escalate=True, source=DEFERRED)
    report.write(REPO, st, q.queue_depths(r), q.worker_alive(r, WORKER), EVENTS)
    if gitops.commit_paths(REPO, ["tasks", "reports", "PROGRESS.md", "docs", "style"], f"studio: daily checkpoint {time.strftime('%Y-%m-%d')}"):
        gitops.push(REPO, gitops.current_branch(REPO))
    EVENTS.clear()


# ---------------------------------------------------------------- loop
def cycle(r, st: State) -> None:
    if free_gb() < MIN_FREE_GB:
        ev(f"disk low ({free_gb():.1f} GB free); pausing new work"); return
    reap_stale(r, st)
    handle_results(r, st)
    run_code_jobs(st)
    close_tasks(st)
    plan_next(r, st)
    refill_backlog()
    daily(r, st)
    depth = sum(q.queue_depths(r).values())
    if wake.maybe_wake(depth, q.worker_alive(r, WORKER)):
        ev(f"sent wake-on-LAN to {WORKER} ({depth} jobs queued)")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    for d in (BACKLOG, IN_PROGRESS, DONE, DEFERRED, REPO / "reports"):
        d.mkdir(parents=True, exist_ok=True)
    r = q.connect()
    st = State(REPO)
    ev(f"orchestrator up; repo={REPO} model={os.environ.get('ORCHESTRATOR_MODEL')}")
    # write a report immediately so the human sees something even on day one
    report.write(REPO, st, q.queue_depths(r), q.worker_alive(r, WORKER), EVENTS)
    while True:
        try:
            cycle(r, st)
        except Exception:
            log.exception("cycle error")
        time.sleep(LOOP_S)


if __name__ == "__main__":
    main()
