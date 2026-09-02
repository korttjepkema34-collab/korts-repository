"""Echo handler. Proves the queue, Syncthing, and result path work before any GPU tool exists."""
from __future__ import annotations

import json
from pathlib import Path

from shared.jobs import Job, Sidecar


def run(job: Job, out_dir: Path, cfg: dict) -> tuple[list[str], str | None]:
    out = out_dir / "stub.txt"
    out.write_text(json.dumps(job.spec, indent=2))
    sc = out_dir / "stub.json"
    Sidecar(generator="stub", model="none", licence="n/a", job_id=job.id, prompt=str(job.spec)).write(sc)
    return [str(out)], str(sc)


def unload(cfg: dict) -> None:
    pass
