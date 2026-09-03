#!/usr/bin/env python3
"""Build (or rebuild) the retrieval index the coder searches: data/rag/index.json.
Needs Ollama running with the embedding model (`ollama pull nomic-embed-text`).

    python scripts/build_rag_index.py          # from the repo root; reads server/.env if present

Takes a few minutes on CPU for the class reference (~10k chunks). Re-run after fetching new docs
or every week or so as game/ grows; the orchestrator does not rebuild it on its own.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "server"))

env = REPO / "server" / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.split("#", 1)[0].strip())
os.environ.setdefault("ORCHESTRATOR_MODEL", "unused")

from orchestrator import rag  # noqa: E402

n = rag.build(REPO)
print(f"indexed {n} chunks. Test: python scripts/build_rag_index.py --query 'how do I connect a signal'")
if "--query" in sys.argv:
    q = sys.argv[sys.argv.index("--query") + 1]
    print(rag.search(REPO, q, k=3))
