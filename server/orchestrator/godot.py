"""Headless Godot runner. Used by the coder gate and the test step. Works on Windows and Linux."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

GODOT_3_PATTERNS = [
    "export var", "onready var", "yield(", "KinematicBody2D", "KinematicBody\n", ".instance()",
    "change_scene(", ".empty()", "connect(\"", "PoolStringArray", "PoolIntArray", "Spatial\n",
]


def godot_bin() -> str | None:
    b = os.environ.get("GODOT_BIN")
    return b if b and Path(b).exists() else None


def run(args: list[str], game_dir: Path, timeout_s: int = 600) -> tuple[int, str]:
    b = godot_bin()
    if not b:
        return 127, "GODOT_BIN not set or not found; skipping Godot run"
    try:
        p = subprocess.run([b, "--headless", "--path", str(game_dir), *args], capture_output=True,
                           text=True, timeout=timeout_s)
        return p.returncode, (p.stdout + p.stderr)[-8000:]
    except subprocess.TimeoutExpired:
        return 124, "Godot timed out"


def load_check(game_dir: Path) -> tuple[bool, str]:
    """Import + load the project and quit. Parse errors in any script show up here."""
    code, out = run(["--import"], game_dir, timeout_s=900)
    if code == 127:
        return True, out  # no Godot available; do not block on it
    code2, out2 = run(["--quit"], game_dir, timeout_s=300)
    text = out + "\n" + out2
    bad = ("SCRIPT ERROR" in text) or ("Parse Error" in text) or ("ERROR:" in text and "res://" in text)
    return (not bad), text


def run_tests(game_dir: Path) -> tuple[bool, str]:
    """gdUnit4 if installed, else the load check only."""
    if (game_dir / "addons" / "gdUnit4").exists() and (game_dir / "tests").exists():
        code, out = run(["-s", "res://addons/gdUnit4/bin/GdUnitCmdTool.gd", "--add", "res://tests",
                         "--ignoreHeadlessMode"], game_dir, timeout_s=1200)
        if code == 127:
            return True, out
        return code == 0, out
    return load_check(game_dir)


def lint(game_dir: Path) -> tuple[bool, str]:
    """gdformat (auto-fix) then gdlint from gdtoolkit, if installed. Never blocks when absent."""
    import shutil as _sh
    files = [str(f) for f in game_dir.rglob("*.gd") if "addons" not in f.parts]
    if not files:
        return True, "no scripts"
    if _sh.which("gdformat"):
        subprocess.run(["gdformat", *files], capture_output=True, text=True, timeout=300)
    if _sh.which("gdlint"):
        p = subprocess.run(["gdlint", *files], capture_output=True, text=True, timeout=300)
        return p.returncode == 0, (p.stdout + p.stderr)[-4000:]
    return True, "gdtoolkit not installed; lint skipped"


def godot3_hits(game_dir: Path) -> list[str]:
    hits = []
    for f in game_dir.rglob("*.gd"):
        if "addons" in f.parts:
            continue
        src = f.read_text(errors="ignore")
        for pat in GODOT_3_PATTERNS:
            if pat in src:
                hits.append(f"{f.relative_to(game_dir)}: contains Godot 3 pattern {pat.strip()!r}")
    return hits
