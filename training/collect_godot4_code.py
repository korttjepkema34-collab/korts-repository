"""Collect permissively licensed Godot 4 GDScript from public repos into SFT examples.

    python training/collect_godot4_code.py            # clones the default list into data/godot4-code/repos
    python training/collect_godot4_code.py --repo-url https://github.com/x/y  # add one

Each repo is filtered by its project.godot: only projects whose `config/features` names a 4.x
engine are used, so Godot 3 code never enters the dataset (the exact bug we are training out).
Every .gd file becomes one example: user = "write <path> for <project>; it does: <doc comment>",
assistant = the file. Weak supervision, but it teaches Godot 4 syntax, @export/@onready,
signals, CharacterBody2D, TileMapLayer, multiplayer API, static typing.

Default sources are MIT. Check the LICENSE of anything you add; keep the list in REPOS.
Output: data/godot4-code/<repo>.jsonl  (picked up by build_datasets.py coder)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPOS = [
    # (url, branch or None, licence)
    ("https://github.com/godotengine/godot-demo-projects", "master", "MIT"),
    ("https://github.com/gdquest-demos/godot-4-3d-third-person-controller", None, "MIT"),
]
SKIP_DIRS = {"addons", ".godot", ".import", "node_modules"}
MAX_FILE = 12_000  # chars


def is_godot4(project_godot: Path) -> bool:
    try:
        t = project_godot.read_text(errors="ignore")
    except OSError:
        return False
    return "config_version=5" in t and ('"4.' in t or "'4." in t or "features=PackedStringArray" in t)


def doc_comment(src: str) -> str:
    lines = []
    for l in src.splitlines():
        s = l.strip()
        if s.startswith("##") or s.startswith("#"):
            lines.append(s.lstrip("#").strip())
        elif s and not s.startswith("extends") and not s.startswith("class_name") and not s.startswith("@"):
            break
    return " ".join(lines)[:300]


def examples_for(project_dir: Path, repo_name: str, licence: str) -> list[dict]:
    out = []
    for gd in project_dir.rglob("*.gd"):
        if SKIP_DIRS & set(gd.parts):
            continue
        try:
            src = gd.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not src.strip() or len(src) > MAX_FILE:
            continue
        if re.search(r"\b(export var|onready var|yield\(|KinematicBody2D|PoolStringArray)\b", src):
            continue  # stray Godot 3 file
        rel = gd.relative_to(project_dir).as_posix()
        purpose = doc_comment(src) or f"the {gd.stem.replace('_', ' ')} script"
        user = (f"Write the GDScript file `{rel}` for the Godot 4 project `{project_dir.name}`. "
                f"Purpose: {purpose}. Godot 4.x, GDScript 2.0, static typing.")
        out.append({"messages": [{"role": "user", "content": user}, {"role": "assistant", "content": f"```gdscript\n{src.rstrip()}\n```"}],
                    "source": f"{repo_name}:{project_dir.name}/{rel}", "licence": licence})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--repo-url", action="append", default=[], help="extra git URL(s); licence assumed MIT, verify")
    a = ap.parse_args()
    root = Path(a.repo).resolve() / "data" / "godot4-code"
    clones = root / "repos"; clones.mkdir(parents=True, exist_ok=True)
    todo = REPOS + [(u, None, "MIT (verify)") for u in a.repo_url]
    for url, branch, licence in todo:
        name = url.rstrip("/").split("/")[-1]
        dst = clones / name
        if not dst.exists():
            cmd = ["git", "clone", "--depth", "1"] + (["-b", branch] if branch else []) + [url, str(dst)]
            print("cloning", url)
            if subprocess.run(cmd).returncode != 0:
                print("  clone failed, skipping"); continue
        n = 0
        with (root / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for pg in dst.rglob("project.godot"):
                if not is_godot4(pg):
                    continue
                for ex in examples_for(pg.parent, name, licence):
                    f.write(json.dumps(ex, ensure_ascii=False) + "\n"); n += 1
        print(f"{name}: {n} Godot 4 examples")


if __name__ == "__main__":
    main()
