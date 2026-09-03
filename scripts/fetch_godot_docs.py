#!/usr/bin/env python3
"""Download the Godot 4 reference docs (reStructuredText) into data/godot-docs/ for retrieval.

    python scripts/fetch_godot_docs.py            # 'stable' branch, class reference + key tutorials
    python scripts/fetch_godot_docs.py --branch 4.4 --all

About 40 MB zipped. Only the folders the coder needs are kept (classes/, tutorials/scripting,
2d, physics, networking, best_practices, getting_started/step_by_step) unless --all.
Then run scripts/build_rag_index.py. Re-run both when you move to a new Godot minor version.
"""
from __future__ import annotations

import argparse
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KEEP = ("classes/", "tutorials/scripting/", "tutorials/2d/", "tutorials/physics/", "tutorials/networking/",
        "tutorials/best_practices/", "getting_started/step_by_step/", "tutorials/animation/", "tutorials/ui/",
        "tutorials/inputs/", "tutorials/audio/", "tutorials/rendering/", "tutorials/shaders/")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="stable", help="godot-docs branch: stable, 4.4, 4.3, master")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=str(REPO / "data" / "godot-docs"))
    a = ap.parse_args()
    url = f"https://github.com/godotengine/godot-docs/archive/refs/heads/{a.branch}.zip"
    print("downloading", url, flush=True)
    data = urllib.request.urlopen(url, timeout=120).read()
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    n = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            parts = info.filename.split("/", 1)
            if len(parts) < 2 or not parts[1].endswith(".rst"):
                continue
            rel = parts[1]
            if not a.all and not rel.startswith(KEEP):
                continue
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(info))
            n += 1
    (out / "VERSION").write_text(a.branch)
    print(f"{n} .rst files in {out}. Next: python scripts/build_rag_index.py")


if __name__ == "__main__":
    sys.exit(main())
