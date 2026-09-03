"""Recipe: QLoRA fine-tune of a small dense coder on the studio's gate-passed runs + public Godot 4
code, with an optional DPO stage on pass/fail pairs. Unsloth + TRL. Fits a 12 GB card.

    python training/train_coder.py --repo C:/studio --dataset assets/training/datasets/coder-... --out assets/training/models/coder-...
        [--base-model unsloth/Qwen2.5-Coder-7B-Instruct] [--max-seq 6144] [--epochs 2]

Output: <out>/lora/ (adapter), <out>/merged/ (16-bit safetensors, importable by `ollama create`),
manifest.json. Activate on the server with scripts/activate_model.py coder.

Base model notes: Qwen2.5-Coder-7B-Instruct is the known-good default (Apache 2.0, tool calling,
GGUF/Ollama friendly). Check docs/04-models.md for a newer small dense coder before a big run;
anything Unsloth lists as supported with a chat template that handles `tools` works here.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tools", default="{}")
    ap.add_argument("--base-model", default=os.environ.get("CODER_BASE_MODEL", "unsloth/Qwen2.5-Coder-7B-Instruct"))
    ap.add_argument("--max-seq", type=int, default=6144)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--public-cap", type=int, default=3000, help="max public examples mixed in")
    ap.add_argument("--no-dpo", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo); ds = repo / a.dataset; out = repo / a.out
    out.mkdir(parents=True, exist_ok=True)

    from unsloth import FastLanguageModel  # noqa: E402  (import here so --help works without torch)
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    sft = load_jsonl(ds / "sft.jsonl")
    public = load_jsonl(ds / "sft_public.jsonl")[: a.public_cap]
    if not sft and not public:
        sys.exit("empty dataset")
    print(f"studio examples: {len(sft)}  public examples: {len(public)}", flush=True)

    model, tok = FastLanguageModel.from_pretrained(a.base_model, max_seq_length=a.max_seq, load_in_4bit=True, dtype=None)
    model = FastLanguageModel.get_peft_model(
        model, r=a.rank, lora_alpha=a.rank, lora_dropout=0.0, bias="none",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=42)

    def render(ex: dict) -> dict:
        kwargs = {"tools": ex["tools"]} if ex.get("tools") else {}
        text = tok.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False, **kwargs)
        return {"text": text}

    rows = [render(e) for e in sft * 2 + public]  # studio runs weighted 2x vs public
    train_ds = Dataset.from_list(rows).shuffle(seed=42)
    t0 = time.time()
    trainer = SFTTrainer(
        model=model, tokenizer=tok, train_dataset=train_ds, dataset_text_field="text",
        args=SFTConfig(output_dir=str(out / "ckpt"), per_device_train_batch_size=1, gradient_accumulation_steps=8,
                       num_train_epochs=a.epochs, learning_rate=a.lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
                       logging_steps=10, save_strategy="no", bf16=True, optim="adamw_8bit", weight_decay=0.01,
                       max_seq_length=a.max_seq, packing=False, seed=42, report_to="none"))
    stats = trainer.train()
    metrics = {"sft_loss": stats.training_loss, "sft_examples": len(rows)}

    dpo = load_jsonl(ds / "dpo.jsonl")
    if dpo and len(dpo) >= 20 and not a.no_dpo:
        from trl import DPOConfig, DPOTrainer
        def render_pair(ex: dict) -> dict:
            kw = {"tools": ex["tools"]} if ex.get("tools") else {}
            prompt = tok.apply_chat_template(ex["prompt"], tokenize=False, add_generation_prompt=True, **kw)
            full_c = tok.apply_chat_template(ex["prompt"] + ex["chosen"], tokenize=False, **kw)
            full_r = tok.apply_chat_template(ex["prompt"] + ex["rejected"], tokenize=False, **kw)
            return {"prompt": prompt, "chosen": full_c[len(prompt):], "rejected": full_r[len(prompt):]}
        pairs = Dataset.from_list([render_pair(e) for e in dpo])
        dtrainer = DPOTrainer(model=model, ref_model=None, tokenizer=tok, train_dataset=pairs, beta=0.1,
                              args=DPOConfig(output_dir=str(out / "ckpt-dpo"), per_device_train_batch_size=1,
                                             gradient_accumulation_steps=8, num_train_epochs=1, learning_rate=5e-6,
                                             max_length=a.max_seq, max_prompt_length=a.max_seq // 2, bf16=True,
                                             logging_steps=5, save_strategy="no", report_to="none", seed=42))
        dstats = dtrainer.train()
        metrics["dpo_loss"] = dstats.training_loss; metrics["dpo_pairs"] = len(dpo)

    model.save_pretrained(str(out / "lora")); tok.save_pretrained(str(out / "lora"))
    model.save_pretrained_merged(str(out / "merged"), tok, save_method="merged_16bit")
    files = ["merged", "lora"]
    try:  # optional: direct GGUF (needs llama.cpp build tools; fine on WSL, flaky on Windows)
        if os.environ.get("EXPORT_GGUF") == "1":
            model.save_pretrained_gguf(str(out / "gguf"), tok, quantization_method="q4_k_m"); files.append("gguf")
    except Exception as e:
        print("gguf export skipped:", e)
    (out / "manifest.json").write_text(json.dumps({
        "recipe": "coder", "files": files, "base_model": a.base_model, "licence": "Apache-2.0 (Qwen)",
        "minutes": round((time.time() - t0) / 60, 1), "metrics": metrics, "max_seq": a.max_seq}, indent=2))
    print("done", metrics)


if __name__ == "__main__":
    main()
