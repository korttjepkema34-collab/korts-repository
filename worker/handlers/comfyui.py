"""ComfyUI handler for `image` jobs.

Loads an API-format workflow JSON from worker/workflows/<spec.workflow>.json, fills in prompt,
negative prompt, size, seed and reference image nodes, queues it, waits, and copies outputs.

Workflow JSON contract: nodes are found by their `_meta.title`. Required titles:
  "POSITIVE", "NEGATIVE", "LATENT" (EmptyLatentImage), "SEED" (KSampler), "SAVE" (SaveImage).
Optional: "REFERENCE" (LoadImage, for IP-Adapter / img2img).
Export from ComfyUI with "Save (API Format)" after setting those titles.
"""
from __future__ import annotations

import json
import random
import shutil
import time
from pathlib import Path

import requests

from shared.jobs import Job, Sidecar

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"


def _find(wf: dict, title: str) -> str:
    for node_id, node in wf.items():
        if node.get("_meta", {}).get("title") == title:
            return node_id
    raise KeyError(f"workflow has no node titled {title!r}")


def run(job: Job, out_dir: Path, cfg: dict) -> tuple[list[str], str | None]:
    base = cfg["tools"]["comfyui"].rstrip("/")
    spec = job.spec
    wf_path = WORKFLOWS / f"{spec.get('workflow', 'default')}.json"
    wf = json.loads(wf_path.read_text())

    prompt = spec["prompt"]
    if job.notes:
        prompt += f". Reviewer notes from earlier attempt: {job.notes}"
    wf[_find(wf, "POSITIVE")]["inputs"]["text"] = prompt
    wf[_find(wf, "NEGATIVE")]["inputs"]["text"] = spec.get("negative_prompt", "")
    latent = wf[_find(wf, "LATENT")]["inputs"]
    latent["width"], latent["height"] = spec.get("width", 1024), spec.get("height", 1024)
    latent["batch_size"] = spec.get("count", 1)
    seed = spec.get("seed") or random.randint(0, 2**31)
    wf[_find(wf, "SEED")]["inputs"]["seed"] = seed
    wf[_find(wf, "SAVE")]["inputs"]["filename_prefix"] = job.id
    refs = spec.get("references") or []
    if refs:
        try:
            ref_node = _find(wf, "REFERENCE")
            # Upload the first reference so ComfyUI can load it by name.
            ref_path = Path(cfg["repo_root"]) / refs[0]
            with ref_path.open("rb") as f:
                requests.post(f"{base}/upload/image", files={"image": f}, timeout=60).raise_for_status()
            wf[ref_node]["inputs"]["image"] = ref_path.name
        except KeyError:
            pass  # workflow has no reference node; fine

    resp = requests.post(f"{base}/prompt", json={"prompt": wf}, timeout=60)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    deadline = time.time() + spec.get("timeout_s", 900)
    while time.time() < deadline:
        hist = requests.get(f"{base}/history/{prompt_id}", timeout=30).json()
        if prompt_id in hist:
            break
        time.sleep(2)
    else:
        raise TimeoutError("ComfyUI did not finish in time")

    outputs: list[str] = []
    comfy_out = Path(cfg["tools"].get("comfyui_output_dir", "")) if cfg["tools"].get("comfyui_output_dir") else None
    for node in hist[prompt_id]["outputs"].values():
        for img in node.get("images", []):
            if comfy_out:
                src = comfy_out / img.get("subfolder", "") / img["filename"]
                dst = out_dir / img["filename"]
                shutil.copy2(src, dst)
            else:
                r = requests.get(f"{base}/view", params={"filename": img["filename"],
                                 "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")}, timeout=60)
                r.raise_for_status()
                dst = out_dir / img["filename"]
                dst.write_bytes(r.content)
            outputs.append(str(dst))

    pp = spec.get("postprocess") or {"palette": True, "downscale": spec.get("downscale", 4), "transparent_bg": spec.get("transparent_bg", True)}
    if pp:
        try:
            from postprocess import process
            outputs = [str(process(Path(o), Path(cfg["repo_root"]), pp)) for o in outputs]
            if pp.get("normal_map"):
                outputs += [o.replace(".px.png", ".px.n.png") for o in outputs]
        except Exception as e:
            raise RuntimeError(f"postprocess failed: {e}") from e

    sc = out_dir / f"{job.id}.json"
    Sidecar(generator="comfyui", model=spec.get("model_label", wf_path.stem),
            licence=spec.get("licence", "see docs/04-models.md"), prompt=prompt,
            negative_prompt=spec.get("negative_prompt"), seed=seed, job_id=job.id,
            extra={"workflow": wf_path.name, "references": refs}).write(sc)
    return outputs, str(sc)


def unload(cfg: dict) -> None:
    base = cfg["tools"]["comfyui"].rstrip("/")
    try:
        requests.post(f"{base}/free", json={"unload_models": True, "free_memory": True}, timeout=30)
    except requests.RequestException:
        pass
