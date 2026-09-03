# training/

Everything that makes the studio's models better at *this* game. Full story: `docs/15-training.md`.
Step-by-step for the owner: `docs/16-when-you-get-home.md`.

| File | Runs on | What |
|---|---|---|
| `build_datasets.py` | server | traces + approved assets -> datasets in `assets/training/datasets/` |
| `collect_godot4_code.py` | server | public MIT Godot 4 repos -> `data/godot4-code/*.jsonl` (Godot 3 filtered out) |
| `train_sdxl_lora.py` | gpu | kohya SDXL LoRA on approved sprites; trigger word `rrstyle` |
| `train_coder.py` | gpu | Unsloth QLoRA (+DPO) of a 7B coder on gate-passed runs + public code |
| `train_reviewer.py` | gpu | Unsloth QLoRA of a small VL model on the owner's verdicts |
| `serve_reviewer.py` | gpu (server later) | OpenAI-compatible endpoint for the fine-tuned reviewer |
| `eval_coder.py` | server | gate pass rate on `eval/heldout_tasks.json`; run before and after |
| `setup.ps1` | gpu | creates the training venv + kohya checkout |

The worker runs the three `train_*.py` recipes as `train` jobs (`worker/handlers/train.py`).
`scripts/enqueue_train.py <recipe>` queues one by hand; `AUTO_TRAIN=1` lets the orchestrator
queue them itself when enough new data exists. `scripts/activate_model.py <recipe>` puts a
finished model into service. Nothing is activated automatically.
