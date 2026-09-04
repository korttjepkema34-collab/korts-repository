"""The engineer fixes the studio's own code (server/, worker/, shared/, scripts/, tests/) when
a studio-bug incident is open. Same tool loop as the coder, different root and a different
gate: every file compiles and `pytest tests` passes. A merged fix asks the supervisor to restart;
the supervisor rolls back to the last good commit if the loop does not come back healthy.
Never edits game/ (that is the coder's), agents/ or docs/ (those are the human's and the
orchestrator's). Prefers the escalation model: rare, important, and latency does not matter."""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from . import gitops, llm

log = logging.getLogger("engineer")
_BASELINE: dict = {}
ALLOWED = ("server/", "worker/", "shared/", "scripts/", "tests/")
MAX_STEPS = 40
TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "List studio source files (server/, worker/, shared/, scripts/, tests/).", "parameters": {"type": "object", "properties": {"subdir": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a studio source file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a studio source file (full content). Only under server/, worker/, shared/, scripts/, tests/.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Compile every python file and run pytest tests/. Run before finish.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "finish", "description": "Done. Summarise the root cause and the fix in two sentences.", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]


def _safe(repo: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/").lstrip("./")
    if not rel.startswith(ALLOWED):
        raise ValueError(f"engineer may only touch {ALLOWED}")
    p = (repo / rel).resolve()
    if repo.resolve() not in p.parents:
        raise ValueError("path escapes the repo")
    return p


def count_tests(repo: Path) -> int:
    return sum(p.read_text(errors="ignore").count("def test_") for p in (repo / "tests").glob("test_*.py"))


def gate(repo: Path, baseline_tests: int | None = None) -> tuple[bool, str]:
    if baseline_tests is not None and count_tests(repo) < baseline_tests:
        return False, f"test count dropped from {baseline_tests} to {count_tests(repo)}; tests may not be deleted"
    files = [str(p) for d in ALLOWED for p in (repo / d).rglob("*.py") if ".venv" not in p.parts]
    p = subprocess.run([sys.executable, "-m", "py_compile", *files], capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        return False, "compile failed:\n" + (p.stderr or p.stdout)[-3000:]
    t = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x", "--no-header", "-p", "no:cacheprovider"], capture_output=True, text=True, timeout=900, cwd=str(repo))
    return t.returncode == 0, (t.stdout + t.stderr)[-4000:]


def _exec(repo: Path, name: str, args: dict) -> str:
    if name == "list_files":
        base = args.get("subdir") or ""
        out = []
        for d in ALLOWED:
            for p in (repo / d).rglob("*"):
                if p.is_file() and ".venv" not in p.parts and "__pycache__" not in p.parts and (not base or str(p.relative_to(repo)).startswith(base)):
                    out.append(str(p.relative_to(repo)))
        return "\n".join(sorted(out)[:400])
    if name == "read_file":
        p = _safe(repo, args["path"]); return p.read_text(errors="ignore")[:60000] if p.exists() else "ERROR: not found"
    if name == "write_file":
        p = _safe(repo, args["path"]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(args["content"]); return f"wrote {args['path']}"
    if name == "run_tests":
        ok, out = gate(repo, _BASELINE.get("n")); return ("PASS\n" if ok else "FAIL\n") + out
    return "ERROR: unknown tool"


def run(repo: Path, signature: str, incident_path: Path, escalate: bool = True) -> tuple[bool, str]:
    base = gitops.current_branch(repo)
    for d in ALLOWED:
        gitops.discard(repo, d.rstrip("/"))
    branch = "engineer/" + re.sub(r"[^a-z0-9]+", "-", signature.lower())[:40]
    gitops.new_branch(repo, branch, base)
    model, oai, _gpu = llm.coder_route(escalate)
    baseline = count_tests(repo)
    _BASELINE["n"] = baseline
    system = ("You are the studio's engineer. You fix bugs in the orchestrator, worker and shared Python code of an "
              "autonomous game studio. Read the incident, find the root cause in the code, write the smallest fix, "
              "add or extend a test in tests/ that would have caught it, run run_tests until it passes, then finish. "
              "Never touch game/, agents/ or docs/. Never delete tests. If the incident is not a code bug, finish "
              "with a summary that says so and what a human should check.")
    user = "Incident:\n" + incident_path.read_text()[:8000] + "\n\nRepo layout: docs/22-how-it-runs.md describes the loop. Start with list_files and read the file named in the traceback."
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    summary = None
    try:
        for _ in range(MAX_STEPS):
            resp = oai.chat.completions.create(model=model, messages=messages, tools=TOOLS, temperature=0.1)
            msg = resp.choices[0].message
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in (msg.tool_calls or [])]})
            if not msg.tool_calls:
                messages.append({"role": "user", "content": "Use the tools. Call finish when done."}); continue
            done = False
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if tc.function.name == "finish":
                    summary = args.get("summary", ""); done = True; break
                try:
                    out = _exec(repo, tc.function.name, args)
                except Exception as e:
                    out = f"ERROR: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out[:12000]})
            if done:
                break
        ok, out = gate(repo, baseline)
        if not ok:
            return False, "gate failed:\n" + out[-2000:]
        if not gitops.commit_paths(repo, [d.rstrip("/") for d in ALLOWED], f"engineer: {summary or signature}"[:200]):
            return False, "engineer made no changes: " + (summary or "")
        sha_before = gitops.git(repo, "rev-parse", base)[1]
        if not gitops.merge(repo, branch, base, f"engineer: merge fix for {signature[:60]}"):
            return False, "merge conflict; branch kept"
        (repo / "reports" / "last_good.txt").write_text(sha_before)
        (repo / "RESTART_REQUESTED").write_text(signature)
        return True, summary or "merged"
    finally:
        for d in ALLOWED:
            gitops.discard(repo, d.rstrip("/"))
        try:
            gitops.checkout(repo, base)
        except Exception:
            log.exception("engineer could not return to %s", base)
