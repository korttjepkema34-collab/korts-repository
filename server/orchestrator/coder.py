"""File-based coder loop. Runs on the server against the game/ folder with headless Godot as the
gate. No editor, no MCP, no dependency on the gaming PC. Tool calls go through the
OpenAI-compatible API (Ollama supports tools for Qwen-class models).

Gate before merge: no Godot 3 patterns, project loads headless, tests pass if gdUnit4 exists.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from . import gitops, godot, llm

log = logging.getLogger("coder")
MAX_STEPS = 40
MAX_FILE_BYTES = 60_000

TOOLS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files under game/ (relative paths).",
        "parameters": {"type": "object", "properties": {"subdir": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a file under game/.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create or overwrite a file under game/ with the full content.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Delete a file under game/.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_godot_check", "description": "Import and load the project headless; returns errors. Run after every batch of edits.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run gdUnit4 tests headless (or the load check if gdUnit4 is missing).",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "finish", "description": "Call when done. Summarise what you changed and why.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]


def _safe(game: Path, rel: str) -> Path:
    p = (game / rel).resolve()
    if game.resolve() not in p.parents and p != game.resolve():
        raise ValueError("path escapes game/")
    return p


def _exec(game: Path, name: str, args: dict) -> str:
    if name == "list_files":
        base = _safe(game, args.get("subdir") or ".")
        files = [str(p.relative_to(game)) for p in base.rglob("*") if p.is_file() and ".godot" not in p.parts]
        return "\n".join(sorted(files)[:400]) or "(empty)"
    if name == "read_file":
        p = _safe(game, args["path"])
        return p.read_text(errors="ignore")[:MAX_FILE_BYTES] if p.exists() else "ERROR: not found"
    if name == "write_file":
        p = _safe(game, args["path"]); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args["content"]); return f"wrote {args['path']} ({len(args['content'])} bytes)"
    if name == "delete_file":
        p = _safe(game, args["path"]); p.unlink(missing_ok=True); return "deleted"
    if name == "run_godot_check":
        ok, out = godot.load_check(game); return ("OK\n" if ok else "ERRORS\n") + out
    if name == "run_tests":
        ok, out = godot.run_tests(game); return ("PASS\n" if ok else "FAIL\n") + out
    return "ERROR: unknown tool"


def run_code_job(repo: Path, task_id: str, job_id: str, spec: dict, notes: str | None, escalate: bool) -> tuple[bool, str]:
    game = repo / "game"
    branch = f"coder/{job_id}"
    base = gitops.current_branch(repo)
    gitops.new_branch(repo, branch, base)
    try:
        system = llm.load_role(repo, "coder") + "\n\n" + (repo / "docs" / "09-godot-conventions.md").read_text()
        user = ("Goal:\n" + str(spec.get("goal", spec)) + "\n\nAcceptance:\n"
                + "\n".join(f"- {a}" for a in spec.get("acceptance", [])) + "\n\nApproved assets available:\n"
                + "\n".join(str(p.relative_to(repo)) for p in (repo / "assets" / "approved").rglob("*") if p.is_file())[:3000]
                + (f"\n\nNotes from the previous failed attempt:\n{notes}" if notes else "")
                + "\n\nWork in small steps. Call run_godot_check after edits. Call finish when the acceptance list is met.")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        model = llm.escalation_model() if escalate else llm.coder_model()
        summary = None
        for step in range(MAX_STEPS):
            resp = llm.client().chat.completions.create(model=model, messages=messages, tools=TOOLS, temperature=0.1)
            msg = resp.choices[0].message
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in (msg.tool_calls or [])]})
            if not msg.tool_calls:
                messages.append({"role": "user", "content": "Use the tools. Call finish when done."})
                continue
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if tc.function.name == "finish":
                    summary = args.get("summary", "")
                    break
                try:
                    out = _exec(game, tc.function.name, args)
                except Exception as e:
                    out = f"ERROR: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out[:12000]})
            if summary is not None:
                break
        # Gate
        hits = godot.godot3_hits(game)
        if hits:
            return False, "Godot 3 patterns found:\n" + "\n".join(hits[:20])
        ok, out = godot.run_tests(game)
        if not ok:
            return False, "Headless check/tests failed:\n" + out[-4000:]
        if not gitops.commit_paths(repo, ["game"], f"{task_id}: {summary or spec.get('goal', 'code job')}"[:200]):
            return False, "coder made no changes"
        merged = gitops.merge(repo, branch, base, f"{task_id}: merge {branch}")
        return (True, summary or "merged") if merged else (False, "merge conflict; branch kept")
    finally:
        gitops.checkout(repo, base)
