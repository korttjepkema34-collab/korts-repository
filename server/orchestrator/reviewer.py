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


def _ask(system: str, content: list, model: str) -> tuple[str, str, str]:
    resp = llm.client(llm.slot_for(model)).chat.completions.create(
        model=model, temperature=0.1, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    verdict = "approved" if str(data.get("verdict", "")).lower().startswith("appr") else "rejected"
    return verdict, str(data.get("reason", ""))[:500], raw


def review_result(repo: Path, res: Result, job_spec: dict) -> tuple[str, str, dict[str, tuple[str, str]]]:
    """Returns (job verdict, reason, per-output verdicts). Each candidate image is judged on its
    own (one image + style references per call), so approved and rejected candidates from the
    same job land in different folders and every verdict is a clean one-image training label.
    The job is approved if at least one candidate is. Non-image assets are approved on existence."""
    system = llm.load_role(repo, "reviewer")
    style = (repo / "style" / "style-bible.md").read_text()
    outputs = [repo / o for o in res.outputs]
    images = [p for p in outputs if p.suffix.lower() in IMAGE_EXT and p.exists()]
    if not outputs or not all(p.exists() for p in outputs):
        return "rejected", "output files missing (Syncthing not caught up, or the worker wrote elsewhere)", {}
    if not images:
        return "approved", "non-image asset; automatic approval until audio review exists", {}

    refs = [p for p in (repo / "style" / "references").glob("*") if p.suffix.lower() in IMAGE_EXT][:2]
    header = ("Job spec:\n" + json.dumps(job_spec, indent=2)[:3000] + "\n\nStyle bible:\n" + style[:6000]
              + "\n\nThe first image is the candidate; any after are style references. "
              "Respond with JSON {\"verdict\": \"approved\"|\"rejected\", \"reason\": \"...\"}.")
    model = llm.reviewer_model()
    per: dict[str, tuple[str, str]] = {}
    reasons: list[str] = []
    for img in images[:8]:
        rel = str(img.relative_to(repo)).replace("\\", "/")
        content = [{"type": "text", "text": header}, _image_block(img)] + [_image_block(p) for p in refs]
        try:
            verdict, reason, raw = _ask(system, content, model)
        except Exception as e:  # reviewer down: do not block the pipeline, but do not approve either
            verdict, reason, raw = "rejected", f"reviewer error: {e}", None
        per[rel] = (verdict, reason)
        reasons.append(f"{img.name}: {verdict} ({reason[:120]})")
        try:  # training-data capture; files move afterwards, the dataset builder re-resolves paths
            traces.write_review_trace(repo, job_id=res.job_id, images=[rel],
                                      references=[str(p.relative_to(repo)).replace("\\", "/") for p in refs],
                                      spec=job_spec, verdict=verdict, reason=reason, model=model, raw=raw)
        except Exception:
            pass
    approved = sum(1 for v, _ in per.values() if v == "approved")
    job_verdict = "approved" if approved else "rejected"
    return job_verdict, f"{approved}/{len(per)} candidates approved; " + "; ".join(reasons)[:900], per


def file_verdict(repo: Path, res: Result, verdict: str, reason: str,
                 per_output: dict[str, tuple[str, str]] | None = None) -> list[str]:
    """Move each output to approved/ or rejected/ (its own verdict when there is one, else the
    job's), copy the sidecar next to every moved file, record verdicts in it. Returns the
    approved paths (what the coder may import), or everything moved if nothing was approved."""
    per_output = per_output or {}
    moved: dict[str, list[str]] = {"approved": [], "rejected": []}
    sidecar_src = repo / res.sidecar if res.sidecar else None
    sidecar_data: dict = {}
    if sidecar_src and sidecar_src.exists():
        try:
            sidecar_data = json.loads(sidecar_src.read_text())
        except Exception:
            sidecar_data = {}
    for rel in res.outputs:
        src = repo / rel
        if not src.exists():
            continue
        v, why = per_output.get(rel.replace("\\", "/"), (verdict, reason))
        dst = repo / "assets" / v / Path(rel).relative_to("assets/incoming")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved[v].append(str(dst.relative_to(repo)).replace("\\", "/"))
        if sidecar_src:
            sc = dict(sidecar_data)
            sc["review"] = {"verdict": v, "reason": why, "by": llm.reviewer_model(), "job_verdict": verdict}
            sc_dst = dst.parent / sidecar_src.name
            if not sc_dst.exists():
                sc_dst.write_text(json.dumps(sc, indent=2))
    if sidecar_src and sidecar_src.exists():
        sidecar_src.unlink()
    return moved["approved"] or moved["rejected"]
