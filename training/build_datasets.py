"""Turn the studio's traces into training datasets. Runs on the server (CPU only, stdlib + Pillow).

    python training/build_datasets.py sdxl_lora   [--out assets/training/datasets/<name>]
    python training/build_datasets.py coder
    python training/build_datasets.py reviewer

Inputs
  sdxl_lora : assets/approved/**/*.png + style/references/*.png, captions from sidecar prompts
  coder     : data/traces/coder/*.json (gate-passed runs -> SFT; pass/fail pairs -> DPO)
              plus data/godot4-code/*.jsonl if training/collect_godot4_code.py has run
  reviewer  : data/traces/reviewer/verdicts.jsonl with owner corrections from overrides.jsonl

Outputs go under assets/training/datasets/ so Syncthing carries them to the GPU box.
The orchestrator imports build() from this file (server/orchestrator/training.py).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

TRIGGER = "rrstyle"                      # LoRA trigger word; put it first in every image prompt
IMAGE_EXT = {".png", ".webp", ".jpg", ".jpeg"}
MAX_TOOL_RESULT = 3500                   # chars kept per tool result in SFT transcripts
MAX_TRANSCRIPT = 70_000                  # chars; longer trajectories are dropped
MIN_IMAGE_SIDE = 1024                    # kohya trains SDXL at 1024; pixel art is upscaled nearest


def _log(msg: str) -> None:
    print(f"[build_datasets] {msg}", flush=True)


# ----------------------------------------------------------------------------- sdxl_lora
def _caption(sidecar: Path | None, fallback: str) -> str:
    prompt = ""
    if sidecar and sidecar.exists():
        try:
            prompt = json.loads(sidecar.read_text()).get("prompt") or ""
        except Exception:
            prompt = ""
    prompt = re.sub(r"\. Reviewer notes from earlier attempt:.*$", "", prompt, flags=re.S)
    prompt = re.sub(r"\s+", " ", prompt).strip(" ,.")
    if not prompt:
        prompt = fallback
    return f"{TRIGGER}, {prompt}"


def _upscale_copy(src: Path, dst: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(src, dst)
        return
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    if max(w, h) < MIN_IMAGE_SIDE:
        f = -(-MIN_IMAGE_SIDE // max(w, h))  # ceil
        im = im.resize((w * f, h * f), Image.NEAREST)
    # flatten transparency onto the palette's ash colour so the LoRA does not learn checkerboards
    bg = Image.new("RGBA", im.size, (46, 43, 51, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(dst.with_suffix(".png"))


def build_sdxl_lora(repo: Path, out: Path) -> int:
    img_dir = out / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    sources: list[tuple[Path, Path | None, str]] = []
    approved = repo / "assets" / "approved"
    if approved.exists():
        for p in sorted(approved.rglob("*")):
            if p.suffix.lower() in IMAGE_EXT:
                sc = next((s for s in p.parent.glob("*.json")), None)
                sources.append((p, sc, f"pixel art asset, {p.parent.name.replace('-', ' ')}"))
    for p in sorted((repo / "style" / "references").glob("*.png")):
        if p.name == "palette.png":
            continue
        desc = {"mock-day.png": "the Keep by day, cobbled square, brick houses, market stalls, warm sun",
                "mock-night.png": "the Keep at night, lamps, fog, a horde of Thralls with glowing eyes"}.get(p.name, p.stem.replace("-", " "))
        sources.append((p, None, desc + ", pixel art, three-quarter top-down, 16 colour palette"))
    for i, (src, sc, fallback) in enumerate(sources):
        dst = img_dir / f"{i:04d}.png"
        try:
            _upscale_copy(src, dst)
        except Exception as e:
            _log(f"skip {src}: {e}")
            continue
        dst.with_suffix(".txt").write_text(_caption(sc, fallback), encoding="utf-8")
        n += 1
    (out / "meta.json").write_text(json.dumps({"recipe": "sdxl_lora", "images": n, "trigger": TRIGGER,
                                               "built_at": time.strftime("%Y-%m-%d %H:%M")}, indent=2))
    _log(f"sdxl_lora: {n} images -> {out}")
    return n


# ----------------------------------------------------------------------------- coder
def _norm_messages(msgs: list[dict]) -> list[dict] | None:
    """OpenAI transcript -> chat-template-friendly: tool_call arguments as dicts, tool results
    trimmed, no empty assistant turns without tool calls."""
    out = []
    for m in msgs:
        m = dict(m)
        if m.get("role") == "tool":
            m["content"] = str(m.get("content", ""))[:MAX_TOOL_RESULT]
        if m.get("role") == "assistant":
            tcs = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args or "{}")
                    except json.JSONDecodeError:
                        args = {"_raw": args}
                tcs.append({"id": tc.get("id", ""), "type": "function", "function": {"name": fn.get("name", ""), "arguments": args}})
            if tcs:
                m["tool_calls"] = tcs
            else:
                m.pop("tool_calls", None)
            if not m.get("content") and not tcs:
                continue
        out.append(m)
    if len(json.dumps(out)) > MAX_TRANSCRIPT:
        return None
    return out


def build_coder(repo: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    traces = sorted((repo / "data" / "traces" / "coder").glob("*.json")) if (repo / "data" / "traces" / "coder").exists() else []
    passed, failed = [], []
    for p in traces:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = _norm_messages(t.get("messages", []))
        if not msgs or len(msgs) < 3:
            continue
        rec = {"task_id": t.get("task_id"), "job_id": t.get("job_id"), "model": t.get("model"),
               "tools": t.get("tools", []), "messages": msgs}
        (passed if t.get("gate", {}).get("ok") else failed).append(rec)
    n = 0
    with (out / "sft.jsonl").open("w", encoding="utf-8") as f:
        for r in passed:
            f.write(json.dumps({"messages": r["messages"], "tools": r["tools"], "source": r["job_id"]}, ensure_ascii=False) + "\n")
            n += 1
    # DPO pairs: same task, a failed run and a passed run sharing the first user prompt's goal
    by_task: dict[str, dict[str, list]] = defaultdict(lambda: {"p": [], "f": []})
    for r in passed:
        by_task[r["task_id"]]["p"].append(r)
    for r in failed:
        by_task[r["task_id"]]["f"].append(r)
    # A pair is only valid when both runs saw the same prompt (same system + user turn). A retry's
    # prompt carries "Notes from the previous failed attempt", so it differs from the first run;
    # such runs are not paired. Matched pairs come from best-of-N style repeats of one job.
    pairs, skipped = 0, 0
    with (out / "dpo.jsonl").open("w", encoding="utf-8") as f:
        for task, d in by_task.items():
            for good in d["p"]:
                prompt = good["messages"][:2]
                for bad in d["f"]:
                    if bad["messages"][:2] != prompt:
                        skipped += 1
                        continue
                    f.write(json.dumps({"prompt": prompt, "chosen": good["messages"][2:], "rejected": bad["messages"][2:],
                                        "tools": good["tools"]}, ensure_ascii=False) + "\n")
                    pairs += 1
    public = 0
    pub_dir = repo / "data" / "godot4-code"
    if pub_dir.exists():
        with (out / "sft_public.jsonl").open("w", encoding="utf-8") as f:
            for src in sorted(pub_dir.glob("*.jsonl")):
                for line in src.open(encoding="utf-8"):
                    if line.strip():
                        f.write(line if line.endswith("\n") else line + "\n"); public += 1
    (out / "meta.json").write_text(json.dumps({"recipe": "coder", "sft": n, "dpo_pairs": pairs, "dpo_skipped_prompt_mismatch": skipped, "public": public,
                                               "failed_runs": len(failed), "built_at": time.strftime("%Y-%m-%d %H:%M")}, indent=2))
    _log(f"coder: {n} passed runs, {pairs} DPO pairs, {public} public examples -> {out}")
    return n + public


# ----------------------------------------------------------------------------- reviewer
def _resolve(repo: Path, rel: str) -> Path | None:
    """A trace records assets/incoming/<job>/x.png; the file has since moved."""
    tail = Path(rel).parts
    if len(tail) >= 2 and tail[0] == "assets":
        tail = tail[2:]
    for bucket in ("approved", "rejected", "incoming"):
        p = repo / "assets" / bucket / Path(*tail)
        if p.exists():
            return p
    p = repo / rel
    return p if p.exists() else None


def _key(rel: str) -> str:
    parts = Path(rel).parts
    return "/".join(parts[2:]) if len(parts) >= 2 and parts[0] == "assets" else rel


def build_reviewer(repo: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / "img").mkdir(exist_ok=True)
    rdir = repo / "data" / "traces" / "reviewer"
    verdicts = [json.loads(l) for l in (rdir / "verdicts.jsonl").open(encoding="utf-8") if l.strip()] if (rdir / "verdicts.jsonl").exists() else []
    overrides: dict[str, dict] = {}
    if (rdir / "overrides.jsonl").exists():
        for l in (rdir / "overrides.jsonl").open(encoding="utf-8"):
            if l.strip():
                o = json.loads(l); overrides[_key(o["image"])] = o   # last decision wins
    style = (repo / "style" / "style-bible.md").read_text(encoding="utf-8")[:6000]
    ref = _resolve(repo, "style/references/mock-day.png")
    if ref:
        shutil.copy2(ref, out / "img" / "ref-mock-day.png")
    n = 0
    seen: set[str] = set()
    with (out / "reviewer.jsonl").open("w", encoding="utf-8") as f:
        for v in verdicts:
            for img in v.get("images", []):
                k = _key(img)
                src = _resolve(repo, img)
                if not src or k in seen:
                    continue
                seen.add(k)
                label, reason, weight = v["verdict"], v.get("reason", ""), 1
                o = overrides.get(k)
                if o:
                    label, reason, weight = o["owner_verdict"], o.get("reason") or reason, 3
                dst = out / "img" / f"{n:05d}{src.suffix.lower()}"
                shutil.copy2(src, dst)
                rec = {"image": f"img/{dst.name}", "reference": "img/ref-mock-day.png" if ref else None,
                       "spec": v.get("spec", {}), "style": style, "verdict": label, "reason": reason,
                       "owner_labelled": bool(o), "weight": weight}
                for _ in range(weight):
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
        # owner decisions on images the machine never saw (e.g. hand-made references)
        for k, o in overrides.items():
            if k in seen:
                continue
            src = _resolve(repo, o["image"])
            if not src:
                continue
            dst = out / "img" / f"{n:05d}{src.suffix.lower()}"
            shutil.copy2(src, dst)
            rec = {"image": f"img/{dst.name}", "reference": "img/ref-mock-day.png" if ref else None, "spec": {},
                   "style": style, "verdict": o["owner_verdict"], "reason": o.get("reason", ""), "owner_labelled": True, "weight": 3}
            for _ in range(3):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    (out / "meta.json").write_text(json.dumps({"recipe": "reviewer", "images": n, "owner_labelled": len(overrides),
                                               "built_at": time.strftime("%Y-%m-%d %H:%M")}, indent=2))
    _log(f"reviewer: {n} labelled images ({len(overrides)} owner decisions) -> {out}")
    return n


BUILDERS = {"sdxl_lora": build_sdxl_lora, "coder": build_coder, "reviewer": build_reviewer}


def build(repo: Path, recipe: str, out: Path) -> int:
    return BUILDERS[recipe](repo, out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recipe", choices=sorted(BUILDERS))
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out) if a.out else repo / "assets" / "training" / "datasets" / f"{a.recipe}-{time.strftime('%Y%m%d-%H%M')}"
    if not out.is_absolute():
        out = repo / out
    n = build(repo, a.recipe, out)
    print(f"{n} examples in {out}")
    sys.exit(0 if n else 2)
