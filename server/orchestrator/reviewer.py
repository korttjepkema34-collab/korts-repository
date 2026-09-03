"""Automatic asset review with a vision model, then move to approved/ or rejected/."""
from __future__ import annotations

import base64
import json
import mimetypes
import shutil
from pathlib import Path

from shared.jobs import Result

from . import llm, traces

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _image_block(path: Path) -> dict:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}


def review_result(repo: Path, res: Result, job_spec: dict) -> tuple[str, str]:
    """Returns (verdict, reason). Non-image assets are approved on existence for now."""
    system = llm.load_role(repo, "reviewer")
    style = (repo / "style" / "style-bible.md").read_text()
    outputs = [repo / o for o in res.outputs]
    images = [p for p in outputs if p.suffix.lower() in IMAGE_EXT and p.exists()]
    if not outputs or not all(p.exists() for p in outputs):
        return "rejected", "output files missing (Syncthing not caught up, or the worker wrote elsewhere)"
    if not images:
        return "approved", "non-image asset; automatic approval until audio/3D review exists"

    refs = [p for p in (repo / "style" / "references").glob("*") if p.suffix.lower() in IMAGE_EXT][:2]
    content = [{"type": "text", "text": "Job spec:\n" + json.dumps(job_spec, indent=2)[:3000]
                + "\n\nStyle bible:\n" + style[:6000]
                + "\n\nFirst images are the candidates; any after are style references. "
                "Respond with JSON {\"verdict\": \"approved\"|\"rejected\", \"reason\": \"...\"}."}]
    content += [_image_block(p) for p in images[:4]]
    content += [_image_block(p) for p in refs]
    model = llm.reviewer_model()
    try:
        resp = llm.client(llm.slot_for(model)).chat.completions.create(
            model=model, temperature=0.1,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        verdict = "approved" if str(data.get("verdict", "")).lower().startswith("appr") else "rejected"
        reason = str(data.get("reason", ""))[:500]
    except Exception as e:  # reviewer down: do not block the pipeline, but do not approve either
        return "rejected", f"reviewer error: {e}"
    # Training-data capture: paths are recorded relative to the repo; file_verdict() moves the
    # files afterwards, so the dataset builder resolves incoming/ -> approved|rejected/ itself.
    try:
        traces.write_review_trace(repo, job_id=res.job_id,
                                  images=[str(p.relative_to(repo)) for p in images[:4]],
                                  references=[str(p.relative_to(repo)) for p in refs],
                                  spec=job_spec, verdict=verdict, reason=reason, model=model, raw=raw)
    except Exception:
        pass
    return verdict, reason


def file_verdict(repo: Path, res: Result, verdict: str, reason: str) -> list[str]:
    """Move outputs + sidecar to approved/ or rejected/, record the verdict in the sidecar."""
    moved = []
    dest_root = repo / "assets" / verdict
    for rel in res.outputs + ([res.sidecar] if res.sidecar else []):
        src = repo / rel
        if not src.exists():
            continue
        rel_inside = Path(rel).relative_to("assets/incoming")
        dst = dest_root / rel_inside
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append(str(dst.relative_to(repo)))
        if dst.suffix == ".json":
            try:
                sc = json.loads(dst.read_text())
                sc["review"] = {"verdict": verdict, "reason": reason, "by": llm.reviewer_model()}
                dst.write_text(json.dumps(sc, indent=2))
            except Exception:
                pass
    return moved
