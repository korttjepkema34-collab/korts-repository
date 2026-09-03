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


def _image_block(path: Path, upscale: bool = True) -> dict:
    """Small VLMs downsample; a 32x48 sprite becomes mush. Upscale with nearest-neighbour so the
    model sees the actual pixels, then send as PNG."""
    data: bytes
    mime = "image/png"
    if upscale:
        try:
            from PIL import Image
            import io
            im = Image.open(path).convert("RGBA")
            f = max(1, min(8, 640 // max(im.width, 1), 640 // max(im.height, 1)))
            if f > 1:
                im = im.resize((im.width * f, im.height * f), Image.NEAREST)
            buf = io.BytesIO(); im.save(buf, format="PNG"); data = buf.getvalue()
        except Exception:
            data = path.read_bytes(); mime = mimetypes.guess_type(path.name)[0] or "image/png"
    else:
        data = path.read_bytes(); mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(data).decode()}}


# Binary rubric: small vision models answer yes/no questions far more reliably than they give
# holistic verdicts. The verdict is computed from the answers by rule, not by the model.
RUBRIC = [
    ("subject_matches_spec", "Does the image show the subject the job spec asked for?", True),
    ("three_quarter_view", "Is it drawn in three-quarter top-down view (front faces of things visible), not pure top-down, side-on or isometric?", True),
    ("pixel_art_crisp", "Is it crisp pixel art with hard edges and flat colour areas (no smooth gradients, no blur, no photo texture)?", True),
    ("style_matches_reference", "Does its colour mood and drawing style match the reference images (ash, leather, rust, tarnished gold, cold glow)?", True),
    ("has_text_or_watermark", "Is there any text, lettering, logo or watermark in the image?", False),
    ("has_baked_glow", "Are there glowing halos, light rays or lens effects painted into the image?", False),
    ("has_artifacts", "Are there obvious artefacts: extra limbs, duplicated features, broken shapes, noise, or a visible seam?", False),
    ("background_clean", "If a sprite: is the background fully transparent or a single flat colour with nothing else in it?", True),
]
REQUIRED_TRUE = {"subject_matches_spec", "pixel_art_crisp", "style_matches_reference"}


def _ask(system: str, content: list, model: str) -> tuple[str, str, str]:
    resp = llm.client(llm.slot_for(model)).chat.completions.create(
        model=model, temperature=0.0, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": content}])
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "rejected", "reviewer returned invalid JSON", raw
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else data
    fails: list[str] = []
    for key, _q, want in RUBRIC:
        v = answers.get(key)
        if v is None:
            continue
        val = v if isinstance(v, bool) else str(v).strip().lower() in ("yes", "true", "y", "1")
        if val != want:
            fails.append(key)
    # rule: any required flag wrong, or any forbidden thing present => reject; else approve
    hard = [f for f in fails if f in REQUIRED_TRUE or f in ("has_text_or_watermark", "has_baked_glow", "has_artifacts")]
    verdict = "rejected" if hard else "approved"
    note = str(data.get("note", data.get("reason", "")))[:300]
    if not fails:
        reason = "all rubric checks passed" + (f"; {note}" if note else "")
    elif verdict == "approved":
        reason = "approved with warnings: " + ", ".join(fails) + (f"; {note}" if note else "")
    else:
        reason = "failed: " + ", ".join(fails) + (f"; {note}" if note else "")
    return verdict, reason[:500], raw
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
    questions = "\n".join(f"- {k}: {q}" for k, q, _ in RUBRIC)
    header = ("Job spec:\n" + json.dumps(job_spec, indent=2)[:2000] + "\n\nStyle bible excerpt:\n" + style[:3000]
              + "\n\nThe first image is the candidate (shown enlarged with hard pixels); any after are style references. "
              "Answer each question with true or false. Respond with JSON only: "
              "{\"answers\": {<key>: true|false, ...}, \"note\": \"one sentence on the biggest problem, or empty\"}\n"
              + questions)
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
