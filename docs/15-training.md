> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 15 - Training the studio's own models

The studio produces labelled data as a side effect of working. This document explains what is
captured, what each fine-tune is for, how the pieces fit the two-machine layout, and the rules
that keep a bad fine-tune from making things worse. Owner's step-by-step: `docs/16-when-you-get-home.md`.

## Why

Prompts describe your conventions; a fine-tune *is* your conventions. Three places it pays:

| Target | Failure it fixes | Data it needs | Where the data comes from |
|---|---|---|---|
| **SDXL style LoRA** | assets drift from the palette, proportions and register (the main failure mode of multi-worker art) | 30-50 approved images to start | `assets/approved/` + `style/references/` |
| **Coder fine-tune** (7B dense, QLoRA) | Godot 3 syntax, wrong API names, ignoring the conventions file | 150+ gate-passed runs, plus public Godot 4 code | `data/traces/coder/` + `training/collect_godot4_code.py` |
| **Reviewer fine-tune** (small VL model, QLoRA) | reviewer lets drift through / rejects good work; it does not know *your* taste | 100+ of your own verdicts | `scripts/override.py session` |

Not worth it: the orchestrator. Planning quality tracks model size; retrieval and prompts do more.

## Cheaper than training, done first

1. **Retrieval.** `scripts/fetch_godot_docs.py` + `scripts/build_rag_index.py` give the coder a
   `search_docs` tool over the Godot 4 class reference, the conventions file and the project's
   own code, and the six most relevant chunks are pasted into every coder prompt. Fixes most
   "wrong API" errors for zero GPU time.
2. **Traces.** Always on. `server/orchestrator/traces.py` records every coder transcript with
   its gate result and every reviewer verdict. Costs nothing; every recipe below depends on it.

## The pieces

```
SERVER (CPU)                                        GAMING PC (GPU)
traces.py  -> data/traces/                          worker/handlers/train.py
override.py (you) -> data/traces/reviewer/overrides   runs training/train_<recipe>.py in training/.venv
training.py: enough new data? build dataset  ---->  reads assets/training/datasets/<name>  (Syncthing)
             assets/training/datasets/<name>        writes assets/training/models/<name>   (Syncthing)
on_trained(): record in data/training/state.json <-- result
activate_model.py (you): ollama create / LoraLoader / serve  -- deliberate, never automatic
eval_coder.py (you or daily): pass rate on 8 held-out tasks
```

- A `train` job is an ordinary queue job (`kind: train`, `role: trainer`) with
  `spec.recipe`, `spec.dataset`, `spec.stale_after_s` (hours, not the usual 90 minutes; the worker's
  own `timeout_s` is set 10 minutes shorter so both sides agree). One at a time, and last in the
  worker's `kinds` list so queued asset jobs go first (the queue is FIFO per kind; `Job.priority`
  is not used by anything yet).
- Datasets are built **on the server** (CPU, stdlib + Pillow) into `assets/training/datasets/`,
  which Syncthing already carries to the GPU box. Models come back the same way. No new sync
  folder, no new port.
- Training runs in its own venv (`training/setup.ps1`) because torch, Unsloth and kohya are heavy
  and version-sensitive. The worker only shells out to it.
- `AUTO_TRAIN=1` lets the daily pass queue a job when a recipe's data has crossed its threshold
  *and* grown enough since the last run (env vars in `server/.env.example`). Off by default.

## Recipes

### sdxl_lora (kohya sd-scripts, ~45-90 min)

`training/build_datasets.py sdxl_lora` copies every approved image and the mock frames,
nearest-neighbour upscales to 1024, flattens transparency onto ash, and writes a caption from
the sidecar prompt prefixed with the trigger word `rrstyle`. `train_sdxl_lora.py` trains a rank-16
U-Net-only LoRA at 1024 with cached latents, 8-bit AdamW and bf16: about 9-10 GB of VRAM.
Activation inserts a `LoraLoader` (title `STYLE_LORA`) into `worker/workflows/default.json` and
adds `rrstyle` to the style bible's positive suffix. Retrain as `approved/` grows.

### coder (Unsloth QLoRA + optional DPO, ~2-6 h)

SFT on gate-passed transcripts (full tool-call trajectories rendered with the model's chat
template, tool results trimmed to 3500 chars, studio runs weighted 2x against public code) then,
when 20+ pairs exist, one DPO epoch on passed-vs-failed runs of the same task. The gate is the
labeller: pass/fail comes free from the headless Godot check and tests. Output is a merged
16-bit safetensors folder that `ollama create --quantize q4_K_M` imports on the server (no
llama.cpp build needed). The result is a dense 7B, so on the server CPU it runs at roughly
6-8 tok/s: fine unattended, or serve it from the GPU box via `CODER_BASE_URL` when idle.

Default base: `unsloth/Qwen2.5-Coder-7B-Instruct` (Apache 2.0, tool calling, Ollama-friendly).
Check for a newer small dense coder before a long run; anything Unsloth supports with a
tools-aware chat template works with the same script.

### reviewer (Unsloth vision QLoRA, ~1-3 h)

One candidate image, the job spec and the style bible in; `{"verdict","reason"}` out, exactly
what `reviewer.py` asks for. Your decisions weigh 3x the machine's. Served by
`training/serve_reviewer.py` (OpenAI-compatible, one request at a time) and pointed at with
`REVIEWER_BASE_URL`. Base: `unsloth/Qwen2.5-VL-3B-Instruct`; try `Qwen3-VL-4B-Instruct` if your
Unsloth lists it.

## Rules that keep it safe

1. **Nothing activates itself.** A finished model is recorded in `data/training/state.json`
   and the decision log; `scripts/activate_model.py` is a human step with a rollback.
2. **Only gate-passed and owner-approved data trains.** Failed runs appear only as the
   *rejected* side of DPO pairs. Training on your own mistakes entrenches them.
3. **Measure before switching the coder.** `training/eval_coder.py` runs eight held-out tasks
   (`training/eval/heldout_tasks.json`) through the real coder loop in a throwaway clone and
   appends a row to `reports/eval-coder.md`. Run it on the current model first so there is a
   baseline. A fine-tune that does not beat the baseline is not activated.
4. **Public code is filtered by engine version.** `collect_godot4_code.py` keeps only projects
   whose `project.godot` declares a 4.x feature set and drops any file with Godot 3 tokens.
5. **One training job at a time, after asset jobs.** It shares the 12 GB with SDXL.
6. **Escalation runs are gold.** The slow big model's passed runs on deferred tasks are the best
   coder examples you will get; they are traced like every other run and train the fast model
   (slow teacher, fast student).

## Windows vs WSL2 for training

kohya and Unsloth both run on native Windows today (`training/setup.ps1`; Unsloth needs the
`triton-windows` wheel). If `import unsloth` keeps failing, install Ubuntu in WSL2 on the gaming
PC, create the venv there, and set `tools.training_cmd` / `tools.training_repo_root` in
`worker/config.yaml` so the worker runs the recipes through `wsl -e`. The scripts only ever see
`--repo` plus relative paths, so both layouts work unchanged.

## Once the server has its 12 GB card

Move `serve_reviewer.py` and the retrieval index there permanently; the fine-tuned reviewer
becomes always-resident. Coder fine-tunes can also run there overnight, leaving the 3080 Ti to
SDXL. Add `train` to the server worker's `kinds` and the queue does the rest.

