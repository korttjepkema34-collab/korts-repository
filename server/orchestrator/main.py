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

from . import checks, coder, engineer, export, gitops, health, incidents as incidents_mod, levels, notify, planner, playtest, report, reviewer, training, wake, writer
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
            # training jobs legitimately run for hours; they say so in spec.stale_after_s
            limit = max(STALE_JOB_S, int(job.spec.get("stale_after_s", 0) or 0))
            if now - started > limit:
                r.lrem(key, 1, raw)
                if job.attempt < job.max_attempts:
                    job.attempt += 1
                    job.notes = (job.notes or "") + " | previous attempt timed out on the worker"
                    q.enqueue(r, job)
                    # same id, so merge into the existing record (add_job would drop spec/job/max_attempts)
                    st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=job.max_attempts,
                               attempt=job.attempt, task=job.task_id, kind=job.kind.value, notes=job.notes, claimed_at=None)
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
            # Deterministic checks first (size, palette, transparency); the vision model only sees what passes.
            failed: dict[str, str] = {}
            if job_meta.get("kind") == "image":
                for rel in res.outputs:
                    ok, why = checks.check_image(REPO, REPO / rel, spec)
                    if not ok:
                        failed[rel] = f"auto-check: {why}"
            if failed and len(failed) == len(res.outputs):
                verdict, reason = "rejected", next(iter(failed.values()))
                per_output = {rel: ("rejected", why) for rel, why in failed.items()}
            else:
                res_ok = res.model_copy(update={"outputs": [o for o in res.outputs if o not in failed]}) if failed else res
                verdict, reason, per_output = reviewer.review_result(REPO, res_ok, spec)
                for rel, why in failed.items():
                    per_output[rel] = ("rejected", why)
                if per_output and not any(v == "approved" for v, _ in per_output.values()):
                    verdict, reason = "rejected", "no candidate passed checks and review; " + reason
            moved = reviewer.file_verdict(REPO, res, verdict, reason, per_output)
            if verdict == "approved":
                st.set_job(res.job_id, "approved", outputs=moved)
                if tf: append_log(tf, f"APPROVED {res.job_id}: {reason} -> {moved[:3]}")
            else:
                _retry_or_fail(r, st, res.job_id, job_meta, f"reviewer: {reason}", tf)
        elif res.status == ResultStatus.OK and job_meta.get("kind") == "train":
            st.set_job(res.job_id, "ok", outputs=res.outputs)
            training.on_trained(REPO, spec, res.outputs, ev)
            if tf: append_log(tf, f"TRAINED {res.job_id}: {res.outputs[:3]}")
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
        new_id = job.id + f"-r{job.attempt}"
        st.supersede(job.task_id, job_id, new_id, job.kind.value, job.attempt)  # old id drops out of the task's outcome
        st.set_job(job_id, "superseded", error=why)
        job.id = new_id
        st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=job.max_attempts, attempt=job.attempt, task=job.task_id, kind=job.kind.value, notes=job.notes)
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
    sigs = st.meta("failure_sigs", {})
    entry = sigs.setdefault(sig, {"count": 0, "last": 0})
    if time.time() - entry["last"] > FAIL_SIG_WINDOW_S:
        entry["count"] = 0
    entry["count"] += 1; entry["last"] = time.time()
    st.set_meta("failure_sigs", sigs)
    if entry["count"] == FAIL_SIG_THRESHOLD:
        ev(f"failure class repeated {FAIL_SIG_THRESHOLD}x, escalating code jobs: {sig}")


def should_escalate(st: State) -> bool:
    now = time.time()
    return any(e["count"] >= FAIL_SIG_THRESHOLD and now - e["last"] < FAIL_SIG_WINDOW_S for e in st.meta("failure_sigs", {}).values())


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
            if meta.get("notes"):  # it failed before and now passed: distil the lesson for future coders
                lesson = f"- {failure_signature(str(meta['notes']))[:100]} -> {msg[:160]}"
                with (REPO / "docs" / "lessons.md").open("a") as f:
                    f.write(lesson.replace("\n", " ") + "\n")
            proof = meta.get("spec", {}).get("proof")
            if proof and isinstance(proof, dict) and proof.get("scene"):
                try:
                    from . import vision
                    verdict = vision.proof_check(REPO, proof)
                    if tf: append_log(tf, f"PROOF {jid}: {verdict[:300]}")
                    if verdict.startswith("FAIL"):
                        st.set_job(jid, "pending", notes=f"merged, but the playtest proof failed: {verdict[:800]}")
                except Exception as e:
                    log.warning("proof check failed to run: %s", e)
        else:
            note_failure(st, msg)
            st.set_job(jid, "pending", notes=msg[:1500]) if runs + 1 < MAX_CODER_RUNS_PER_TASK else st.set_job(jid, "failed", error=msg[:1500])
            if tf: append_log(tf, f"CODER FAIL {jid} (run {runs + 1}): {msg[:300]}")
        return  # one coder run per cycle; they are long


