"""Recipe: SDXL style LoRA with kohya sd-scripts. Runs on the GPU box (12 GB is enough).

    python training/train_sdxl_lora.py --repo C:/studio --dataset assets/training/datasets/sdxl_lora-... --out assets/training/models/sdxl_lora-...
        [--tools '{"kohya_dir": "...", "sdxl_checkpoint": "..."}'] [--steps 1800] [--dim 16]

What it does: writes a kohya dataset .toml for <dataset>/img (image + same-name .txt caption),
then runs sdxl_train_network.py with settings that fit 12 GB: batch 1, cached latents and
text-encoder outputs, U-Net only, 8-bit AdamW, gradient checkpointing, bf16.
Output: <out>/rrstyle.safetensors + manifest.json. Activate with scripts/activate_model.py sdxl_lora.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tools", default="{}", help="JSON of worker cfg.tools")
    ap.add_argument("--base-model", default=None, help="SDXL checkpoint path (overrides tools.sdxl_checkpoint)")
    ap.add_argument("--steps", type=int, default=int(os.environ.get("LORA_STEPS", "1800")))
    ap.add_argument("--dim", type=int, default=16)
    ap.add_argument("--lr", default="1e-4")
    ap.add_argument("--name", default="rrstyle")
    a = ap.parse_args()
    tools = json.loads(a.tools or "{}")
    repo = Path(a.repo)
    ds = repo / a.dataset
    out = repo / a.out
    out.mkdir(parents=True, exist_ok=True)
    kohya = Path(tools.get("kohya_dir") or repo / "training" / "sd-scripts")
    ckpt = a.base_model or tools.get("sdxl_checkpoint")
    if not ckpt or not Path(ckpt).exists():
        sys.exit(f"SDXL checkpoint not found: {ckpt!r}. Set tools.sdxl_checkpoint in worker/config.yaml")
    if not (kohya / "sdxl_train_network.py").exists():
        sys.exit(f"kohya sd-scripts not found at {kohya}. Run training/setup.ps1")
    images = sorted((ds / "img").glob("*.png"))
    if not images:
        sys.exit(f"no images in {ds / 'img'}")
    # repeats so that one epoch is ~200 samples, epochs so that total steps ~= --steps
    repeats = max(1, round(200 / len(images)))
    epochs = max(1, round(a.steps / (len(images) * repeats)))
    toml = f"""[general]
enable_bucket = true
shuffle_caption = true
keep_tokens = 1
caption_extension = ".txt"

[[datasets]]
resolution = 1024
batch_size = 1
min_bucket_reso = 512
max_bucket_reso = 1024

  [[datasets.subsets]]
  image_dir = "{(ds / 'img').as_posix()}"
  num_repeats = {repeats}
"""
    (out / "dataset.toml").write_text(toml)
    cmd = [sys.executable, str(kohya / "sdxl_train_network.py"),
           "--pretrained_model_name_or_path", str(ckpt),
           "--dataset_config", str(out / "dataset.toml"),
           "--output_dir", str(out), "--output_name", a.name, "--save_model_as", "safetensors",
           "--network_module", "networks.lora", "--network_dim", str(a.dim), "--network_alpha", str(max(1, a.dim // 2)),
           "--network_train_unet_only",
           "--learning_rate", a.lr, "--lr_scheduler", "cosine", "--lr_warmup_steps", "50",
           "--optimizer_type", "AdamW8bit", "--max_train_epochs", str(epochs),
           "--mixed_precision", "bf16", "--save_precision", "fp16", "--no_half_vae",
           "--cache_latents", "--cache_latents_to_disk", "--cache_text_encoder_outputs", "--cache_text_encoder_outputs_to_disk",
           "--gradient_checkpointing", "--sdpa", "--min_snr_gamma", "5",
           "--max_data_loader_n_workers", "2", "--persistent_data_loader_workers",
           "--save_every_n_epochs", str(max(1, epochs // 3)), "--seed", "42",
           "--logging_dir", str(out / "logs")]
    print(" ".join(cmd), flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=str(kohya)).returncode
    if rc != 0:
        sys.exit(rc)
    final = out / f"{a.name}.safetensors"
    if not final.exists():
        sys.exit("training ended without a final safetensors file")
    (out / "manifest.json").write_text(json.dumps({
        "recipe": "sdxl_lora", "files": [final.name], "base_model": Path(ckpt).name, "licence": "CreativeML OpenRAIL++ (SDXL)",
        "trigger": "rrstyle", "images": len(images), "repeats": repeats, "epochs": epochs, "dim": a.dim,
        "minutes": round((time.time() - t0) / 60, 1), "metrics": {}}, indent=2))
    print("done:", final)


if __name__ == "__main__":
    main()
