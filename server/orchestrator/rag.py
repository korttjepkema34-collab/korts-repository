"""Retrieval for the coder: Godot 4 docs + this repo's own conventions and code, embedded with
nomic-embed-text through Ollama, searched by cosine similarity. Pure Python, no vector DB.

Index lives at data/rag/index.json. Build it with `python scripts/build_rag_index.py` (server).
Sources, in priority order:
  docs/09-godot-conventions.md, docs/10-game-design.md, style/style-bible.md
  game/**/*.gd, game/**/*.tscn (the project's own code; re-index as it grows)
  data/godot-docs/**/*.rst  (fetched by scripts/fetch_godot_docs.py; optional but the big win)

If the index is missing, search() returns "" and the coder runs as before.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

from . import llm

INDEX = Path("data") / "rag" / "index.json"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
CHUNK_CHARS = 1400
MAX_CHUNKS_PER_FILE = 60


def _index_path(repo: Path) -> Path:
    return repo / INDEX


def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), 32):
        batch = texts[i:i + 32]
        resp = llm.client().embeddings.create(model=EMBED_MODEL, input=batch)
        out.extend([d.embedding for d in resp.data])
    return out


def _chunks(text: str, path: str) -> list[dict]:
    """Split on headings (md/rst) or top-level funcs (gd), then by size."""
    if path.endswith(".gd"):
        parts = re.split(r"\n(?=func |static func |class |signal )", text)
    elif path.endswith(".rst"):
        parts = re.split(r"\n(?=[^\n]+\n[-=~^]{4,}\n)", text)
    else:
        parts = re.split(r"\n(?=#{1,4} )", text)
    out: list[dict] = []
    buf = ""
    for part in parts:
        if len(buf) + len(part) < CHUNK_CHARS:
            buf += part
            continue
        if buf.strip():
            out.append({"path": path, "text": buf.strip()})
        buf = part
        while len(buf) > CHUNK_CHARS * 2:
            out.append({"path": path, "text": buf[:CHUNK_CHARS * 2].strip()})
            buf = buf[CHUNK_CHARS * 2:]
    if buf.strip():
        out.append({"path": path, "text": buf.strip()})
    return out[:MAX_CHUNKS_PER_FILE]


def sources(repo: Path) -> list[Path]:
    files: list[Path] = []
    for rel in ("docs/09-godot-conventions.md", "docs/10-game-design.md", "style/style-bible.md",
                "docs/14-world-bible.md"):
        if (repo / rel).exists():
            files.append(repo / rel)
    game = repo / "game"
    if game.exists():
        files += [p for p in game.rglob("*.gd") if "addons" not in p.parts and ".godot" not in p.parts]
        files += [p for p in game.rglob("*.tscn") if ".godot" not in p.parts]
    docs = repo / "data" / "godot-docs"
    if docs.exists():
        files += sorted(docs.rglob("*.rst"))
    return files


def build(repo: Path, log=print) -> int:
    chunks: list[dict] = []
    for f in sources(repo):
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        rel = str(f.relative_to(repo)).replace("\\", "/")
        chunks += _chunks(text, rel)
    log(f"embedding {len(chunks)} chunks from {len(sources(repo))} files with {EMBED_MODEL} ...")
    vecs = embed([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        c["vec"] = [x / n for x in v]
    p = _index_path(repo)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"model": EMBED_MODEL, "chunks": chunks}))
    log(f"wrote {p} ({p.stat().st_size / 1e6:.1f} MB)")
    return len(chunks)


_cache: dict | None = None


def _load(repo: Path) -> dict | None:
    global _cache
    p = _index_path(repo)
    if not p.exists():
        return None
    if _cache is None or _cache.get("_mtime") != p.stat().st_mtime:
        _cache = json.loads(p.read_text())
        _cache["_mtime"] = p.stat().st_mtime
    return _cache


def search(repo: Path, query: str, k: int = 6, max_chars: int = 7000) -> str:
    """Top-k chunks formatted for a prompt. Empty string if no index or Ollama is down."""
    idx = _load(repo)
    if not idx or not idx.get("chunks"):
        return ""
    try:
        qv = embed([query[:4000]])[0]
    except Exception:
        return ""
    n = math.sqrt(sum(x * x for x in qv)) or 1.0
    qv = [x / n for x in qv]
    scored = []
    for c in idx["chunks"]:
        v = c["vec"]
        s = sum(a * b for a, b in zip(qv, v))
        scored.append((s, c))
    scored.sort(key=lambda t: -t[0])
    out, used = [], 0
    for s, c in scored[:k]:
        block = f"### {c['path']} (score {s:.2f})\n{c['text']}"
        if used + len(block) > max_chars:
            break
        out.append(block); used += len(block)
    return "\n\n".join(out)