# ---------------------------------------------------------------- 3b. text and level jobs (in-process, CPU)
def run_content_jobs(st: State) -> None:
    for jid, meta in list(st.data["jobs"].items()):
        kind = meta.get("kind")
        if kind not in ("text", "level") or meta.get("status") != "pending":
            continue
        task_id = meta["task"]; tf = task_file(task_id)
        st.set_job(jid, "running")
        escalate = bool(meta.get("escalate")) or should_escalate(st)
        try:
            fn = writer.run_text_job if kind == "text" else levels.run_level_job
            ok, msg = fn(REPO, meta.get("spec", {}), meta.get("notes"), escalate)
        except Exception as e:
            ok, msg = False, f"{kind} job crashed: {e}"
            log.exception("%s job crashed", kind)
        if ok:
            st.set_job(jid, "ok", summary=msg)
            gitops.commit_paths(REPO, ["game/data"], f"{task_id}: {kind} {msg[:120]}")
            if tf: append_log(tf, f"{kind.upper()} OK {jid}: {msg[:300]}")
        else:
            st.set_job(jid, "failed", error=msg[:1500])
            if tf: append_log(tf, f"{kind.upper()} FAILED {jid}: {msg[:400]}")
        return


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
    st.reset_task(task_id)  # a re-plan (deferred/) must not inherit old failed jobs or the coder-run cap
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
def refill_backlog(st: State) -> None:
    day = time.strftime("%Y-%m-%d")
    gen = st.meta("generated_today", {"day": "", "n": 0})  # persisted so a restart cannot reset the cap
    if gen.get("day") != day:
        gen = {"day": day, "n": 0}
    if list(BACKLOG.glob("*.md")) or gen["n"] >= MAX_GENERATED_TASKS_PER_DAY:
        return
    if list(IN_PROGRESS.glob("*.md")):
        return  # finish what is open first
    try:
        created = planner.generate_backlog(REPO, count=3)
        gen["n"] += len(created)
        st.set_meta("generated_today", gen)
        ev(f"generated backlog: {[p.name for p in created]}")
    except Exception as e:
        ev(f"backlog generation failed: {e}")


# ---------------------------------------------------------------- 7. daily
def daily(r, st: State) -> None:
    if time.time() - float(st.meta("last_daily", 0.0)) < 86400:
        return
    st.set_meta("last_daily", time.time())
    # retry one deferred task with the escalation model
    deferred = sorted(DEFERRED.glob("*.md"), key=task_priority)
    if deferred:
        plan_next(r, st, escalate=True, source=DEFERRED)
    # Self-improvement: when enough new labelled data has accumulated, queue a training job
    # for the GPU worker (off by default; AUTO_TRAIN=1 in server/.env). See docs/15-training.md.
    try:
        for job in training.auto_jobs(REPO, st):
            st.add_job(job.task_id, job.id, job.kind.value)
            st.set_job(job.id, "pending", job=job.to_json(), spec=job.spec, max_attempts=job.max_attempts,
                       attempt=1, task=job.task_id, kind=job.kind.value)
            q.enqueue(r, job)
            ev(f"queued training job {job.id} ({job.spec.get('recipe')})")
    except Exception:
        log.exception("auto-train check failed")
    # Nightly playtest and build: proof that the game runs, and something to double-click on return.
    if os.environ.get("PLAYTEST_DAILY", "1") == "1":
        try:
            playtest.run(REPO, ev)
        except Exception:
            log.exception("playtest failed")
    if os.environ.get("BUILD_DAILY", "1") == "1":
        try:
            export.build(REPO, ev)
        except Exception:
            log.exception("build failed")
    report.write(REPO, st, q.queue_depths(r), q.worker_alive(r, WORKER), EVENTS)
    if INC is not None and INC.open_list():
        with (REPO / "PROGRESS.md").open("a") as f:
            f.write("\n## Open incidents\n" + "\n".join(f"- {i['kind']}: {i['signature']} (attempts {i.get('attempts', 0)}) -> incidents/{i['file']}" for i in INC.open_list()) + "\n")
    done_n = len(list(DONE.glob("*.md"))); def_n = len(list(DEFERRED.glob("*.md")))
    notify.send("studio: daily", f"done {done_n}, deferred {def_n}, open incidents {len(INC.open_list()) if INC else 0}, queue {sum(q.queue_depths(r).values())}")
    if gitops.commit_paths(REPO, ["tasks", "reports", "PROGRESS.md", "docs", "style", "incidents"], f"studio: daily checkpoint {time.strftime('%Y-%m-%d')}"):
        gitops.push(REPO, gitops.current_branch(REPO))
    EVENTS.clear()


