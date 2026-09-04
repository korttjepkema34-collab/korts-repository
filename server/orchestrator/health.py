"""Health file, dependency healing and git sanity. Runs at the start of every cycle."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from . import gitops

STARTED = time.time()
_state = {"cycles": 0, "errors": [], "llm_down_since": None, "redis_down_since": None, "healed": {}}


def probe_llm() -> bool:
    base = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
    try:
        with urllib.request.urlopen(base + "/models", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def probe_redis(r) -> bool:
    try:
        return bool(r.ping())
    except Exception:
        return False


def _run_start(cmd_env: str, ev) -> None:
    """Run a start command from the environment at most once per 10 minutes."""
    cmd = os.environ.get(cmd_env, "").strip()
    if not cmd:
        return
    last = _state["healed"].get(cmd_env, 0)
    if time.time() - last < 600:
        return
    _state["healed"][cmd_env] = time.time()
    ev(f"heal: running {cmd_env}: {cmd}")
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        ev(f"heal: {cmd_env} failed to launch: {e}")


def heal(r, ev, incidents) -> dict:
    """Probe Ollama and Redis; try to restart them; open an incident if they stay down."""
    now = time.time()
    status = {"llm": probe_llm(), "redis": probe_redis(r)}
    for key, up, cmd_env, label in (("llm_down_since", status["llm"], "OLLAMA_START_CMD", "Ollama"),
                                    ("redis_down_since", status["redis"], "REDIS_START_CMD", "Redis")):
        if up:
            if _state[key]:
                ev(f"heal: {label} back after {int(now - _state[key])} s")
                incidents.resolve(f"infra:{label}", f"{label} reachable again")
            _state[key] = None
            continue
        if _state[key] is None:
            _state[key] = now
            ev(f"heal: {label} unreachable")
        elif now - _state[key] > 120:
            _run_start(cmd_env, ev)
        if now - _state[key] > 1800:
            incidents.open("infra", f"infra:{label}", f"{label} has been unreachable for {int((now - _state[key]) / 60)} minutes. "
                           f"Start command tried: {os.environ.get(cmd_env) or '(none set)'}",
                           plan=f"1. Check the {label} process/service on the server. 2. Set {cmd_env} in server/.env so the loop can restart it. 3. If it keeps dying, check RAM (Ollama) or Docker Desktop (Redis).")
    return status


def git_sanity(repo: Path, ev) -> None:
    """Never let the working tree start a cycle in a broken state."""
    code, out = gitops.git(repo, "status", "--porcelain=v1", "--branch")
    if code != 0:
        ev("git: status failed: " + out[:200]); return
    if (repo / ".git" / "MERGE_HEAD").exists():
        gitops.git(repo, "merge", "--abort"); ev("git: aborted a stuck merge")
    branch = gitops.current_branch(repo)
    if branch.startswith("coder/") or branch == "HEAD":
        gitops.discard(repo, "game")
        gitops.git(repo, "checkout", "-q", "main")
        ev(f"git: was on {branch}, returned to main")


def write(repo: Path, extra: dict) -> None:
    _state["cycles"] += 1
    cutoff = time.time() - 3600
    _state["errors"] = [e for e in _state["errors"] if e[0] > cutoff]
    data = {"ts": time.time(), "started": STARTED, "uptime_s": int(time.time() - STARTED), "cycles": _state["cycles"],
            "errors_last_hour": len(_state["errors"]), "last_error": _state["errors"][-1][1] if _state["errors"] else None, **extra}
    p = repo / "reports" / "health.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def record_error(sig: str) -> int:
    _state["errors"].append((time.time(), sig))
    return sum(1 for _, s in _state["errors"] if s == sig)
