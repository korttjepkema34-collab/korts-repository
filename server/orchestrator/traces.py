"""Training-data capture. Every coder run and every reviewer verdict is written to data/traces/
so the studio accumulates labelled examples as a side effect of working.

  data/traces/coder/<job_id>.json      full tool-call transcript + gate outcome (pass/fail)
  data/traces/reviewer/verdicts.jsonl  one line per asset verdict, with image paths
  data/traces/reviewer/overrides.jsonl one line per owner correction (scripts/override.py)

Nothing here is read by the studio loop. training/build_datasets.py turns it into datasets.
See docs/15-training.md.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def traces_dir(repo: Path) -> Path:
    return repo / "data" / "traces"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def write_coder_trace(repo: Path, *, job_id: str, task_id: str, model: str, escalate: bool,
                      spec: dict, notes: str | None, tools: list[dict], messages: list[dict],
                      gate_ok: bool, gate_msg: str, summary: str | None, steps: int) -> Path:
    """Persist one coder trajectory. `messages` is the OpenAI-format transcript including tool
    results. gate_ok is the label: True only if the Godot 3 scan, headless check/tests and merge
    all succeeded."""
    d = traces_dir(repo) / "coder"
    d.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {
        "job_id": job_id, "task_id": task_id, "model": model, "escalate": escalate,
        "recorded_at": _now(), "spec": spec, "notes": notes, "steps": steps,
        "tools": tools, "messages": messages,
        "gate": {"ok": gate_ok, "message": gate_msg[-4000:]}, "summary": summary,
    }
    p = d / f"{job_id}.json"
    p.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return p


def write_review_trace(repo: Path, *, job_id: str, images: list[str], references: list[str],
                       spec: dict, verdict: str, reason: str, model: str, raw: str | None = None) -> None:
    d = traces_dir(repo) / "reviewer"
    d.mkdir(parents=True, exist_ok=True)
    rec = {"job_id": job_id, "recorded_at": _now(), "images": images, "references": references,
           "spec": spec, "verdict": verdict, "reason": reason, "model": model, "raw": raw}
    with (d / "verdicts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_override(repo: Path, *, image: str, machine_verdict: str | None, owner_verdict: str,
                   reason: str, job_id: str | None) -> None:
    d = traces_dir(repo) / "reviewer"
    d.mkdir(parents=True, exist_ok=True)
    rec = {"image": image, "recorded_at": _now(), "job_id": job_id, "machine_verdict": machine_verdict,
           "owner_verdict": owner_verdict, "reason": reason}
    with (d / "overrides.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def counts(repo: Path) -> dict[str, int]:
    """Cheap stats for the daily report and the auto-train rule."""
    d = traces_dir(repo)
    coder = list((d / "coder").glob("*.json")) if (d / "coder").exists() else []
    passed = 0
    for p in coder:
        try:
            if json.loads(p.read_text()).get("gate", {}).get("ok"):
                passed += 1
        except Exception:
            pass
    def lines(p: Path) -> int:
        return sum(1 for _ in p.open(encoding="utf-8")) if p.exists() else 0
    return {"coder_runs": len(coder), "coder_passed": passed,
            "verdicts": lines(d / "reviewer" / "verdicts.jsonl"),
            "overrides": lines(d / "reviewer" / "overrides.jsonl")}