# ---------------------------------------------------------------- safety nets
INC: incidents_mod.Incidents | None = None


def run_engineer(st: State) -> None:
    """Fix the studio's own code when a studio-bug incident is open. One attempt per cycle."""
    if INC is None or os.environ.get("ENGINEER_ENABLED", "1") != "1":
        return
    for sig, rec in INC.engineer_candidates():
        path = INC.dir / rec["file"]
        ev(f"engineer: working incident {sig[:60]}")
        try:
            ok, msg = engineer.run(REPO, sig, path)
        except Exception as e:
            ok, msg = False, f"engineer crashed: {e}"
            log.exception("engineer crashed")
        n = INC.attempt(sig, msg[:600])
        if ok:
            INC.note(sig, "Diagnosis", msg[:600])
            INC.note(sig, "Plan", "fix merged; the supervisor restarts the loop and rolls back if it does not come back healthy")
            notify.send("studio: fix merged", f"{sig[:80]} | {msg[:300]}")
            ev("engineer: fix merged, restart requested")
        elif n >= 3:
            INC.note(sig, "Plan", "3 engineer attempts failed; this needs a human. Read Attempts above.")
            notify.send("studio: needs a human", sig[:200], "high")
        return


def cycle(r, st: State) -> None:
    global INC
    if INC is None:
        INC = incidents_mod.Incidents(REPO, ev)
    health.git_sanity(REPO, ev)
    infra = health.heal(r, ev, INC)
    if not infra["redis"]:
        health.write(REPO, {"infra": infra}); return  # nothing else can run without the queue
    if free_gb() < MIN_FREE_GB:
        ev(f"disk low ({free_gb():.1f} GB free); pausing new work")
        INC.open("disk", "disk:low", f"{free_gb():.1f} GB free, below MIN_FREE_GB", plan="Delete old builds/, reports/playtests/, assets/rejected/; or raise the disk.")
        health.write(REPO, {"infra": infra, "disk_gb": free_gb()}); return
    if not infra["llm"]:
        health.write(REPO, {"infra": infra}); reap_stale(r, st); handle_results(r, st); close_tasks(st); return  # no model: only bookkeeping
    reap_stale(r, st)
    handle_results(r, st)
    run_content_jobs(st)
    run_code_jobs(st)
    close_tasks(st)
    plan_next(r, st)
    refill_backlog(st)
    run_engineer(st)
    daily(r, st)
    depth = sum(q.queue_depths(r).values())
    if wake.maybe_wake(depth, q.worker_alive(r, WORKER)):
        ev(f"sent wake-on-LAN to {WORKER} ({depth} jobs queued)")
    health.write(REPO, {"infra": infra, "queue": depth, "in_flight": st.in_flight(), "open_incidents": len(INC.open_list())})
    if (REPO / "RESTART_REQUESTED").exists():
        ev("restart requested by the engineer; exiting for the supervisor")
        raise SystemExit(3)


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
        except SystemExit:
            raise
        except Exception as e:
            log.exception("cycle error")
            import traceback
            tb = traceback.format_exc()
            sig = "studio:" + failure_signature(f"{type(e).__name__}: {e}")
            n = health.record_error(sig)
            if n >= 3 and INC is not None:
                INC.open("studio-bug", sig, f"The orchestrator cycle raised the same error {n} times in the last hour.\n\n```\n{tb[-3000:]}\n```",
                         plan="The engineer will read the traceback, fix the studio code on a branch, add a test, and merge behind the test gate. The supervisor restarts the loop and rolls back if it does not come back healthy.")
                notify.send("studio: incident opened", sig[:200], "high")
        time.sleep(LOOP_S)


if __name__ == "__main__":
    main()
