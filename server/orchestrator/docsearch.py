"""Search the engine's own class reference so the coder never guesses an API.

Build the dump once on the server (exact match for the installed Godot version):
    scripts/dump_godot_docs.ps1     (Windows)   or   scripts/dump_godot_docs.sh
It writes XML class files to server/godot-docs/. This module indexes them with a small
BM25-style scorer (no dependencies) and returns compact member signatures.
"""
from __future__ import annotations

import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

_INDEX: list[dict] | None = None
_DF: dict[str, int] = {}
_TOK = re.compile(r"[a-z0-9_]+")


def docs_dir() -> Path:
    return Path(os.environ.get("GODOT_DOCS_DIR") or Path(__file__).resolve().parents[1] / "godot-docs")


def _tokens(s: str) -> list[str]:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)  # split CamelCase
    return _TOK.findall(s.lower())


def _entries_from_class(path: Path) -> list[dict]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    cname = root.get("name", path.stem)
    inherits = root.get("inherits", "")
    brief = (root.findtext("brief_description") or "").strip()
    out = [{"cls": cname, "kind": "class", "sig": f"class {cname}" + (f" extends {inherits}" if inherits else ""), "doc": brief[:300]}]
    for m in root.iter("method"):
        ret = m.find("return")
        rt = ret.get("type", "void") if ret is not None else "void"
        args = ", ".join(f"{p.get('name')}: {p.get('type')}" + (f" = {p.get('default')}" if p.get("default") else "") for p in m.findall("param"))
        desc = (m.findtext("description") or "").strip()
        out.append({"cls": cname, "kind": "method", "sig": f"{cname}.{m.get('name')}({args}) -> {rt}", "doc": desc[:240]})
    for mem in root.iter("member"):
        out.append({"cls": cname, "kind": "property", "sig": f"{cname}.{mem.get('name')}: {mem.get('type')}", "doc": (mem.text or '').strip()[:200]})
    for sig in root.iter("signal"):
        args = ", ".join(f"{p.get('name')}: {p.get('type')}" for p in sig.findall("param"))
        out.append({"cls": cname, "kind": "signal", "sig": f"signal {cname}.{sig.get('name')}({args})", "doc": (sig.findtext("description") or '').strip()[:200]})
    for c in root.iter("constant"):
        out.append({"cls": cname, "kind": "constant", "sig": f"{cname}.{c.get('name')} = {c.get('value')}", "doc": (c.text or '').strip()[:120]})
    return out


def build_index() -> int:
    global _INDEX, _DF
    _INDEX, _DF = [], {}
    d = docs_dir()
    if not d.exists():
        return 0
    for f in sorted(d.rglob("*.xml")):
        for e in _entries_from_class(f):
            toks = _tokens(e["sig"] + " " + e["doc"])
            e["toks"] = toks
            e["tf"] = {}
            for t in toks:
                e["tf"][t] = e["tf"].get(t, 0) + 1
            for t in set(toks):
                _DF[t] = _DF.get(t, 0) + 1
            _INDEX.append(e)
    return len(_INDEX)


def search(query: str, k: int = 8) -> str:
    if _INDEX is None:
        build_index()
    if not _INDEX:
        return ("Godot class reference dump not found at %s. Run scripts/dump_godot_docs on the server. "
                "Fall back to docs/16-godot4-cookbook.md." % docs_dir())
    q = _tokens(query)
    n = len(_INDEX)
    avg = sum(len(e["toks"]) for e in _INDEX) / max(1, n)
    scored = []
    for e in _INDEX:
        s = 0.0
        for t in q:
            tf = e["tf"].get(t, 0)
            if not tf:
                continue
            idf = math.log(1 + (n - _DF.get(t, 0) + 0.5) / (_DF.get(t, 0) + 0.5))
            s += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(e["toks"]) / avg))
        if e["kind"] == "class" and s:
            s *= 1.3
        if s:
            scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    lines = [f"[{e['kind']}] {e['sig']}" + (f"\n    {e['doc']}" if e["doc"] else "") for _, e in scored[:k]]
    return "\n".join(lines) if lines else "no matches; try the class name or a different verb"
