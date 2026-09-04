"""Nightly Windows build so there is something to play on return. Needs Godot export templates
installed (Editor > Manage Export Templates) and game/export_presets.cfg (in the repo)."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


def build(repo: Path, ev) -> str | None:
    b = os.environ.get("GODOT_BIN")
    if not b or not Path(b).exists():
        return None
    day = time.strftime("%Y-%m-%d")
    out = repo / "builds" / f"reapers-relics-{day}"
    out.mkdir(parents=True, exist_ok=True)
    exe = out / "ReapersRelics.exe"
    p = subprocess.run([b, "--headless", "--path", str(repo / "game"), "--export-release", "Windows Desktop", str(exe)],
                       capture_output=True, text=True, timeout=900)
    if exe.exists() and exe.stat().st_size > 1_000_000:
        ev(f"build: {exe.relative_to(repo)} ({exe.stat().st_size // 1_000_000} MB)")
        # keep the last 7 builds
        for old in sorted(repo.joinpath("builds").glob("reapers-relics-*"))[:-7]:
            import shutil; shutil.rmtree(old, ignore_errors=True)
        return str(exe.relative_to(repo))
    ev("build failed: " + (p.stdout + p.stderr)[-300:].replace("\n", " "))
    return None
