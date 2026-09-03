#!/usr/bin/env python3
"""Put a finished fine-tune into service. Deliberate step; nothing activates itself.

    python scripts/activate_model.py sdxl_lora  [--model-dir assets/training/models/sdxl_lora-...] [--strength 0.8]
        On the GPU box. Copies rrstyle.safetensors into ComfyUI's loras folder (worker/config.yaml
        tools.comfyui_loras_dir or --loras-dir) and inserts a LoraLoader into worker/workflows/default.json.
        The style bible's positive prompt suffix gets the trigger word `rrstyle`.

    python scripts/activate_model.py coder [--name reapers-coder] [--quantize q4_K_M]
        On the server. `ollama create` from the merged safetensors, then tells you the .env line.

    python scripts/activate_model.py reviewer
        Prints the serve command for the GPU box and the .env lines. (Serving is a long-running
        process; see docs/15-training.md.)

    python scripts/activate_model.py rollback <recipe>
        Undo: restores the previous workflow / prints the previous .env values.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "assets" / "training" / "models"
WORKFLOW = REPO / "worker" / "workflows" / "default.json"
STYLE = REPO / "style" / "style-bible.md"


def latest(recipe: str, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit); p = p if p.is_absolute() else REPO / p
        if not (p / "manifest.json").exists():
            sys.exit(f"no manifest.json in {p}")
        return p
    cands = sorted([d for d in MODELS.glob(f"{recipe}-*") if (d / "manifest.json").exists()])
    if not cands:
        sys.exit(f"no finished {recipe} model under {MODELS}")
    return cands[-1]


def activate_sdxl(a) -> None:
    d = latest("sdxl_lora", a.model_dir)
    m = json.loads((d / "manifest.json").read_text())
    lora = d / m["files"][0]
    cfg = {}
    cfgp = REPO / "worker" / "config.yaml"
    if cfgp.exists():
        import yaml
        cfg = yaml.safe_load(cfgp.read_text()) or {}
    loras_dir = a.loras_dir or cfg.get("tools", {}).get("comfyui_loras_dir")
    if not loras_dir:
        sys.exit("where is ComfyUI's models/loras folder? pass --loras-dir or set tools.comfyui_loras_dir in worker/config.yaml")
    dst = Path(loras_dir) / f"rrstyle-{d.name}.safetensors"
    shutil.copy2(lora, dst)
    print("copied", lora.name, "->", dst)
    wf = json.loads(WORKFLOW.read_text())
    if not WORKFLOW.with_suffix(".json.bak").exists():
        shutil.copy2(WORKFLOW, WORKFLOW.with_suffix(".json.bak"))  # keep the pre-LoRA original for rollback
    ckpt_id = next(k for k, v in wf.items() if v.get("class_type") == "CheckpointLoaderSimple")
    lora_id = next((k for k, v in wf.items() if v.get("_meta", {}).get("title") == "STYLE_LORA"), None)
    if lora_id is None:
        lora_id = "lora_style"
        for node in wf.values():  # re-point every consumer of the checkpoint's MODEL/CLIP outputs
            for key, val in node.get("inputs", {}).items():
                if isinstance(val, list) and len(val) == 2 and val[0] == ckpt_id and val[1] in (0, 1):
                    node["inputs"][key] = [lora_id, val[1]]
        wf[lora_id] = {"class_type": "LoraLoader", "_meta": {"title": "STYLE_LORA"},
                       "inputs": {"lora_name": dst.name, "strength_model": a.strength, "strength_clip": a.strength,
                                  "model": [ckpt_id, 0], "clip": [ckpt_id, 1]}}
    else:
        wf[lora_id]["inputs"].update(lora_name=dst.name, strength_model=a.strength, strength_clip=a.strength)
    WORKFLOW.write_text(json.dumps(wf, indent=2))
    print("workflow updated:", WORKFLOW.relative_to(REPO), "(backup .bak)")
    s = STYLE.read_text(encoding="utf-8")
    if "rrstyle" not in s:
        s2 = re.sub(r"(- Positive suffix: `)", r"\1rrstyle, ", s, count=1)
        if s2 != s:
            STYLE.write_text(s2, encoding="utf-8"); print("style bible: added trigger word 'rrstyle' to the positive suffix")
    print("\nDone. Next image job uses the LoRA. Commit worker/workflows/default.json and style/style-bible.md.\n"
          "Judge the first 10 outputs yourself (scripts/override.py session). If they are worse: python scripts/activate_model.py rollback sdxl_lora")


def activate_coder(a) -> None:
    d = latest("coder", a.model_dir)
    merged = d / "merged"
    gguf = next(iter((d / "gguf").glob("*.gguf")), None) if (d / "gguf").exists() else None
    src = gguf or merged
    if not src.exists():
        sys.exit(f"no merged/ or gguf/ in {d}")
    m = json.loads((d / "manifest.json").read_text())
    modelfile = d / "Modelfile"
    lines = [f"FROM {src}", "PARAMETER temperature 0.1", "PARAMETER num_ctx 16384"]
    if gguf:  # a GGUF has no chat template of its own; borrow the base model's from Ollama
        base_tag = a.template_from or "qwen2.5-coder:7b"
        p = subprocess.run(["ollama", "show", "--modelfile", base_tag], capture_output=True, text=True)
        if p.returncode == 0:
            keep = [l for l in p.stdout.splitlines() if not l.startswith(("FROM", "#"))]
            lines += keep
        else:
            print(f"warning: could not read template from {base_tag}; pull it first for tool calling to work")
    modelfile.write_text("\n".join(lines) + "\n")
    cmd = ["ollama", "create", a.name, "-f", str(modelfile)] + (["--quantize", a.quantize] if not gguf else [])
    print(" ".join(cmd)); rc = subprocess.run(cmd).returncode
    if rc != 0:
        sys.exit(rc)
    print(f"\nModel '{a.name}' is in Ollama (base {m.get('base_model')}).\n"
          f"1. Measure it first:  cd server && .venv\\Scripts\\python ..\\training\\eval_coder.py --model {a.name}\n"
          f"2. If it beats the current CODER_MODEL row in reports/eval-coder.md, set in server/.env:\n"
          f"     CODER_MODEL={a.name}\n   and restart the orchestrator. Rollback = put the old value back.")


def activate_reviewer(a) -> None:
    d = latest("reviewer", a.model_dir)
    print(f"Fine-tuned reviewer: {d}\n\nOn the GPU box (training venv):\n"
          f"  training\\.venv\\Scripts\\python training\\serve_reviewer.py --model {d / 'merged'} --port 8191\n"
          f"  (leave it running; add it to Task Scheduler like the worker once you trust it)\n\n"
          f"On the server, in server/.env:\n  REVIEWER_BASE_URL=http://<gpu tailscale ip>:8191/v1\n  REVIEWER_MODEL=reapers-reviewer\n"
          f"Restart the orchestrator. Rollback = remove REVIEWER_BASE_URL and restore REVIEWER_MODEL=qwen3-vl:8b.\n"
          f"Check it against your own judgement for a week: scripts/override.py session")


def rollback(a) -> None:
    if a.recipe == "sdxl_lora":
        bak = WORKFLOW.with_suffix(".json.bak")
        if bak.exists():
            shutil.copy2(bak, WORKFLOW); print("restored", WORKFLOW.relative_to(REPO))
        s = STYLE.read_text(encoding="utf-8").replace("`rrstyle, ", "`", 1)
        STYLE.write_text(s, encoding="utf-8"); print("removed trigger word from the style bible")
    else:
        print("edit server/.env: restore the previous CODER_MODEL / REVIEWER_MODEL and remove *_BASE_URL, then restart the orchestrator")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sdxl_lora"); s.add_argument("--model-dir"); s.add_argument("--loras-dir"); s.add_argument("--strength", type=float, default=0.8)
    c = sub.add_parser("coder"); c.add_argument("--model-dir"); c.add_argument("--name", default="reapers-coder"); c.add_argument("--quantize", default="q4_K_M"); c.add_argument("--template-from")
    r = sub.add_parser("reviewer"); r.add_argument("--model-dir")
    b = sub.add_parser("rollback"); b.add_argument("recipe", choices=["sdxl_lora", "coder", "reviewer"])
    a = ap.parse_args()
    {"sdxl_lora": activate_sdxl, "coder": activate_coder, "reviewer": activate_reviewer, "rollback": rollback}[a.cmd](a)


if __name__ == "__main__":
    main()
