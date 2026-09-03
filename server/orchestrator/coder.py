"""Coder loop. Runs on the server against the game/ folder.

Tools, from always-available to optional:
  - file tools (list/read/write/delete)                       always
  - headless load check and gdUnit4 tests                     always (needs GODOT_BIN)
  - run a scene headless and capture printed output/errors    needs GODOT_BIN
  - visual_check: windowed screenshot described by the        needs GODOT_BIN + a logged-in desktop
    vision model                                              (server iGPU is enough)
  - mcp_* editor tools from a Godot MCP server                needs GODOT_MCP_CMD + the `mcp` package
Tool calls go through the OpenAI-compatible API (Ollama supports tools for Qwen-class models).

Gate before merge: no Godot 3 patterns, project loads headless, tests pass if gdUnit4 exists.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from . import gitops, godot, llm, mcp_bridge, rag, traces, vision

log = logging.getLogger("coder")
MAX_STEPS = 40
MAX_FILE_BYTES = 60_000

TOOLS = [
    {"type": "function", "function": {"name": "search_docs", "description": "Search the Godot 4 reference docs, this project's conventions and its existing code. Use before writing any API call you are not certain of (signals, TileMapLayer, CharacterBody2D, multiplayer, tweens).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
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
    {"type": "function", "function": {"name": "visual_check", "description": "Render a scene in a real window, screenshot it, and have the vision model describe it against your expectation. Use after building or changing any scene.",
        "parameters": {"type": "object", "properties": {"scene": {"type": "string", "description": "res:// path to a .tscn"}, "expectation": {"type": "string"}}, "required": ["scene", "expectation"]}}},
    {"type": "function", "function": {"name": "run_scene_capture_output", "description": "Run a scene headless for a few seconds and return its printed output and errors (server-side logic, no rendering).",
        "parameters": {"type": "object", "properties": {"scene": {"type": "string"}, "seconds": {"type": "integer"}}, "required": ["scene"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Call when done. Summarise what you changed and why.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]


def _safe(game: Path, rel: str) -> Path:
    p = (game / rel).resolve()
    if game.resolve() not in p.parents and p != game.resolve():
        raise ValueError("path escapes game/")
    return p


def _exec(game: Path, name: str, args: dict, mcp=None) -> str:
    game = game.resolve()
    if name.startswith("mcp_") and mcp is not None:
        return mcp.call(name, args)
    if name == "search_docs":
        return rag.search(game.parent, args.get("query", ""), k=5) or "(no index built; run scripts/build_rag_index.py on the server)"
    if name == "visual_check":
        return vision.visual_check(game.parent, args["scene"], args.get("expectation", ""))
    if name == "run_scene_capture_output":
        code, out = godot.run(["--quit-after", str(int(args.get("seconds", 3)) * 60), args["scene"]], game, timeout_s=120)
        return f"exit {code}\n{out}"
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
    mcp = mcp_bridge.connect_if_configured(str(game))
    tools = TOOLS + (mcp.tools if mcp else [])
    model = llm.escalation_model() if escalate else llm.coder_model()
    messages: list[dict] = []
    summary = None
    steps = 0

    def gate_and_merge() -> tuple[bool, str]:
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

    try:
        system = llm.load_role(repo, "coder") + "\n\n" + (repo / "docs" / "09-godot-conventions.md").read_text()
        goal = str(spec.get("goal", spec))
        # Retrieval: the most relevant docs/code chunks for this goal, if an index exists.
        refs = rag.search(repo, goal + "\n" + "\n".join(str(a) for a in spec.get("acceptance", [])), k=6)
        user = ("Goal:\n" + goal + "\n\nAcceptance:\n"
                + "\n".join(f"- {a}" for a in spec.get("acceptance", [])) + "\n\nApproved assets available:\n"
                + "\n".join(str(p.relative_to(repo)) for p in (repo / "assets" / "approved").rglob("*") if p.is_file())[:3000]
                + (f"\n\nNotes from the previous failed attempt:\n{notes}" if notes else "")
                + (f"\n\nReference material (Godot 4 docs and this project; use search_docs for more):\n{refs}" if refs else "")
                + "\n\nWork in small steps. Call run_godot_check after edits. Call finish when the acceptance list is met.")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        for step in range(MAX_STEPS):
            steps = step + 1
            resp = llm.client(llm.slot_for(model)).chat.completions.create(model=model, messages=messages, tools=tools, temperature=0.1)
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
                    out = _exec(game, tc.function.name, args, mcp)
                except Exception as e:
                    out = f"ERROR: {e}"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out[:12000]})
            if summary is not None:
                break
        # Gate, then record the whole run with its pass/fail label for training.
        ok, msg = gate_and_merge()
        try:
            traces.write_coder_trace(repo, job_id=job_id, task_id=task_id, model=model, escalate=escalate,
                                     spec=spec, notes=notes, tools=tools, messages=messages,
                                     gate_ok=ok, gate_msg=msg, summary=summary, steps=steps)
        except Exception:
            log.exception("could not write coder trace")
        return ok, msg
    finally:
        if mcp:
            mcp.close()
        gitops.checkout(repo, base)
