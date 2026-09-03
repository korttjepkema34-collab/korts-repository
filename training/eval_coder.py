"""Measure a coder model: gate pass rate on the held-out tasks in training/eval/heldout_tasks.json.
Run on the server (it needs GODOT_BIN and the orchestrator venv). Works on a throwaway clone so
nothing touches the real game/ folder or its branches.

    cd server && .\\.venv\\Scripts\\python.exe ..\\training\\eval_coder.py --model qwen3.6:35b-a3b-coding
    cd server && .\\.venv\\Scripts\\python.exe ..\\training\\eval_coder.py --model reapers-coder --base-url http://127.0.0.1:11434/v1

Prints a table and appends a row to reports/eval-coder.md. Compare rows before and after a
fine-tune; a fine-tune that does not raise this number is not activated.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "server"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="Ollama tag or served model name to evaluate as CODER_MODEL")
    ap.add_argument("--base-url", default=None, help="CODER_BASE_URL if the model is served elsewhere")
    ap.add_argument("--tasks", default=str(HERE / "eval" / "heldout_tasks.json"))
    ap.add_argument("--only", default=None, help="comma-separated task ids")
    ap.add_argument("--keep", action="store_true", help="keep the scratch clone")
    a = ap.parse_args()
    os.environ["CODER_MODEL"] = a.model
    if a.base_url:
        os.environ["CODER_BASE_URL"] = a.base_url
    os.environ.setdefault("ORCHESTRATOR_MODEL", a.model)
    from orchestrator import coder  # noqa: E402

    tasks = json.loads(Path(a.tasks).read_text())
    if a.only:
        want = set(a.only.split(",")); tasks = [t for t in tasks if t["id"] in want]
    scratch = Path(tempfile.mkdtemp(prefix="coder-eval-"))
    subprocess.run(["git", "clone", "-q", str(REPO), str(scratch)], check=True)
    # traces from eval runs are still useful data, but keep them out of the real trace folder
    results = []
    for t in tasks:
        t0 = time.time()
        try:
            ok, msg = coder.run_code_job(scratch, t["id"], f"{t['id']}-eval", {"goal": t["goal"], "acceptance": t["acceptance"]}, None, False)
        except Exception as e:
            ok, msg = False, f"crash: {e}"
        results.append({"id": t["id"], "ok": ok, "minutes": round((time.time() - t0) / 60, 1), "msg": msg[:200].replace("\n", " ")})
        print(f"{t['id']}: {'PASS' if ok else 'FAIL'} ({results[-1]['minutes']} min) {results[-1]['msg']}", flush=True)
        # reset the scratch clone between tasks so failures do not compound
        subprocess.run(["git", "-C", str(scratch), "checkout", "-q", "-f", "."], check=False)
        subprocess.run(["git", "-C", str(scratch), "clean", "-qfd", "game"], check=False)
    passed = sum(r["ok"] for r in results)
    line = f"| {time.strftime('%Y-%m-%d %H:%M')} | {a.model} | {passed}/{len(results)} | {sum(r['minutes'] for r in results):.0f} min | {' '.join(r['id'] for r in results if r['ok'])} |\n"
    rep = REPO / "reports" / "eval-coder.md"
    if not rep.exists():
        rep.write_text("# Coder eval (held-out tasks)\n\n| when | model | passed | time | passed ids |\n|---|---|---|---|---|\n")
    rep.open("a").write(line)
    print(f"\n{passed}/{len(results)} passed. Row appended to {rep}")
    if not a.keep:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
