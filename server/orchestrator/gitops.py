"""Minimal git helpers. The orchestrator is the integrator: it commits the task board, docs and
reports on main, and merges coder branches after the gate passes."""
from __future__ import annotations

import subprocess
from pathlib import Path


def git(repo: Path, *args: str, check: bool = False) -> tuple[int, str]:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p.returncode, (p.stdout + p.stderr).strip()


def current_branch(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD")[1]


def commit_paths(repo: Path, paths: list[str], message: str) -> bool:
    git(repo, "add", "-A", "--", *paths)
    code, out = git(repo, "diff", "--cached", "--quiet")
    if code == 0:
        return False  # nothing staged
    git(repo, "-c", "user.name=studio-orchestrator", "-c", "user.email=orchestrator@studio.local",
        "commit", "-q", "-m", message)
    return True


def new_branch(repo: Path, name: str, base: str) -> None:
    git(repo, "checkout", "-q", "-B", name, base, check=True)


def checkout(repo: Path, name: str) -> None:
    git(repo, "checkout", "-q", name, check=True)


def merge(repo: Path, branch: str, into: str, message: str) -> bool:
    checkout(repo, into)
    code, out = git(repo, "-c", "user.name=studio-orchestrator", "-c", "user.email=orchestrator@studio.local",
                    "merge", "--no-ff", "-q", "-m", message, branch)
    if code != 0:
        git(repo, "merge", "--abort")
        return False
    return True


def push(repo: Path, branch: str) -> None:
    git(repo, "push", "-q", "-u", "origin", branch)  # best effort; ignore failures offline
