"""Recipe: QLoRA fine-tune of a small vision-language model on the owner's approve/reject
decisions, so the reviewer learns this project's taste. Unsloth vision. Fits 12 GB for 3-4B.

    python training/train_reviewer.py --repo C:/studio --dataset assets/training/datasets/reviewer-... --out assets/training/models/reviewer-...
        [--base-model unsloth/Qwen2.5-VL-3B-Instruct]

Each example: candidate image (+ the mock-day reference), job spec, style bible excerpt ->
{"verdict": "...", "reason": "..."} exactly as server/orchestrator/reviewer.py expects.
Output: <out>/lora + <out>/merged, served by training/serve_reviewer.py (OpenAI-compatible) and
pointed at with REVIEWER_BASE_URL in server/.env. See scripts/activate_model.py reviewer.

Base model: Qwen2.5-VL-3B-Instruct is the safe default. Try unsloth/Qwen3-VL-4B-Instruct if your
Unsloth version lists it; same script.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tools", default="{}")
    ap.add_argument("--base-model", default=os.environ.get("REVIEWER_BASE_MODEL", "unsloth/Qwen2.5-VL-3B-Instruct"))
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--with-reference", action="store_true", help="also feed the mock-day reference image")
    a = ap.parse_args()
    repo = Path(a.repo); ds = repo / a.dataset; out = repo / a.out
    out.mkdir(parents=True, exist_ok=True)

    from PIL import Image
    from unsloth import FastVisionModel, is_bf16_supported
    from unsloth.trainer import UnslothVisionDataCollator
    from trl import SFTConfig, SFTTrainer

    rows = [json.loads(l) for l in (ds / "reviewer.jsonl").open(encoding="utf-8") if l.strip()]
    if not rows:
        sys.exit("empty dataset")
    system = (repo / "agents" / "reviewer.md").read_text(encoding="utf-8")

    def convert(r: dict) -> dict:
        content = [{"type": "text", "text": "Job spec:\n" + json.dumps(r.get("spec", {}), indent=2)[:2000]
                    + "\n\nStyle bible:\n" + r.get("style", "")[:4000]
                    + "\n\nFirst image is the candidate" + ("; the second is a style reference." if a.with_reference and r.get("reference") else ".")
                    + " Respond with JSON {\"verdict\": \"approved\"|\"rejected\", \"reason\": \"...\"}."},
                   {"type": "image", "image": Image.open(ds / r["image"]).convert("RGB")}]
        if a.with_reference and r.get("reference"):
            content.append({"type": "image", "image": Image.open(ds / r["reference"]).convert("RGB")})
        answer = json.dumps({"verdict": r["verdict"], "reason": r.get("reason", "")[:300]})
        return {"messages": [{"role": "system", "content": [{"type": "text", "text": system[:3000]}]},
                             {"role": "user", "content": content},
                             {"role": "assistant", "content": [{"type": "text", "text": answer}]}]}

    data = [convert(r) for r in rows]
    model, proc = FastVisionModel.from_pretrained(a.base_model, load_in_4bit=True, use_gradient_checkpointing="unsloth")
    model = FastVisionModel.get_peft_model(model, finetune_vision_layers=False, finetune_language_layers=True,
                                           finetune_attention_modules=True, finetune_mlp_modules=True,
                                           r=a.rank, lora_alpha=a.rank, lora_dropout=0.0, bias="none", random_state=42)
    FastVisionModel.for_training(model)
    t0 = time.time()
    trainer = SFTTrainer(
        model=model, tokenizer=proc, data_collator=UnslothVisionDataCollator(model, proc), train_dataset=data,
        args=SFTConfig(output_dir=str(out / "ckpt"), per_device_train_batch_size=1, gradient_accumulation_steps=8,
                       num_train_epochs=a.epochs, learning_rate=a.lr, warmup_ratio=0.05, lr_scheduler_type="cosine",
                       logging_steps=5, save_strategy="no", optim="adamw_8bit", weight_decay=0.01,
                       fp16=not is_bf16_supported(), bf16=is_bf16_supported(), report_to="none", seed=42,
                       remove_unused_columns=False, dataset_text_field="", dataset_kwargs={"skip_prepare_dataset": True},
                       max_seq_length=4096))
    stats = trainer.train()
    model.save_pretrained(str(out / "lora")); proc.save_pretrained(str(out / "lora"))
    model.save_pretrained_merged(str(out / "merged"), proc, save_method="merged_16bit")
    (out / "manifest.json").write_text(json.dumps({
        "recipe": "reviewer", "files": ["merged", "lora"], "base_model": a.base_model, "licence": "Apache-2.0 (Qwen)",
        "minutes": round((time.time() - t0) / 60, 1), "metrics": {"loss": stats.training_loss, "examples": len(data)}}, indent=2))
    print("done")


if __name__ == "__main__":
    main()
