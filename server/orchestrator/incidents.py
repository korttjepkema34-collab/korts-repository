"""Incidents: problems with the studio itself, written down with a diagnosis, a plan, the
attempts made, and the resolution. One markdown file per incident in incidents/. The daily
report lists open ones; the engineer works studio-bug incidents; humans read the rest."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path


class Incidents:
    def __init__(self, repo: Path, ev):
        self.repo = repo; self.ev = ev
        self.dir = repo / "incidents"; self.dir.mkdir(exist_ok=True)
        self.index = self.dir / ".index.json"
        self.data = json.loads(self.index.read_text()) if self.index.exists() else {}

    def _save(self):
        self.index.write_text(json.dumps(self.data, indent=2))

    def open(self, kind: str, signature: str, detail: str, plan: str = "", diagnosis: str = "") -> Path | None:
        if signature in self.data and self.data[signature].get("status") == "open":
            self.data[signature]["count"] = self.data[signature].get("count", 1) + 1
            self.data[signature]["last"] = time.strftime("%Y-%m-%d %H:%M"); self._save()
            return self.dir / self.data[signature]["file"]
        slug = re.sub(r"[^a-z0-9]+", "-", signature.lower()).strip("-")[:50]
        fname = f"{time.strftime('%Y-%m-%d')}-{kind}-{slug}.md"
        path = self.dir / fname
        path.write_text(f"""# Incident: {signature[:80]}

- kind: {kind}
- status: open
- opened: {time.strftime('%Y-%m-%d %H:%M')}
- occurrences: 1

## Detected
{detail}

## Diagnosis
{diagnosis or '(pending)'}

## Plan
{plan or '(pending)'}

## Attempts

## Resolution
(open)
""")
        self.data[signature] = {"file": fname, "kind": kind, "status": "open", "count": 1, "opened": time.strftime("%Y-%m-%d %H:%M"), "attempts": 0}
        self._save(); self.ev(f"incident opened: {signature[:80]}")
        return path

    def note(self, signature: str, section: str, text: str) -> None:
        rec = self.data.get(signature)
        if not rec:
            return
        p = self.dir / rec["file"]; t = p.read_text()
        marker = f"## {section}\n"
        if marker in t:
            head, tail = t.split(marker, 1)
            nxt = tail.find("\n## ")
            body = tail if nxt < 0 else tail[:nxt]
            rest = "" if nxt < 0 else tail[nxt:]
            body = body.replace("(pending)", "").rstrip() + f"\n{text}\n"
            p.write_text(head + marker + body + rest)

    def attempt(self, signature: str, text: str) -> int:
        rec = self.data.get(signature)
        if not rec:
            return 0
        rec["attempts"] = rec.get("attempts", 0) + 1; self._save()
        self.note(signature, "Attempts", f"- {time.strftime('%Y-%m-%d %H:%M')} attempt {rec['attempts']}: {text}")
        return rec["attempts"]

    def resolve(self, signature: str, text: str) -> None:
        rec = self.data.get(signature)
        if not rec or rec.get("status") != "open":
            return
        rec["status"] = "resolved"; rec["resolved"] = time.strftime("%Y-%m-%d %H:%M"); self._save()
        p = self.dir / rec["file"]; t = p.read_text().replace("- status: open", "- status: resolved").replace("## Resolution\n(open)", f"## Resolution\n{time.strftime('%Y-%m-%d %H:%M')}: {text}")
        p.write_text(t); self.ev(f"incident resolved: {signature[:80]}")

    def open_list(self) -> list[dict]:
        return [dict(signature=s, **r) for s, r in self.data.items() if r.get("status") == "open"]

    def engineer_candidates(self) -> list[tuple[str, dict]]:
        return [(s, r) for s, r in self.data.items() if r.get("status") == "open" and r.get("kind") == "studio-bug" and r.get("attempts", 0) < 3]
