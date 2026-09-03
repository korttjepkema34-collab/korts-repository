#!/usr/bin/env python3
"""Your verdicts on the reviewer's verdicts. Ten minutes of this per week is what trains the
reviewer to your taste, and fixes any wrong calls right now.

    python scripts/override.py session            # walk through recent machine verdicts, one image at a time
    python scripts/override.py session --only rejected --limit 30
    python scripts/override.py approve assets/rejected/007-x/0001.png "good enough, palette is fine"
    python scripts/override.py reject  assets/approved/007-x/0002.png "cloak is purple, not leather"
    python scripts/override.py stats

Every decision (agree or disagree) is appended to data/traces/reviewer/overrides.jsonl and the
file + sidecar move to the folder you chose. Run on the server (where the traces are).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "server"))
from orchestrator import traces  # noqa: E402

IMG = {".png", ".webp", ".jpg", ".jpeg"}


def _open(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        print("  (could not open viewer:", e, ")")


def _sidecar(img: Path) -> Path | None:
    for c in (img.with_suffix(".json"), *img.parent.glob("*.json")):
        if c.exists():
            return c
    return None


def _current_verdict(img: Path) -> str | None:
    parts = img.resolve().relative_to(REPO.resolve()).parts
    return parts[1] if len(parts) > 2 and parts[0] == "assets" and parts[1] in ("approved", "rejected") else None


def decide(img: Path, owner_verdict: str, reason: str) -> None:
    img = img if img.is_absolute() else REPO / img
    if not img.exists():
        sys.exit(f"not found: {img}")
    machine = _current_verdict(img)
    sc = _sidecar(img)
    job_id = None
    if sc:
        try:
            d = json.loads(sc.read_text())
            job_id = d.get("job_id")
            d.setdefault("review", {})
            d["review"]["owner_override"] = {"verdict": owner_verdict, "reason": reason, "at": time.strftime("%Y-%m-%d %H:%M")}
            sc.write_text(json.dumps(d, indent=2))
        except Exception:
            pass
    rel_before = str(img.relative_to(REPO)).replace("\\", "/")
    if machine and machine != owner_verdict:
        dest_dir = REPO / "assets" / owner_verdict / img.parent.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img), dest_dir / img.name)
        if sc and sc.parent == img.parent:
            # move the sidecar too unless other images in the folder still need it
            if not any(p.suffix.lower() in IMG for p in img.parent.iterdir()):
                shutil.move(str(sc), dest_dir / sc.name)
            else:
                shutil.copy2(str(sc), dest_dir / sc.name)
        img = dest_dir / img.name
    traces.write_override(REPO, image=str(img.relative_to(REPO)).replace("\\", "/"), machine_verdict=machine,
                          owner_verdict=owner_verdict, reason=reason, job_id=job_id)
    print(f"  {rel_before}: machine={machine} you={owner_verdict}" + ("" if machine == owner_verdict else f" -> moved to assets/{owner_verdict}/"))


def session(only: str | None, limit: int) -> None:
    vpath = REPO / "data" / "traces" / "reviewer" / "verdicts.jsonl"
    seen_path = REPO / "data" / "traces" / "reviewer" / "overrides.jsonl"
    done = set()
    if seen_path.exists():
        for l in seen_path.open(encoding="utf-8"):
            if l.strip():
                done.add(Path(json.loads(l)["image"]).name)
    rows = [json.loads(l) for l in vpath.open(encoding="utf-8") if l.strip()] if vpath.exists() else []
    queue = []
    for v in reversed(rows):
        if only and v["verdict"] != only:
            continue
        for img in v.get("images", []):
            name = Path(img).name
            if name in done:
                continue
            cur = next((p for b in ("approved", "rejected", "incoming") for p in (REPO / "assets" / b).rglob(name)), None)
            if cur:
                queue.append((cur, v))
    queue = queue[:limit]
    if not queue:
        print("nothing new to review"); return
    print(f"{len(queue)} images. Keys: y = approve, n = reject, s = skip, q = quit. Add a note after a space: 'n cloak wrong colour'")
    for i, (img, v) in enumerate(queue, 1):
        print(f"\n[{i}/{len(queue)}] {img.relative_to(REPO)}\n  machine said {v['verdict'].upper()}: {v.get('reason', '')[:200]}\n  spec: {str(v.get('spec', {}).get('prompt', ''))[:160]}")
        _open(img)
        ans = input("  y/n/s/q > ").strip()
        if not ans or ans[0] == "s":
            continue
        if ans[0] == "q":
            break
        note = ans[1:].strip()
        if ans[0] == "y":
            decide(img, "approved", note or "owner approved")
        elif ans[0] == "n":
            decide(img, "rejected", note or "owner rejected")
    print("\n", traces.counts(REPO))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("session"); s.add_argument("--only", choices=["approved", "rejected"]); s.add_argument("--limit", type=int, default=40)
    for name in ("approve", "reject"):
        p = sub.add_parser(name); p.add_argument("image"); p.add_argument("reason", nargs="?", default="")
    sub.add_parser("stats")
    a = ap.parse_args()
    if a.cmd == "session":
        session(a.only, a.limit)
    elif a.cmd == "stats":
        print(json.dumps(traces.counts(REPO), indent=2))
    else:
        decide(Path(a.image), "approved" if a.cmd == "approve" else "rejected", a.reason or f"owner {a.cmd}")


if __name__ == "__main__":
    main()
