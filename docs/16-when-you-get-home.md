> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 16 - When you get home: making the studio learn

Everything in this branch is wired and tested against synthetic data. What is left is the part
only you can do on the real machines: install two things, run three commands, and spend ten
minutes a week grading pictures. Ordered by payoff. Tick as you go.

## 0. Ten-second summary

- The studio now **records everything** it does (traces) with a pass/fail label. Free. Already on.
- The coder now **looks things up** in the Godot 4 docs before writing code. Needs one download.
- When enough data exists, the GPU box can **train** a style LoRA, a coder, and a reviewer,
  from your own approved work. You start those with one command, or set `AUTO_TRAIN=1`.
- You **grade** the reviewer's calls with `scripts/override.py session` when you feel like it.
  That is the only human labour in the whole loop.

## How to run the scripts

Every `python scripts\...` and `training\...` command in this file is run **on the server from
the repo root** through `studio.ps1`, which uses the orchestrator's venv and loads `server\.env`:

```powershell
cd C:\studio
.\studio.ps1 scripts\override.py stats
```

On the gaming PC the same scripts run with `worker\.venv\Scripts\python.exe` (the two that run
there are `scripts\activate_model.py sdxl_lora` and `training\serve_reviewer.py`; the latter
uses `training\.venv`).

## 1. Server (30 minutes, do first)

- [ ] Pull this branch on the server and reinstall the orchestrator deps (Pillow was added):
      ```powershell
      cd C:\studio ; git pull
      cd server ; .\.venv\Scripts\pip install -r orchestrator\requirements.txt
      ```
- [ ] Copy the new lines from `server/.env.example` into `server/.env`
      (`AUTO_TRAIN=0`, the thresholds, `EMBED_MODEL`, empty `CODER_BASE_URL` / `REVIEWER_BASE_URL`).
- [ ] Give the coder its reference library (needs internet, ~40 MB; then a few minutes of CPU):
      ```powershell
      ollama pull nomic-embed-text
      .\studio.ps1 scripts\fetch_godot_docs.py
      .\studio.ps1 scripts\build_rag_index.py
      ```
      Test it: `.\studio.ps1 scripts\build_rag_index.py --query "connect a signal in Godot 4"` prints doc chunks.
- [ ] Get the public Godot 4 code for the coder fine-tune (needs git + internet; 5 minutes):
      `.\studio.ps1 training\collect_godot4_code.py`
- [ ] Baseline the current coder so later fine-tunes have something to beat (runs 8 small
      tasks through the real coder loop; an hour or two on CPU, unattended):
      `.\studio.ps1 training\eval_coder.py --model qwen3.6:35b-a3b-coding`
      Result row lands in `reports\eval-coder.md`.
- [ ] Restart the orchestrator. Look for `search_docs` in coder logs and files appearing under
      `data\traces\` after the first coder run and first review.

## 2. Gaming PC (45 minutes plus downloads)

- [ ] Pull the branch. Add `train` to `kinds` in `worker\config.yaml` and fill the new `tools`
      entries: `training_python`, `kohya_dir`, `sdxl_checkpoint` (the same checkpoint file
      ComfyUI uses), and `comfyui_loras_dir` (ComfyUI's `models\loras`).
- [ ] Build the training venv (10 GB of downloads):
      `.\training\setup.ps1`
      It ends by printing your GPU name. If `import unsloth` fails, see "WSL2 route" in
      `docs/15-training.md`; kohya (the LoRA) works regardless.
- [ ] Restart the worker. It now logs `kinds=[..., 'train']`.

## 3. First training run: the style LoRA (the big win)

Needs 30-50 images in `assets\approved\`. If task 002 (reference images) and the tileset tasks
have run, you have them. If not, hand-pick: anything you would put in the game goes in
`assets\approved\<name>\`; quick way is `scripts\override.py session` (next section).

- [ ] On the server: `.\studio.ps1 scripts\enqueue_train.py sdxl_lora`
      It builds the dataset, prints the image count, and queues the job. The worker picks it up
      when the gaming PC is on and not in gaming mode. 45-90 minutes.
- [ ] When `assets\training\models\sdxl_lora-<date>\manifest.json` exists, on the gaming PC:
      `worker\.venv\Scripts\python.exe scripts\activate_model.py sdxl_lora`
      This copies the LoRA into ComfyUI, adds a `STYLE_LORA` node to `worker\workflows\default.json`,
      and adds the trigger word `rrstyle` to the style bible. Commit those two files.
- [ ] Judge the next ten generated images yourself. Worse? `worker\.venv\Scripts\python.exe scripts\activate_model.py rollback sdxl_lora`.
      Try `--strength 0.6` before giving up on it.

## 4. Ten minutes a week: grade the reviewer

```powershell
.\studio.ps1 scripts\override.py session
```
Opens each recent image in your viewer, shows what the machine decided, asks `y` / `n` / `s`.
Agreeing is a label too. Disagreeing moves the file to the right folder immediately, so this
is also how you fix wrong calls. `.\studio.ps1 scripts\override.py stats` shows the counts.
At 100 of your decisions the reviewer recipe becomes worth running.

## 5. Later: coder and reviewer fine-tunes

- [ ] Coder, once `scripts\override.py stats` shows 150+ `coder_passed` (or sooner using the
      public code alone; it will still fix Godot 3 habits):
      `.\studio.ps1 scripts\enqueue_train.py coder`  (2-6 hours on the 3080 Ti)
      then on the server `.\studio.ps1 scripts\activate_model.py coder` (imports into Ollama as
      `reapers-coder`), then **measure**: `.\studio.ps1 training\eval_coder.py --model reapers-coder`.
      Better than the baseline row? Set `CODER_MODEL=reapers-coder` in `.env`, restart.
- [ ] Reviewer, once 100+ of your verdicts exist:
      `.\studio.ps1 scripts\enqueue_train.py reviewer`, then `.\studio.ps1 scripts\activate_model.py reviewer`
      prints the serve command for the gaming PC and the two `.env` lines.
- [ ] Set `AUTO_TRAIN=1` when you trust the loop. The daily pass then queues a retrain whenever
      a recipe's data has grown past its threshold. Activation stays manual.

## 6. What you will see

- `PROGRESS.md` gains a "Training data" row: coder runs / passed, verdicts, your verdicts.
- `docs\decisions.md` gets an "(auto) trained ..." line per finished run.
- `data\training\latest.json` lists every finished model and where it is.
- `reports\eval-coder.md` is the scoreboard.

## 7. Ideas worth trying after the basics work

Brainstorm, roughly in order of bang for buck. None are built yet.

1. **Best-of-N with the gate as judge.** Run the coder twice on the same job with different
   seeds, keep whichever passes; both traces are DPO material. Doubles CPU time per job, which
   nobody notices unattended, and roughly doubles the labelled pairs.
2. **Slow teacher, fast student.** Let the escalation model (gpt-oss-120b) do one extra deferred
   task per night purely to generate training runs. Its passes are the highest-quality coder
   examples you will ever get, and the 7B student picks them up.
3. **Synthetic Godot 4 Q&A from the docs.** Have the orchestrator model write 2,000 short
   question/answer pairs from `data\godot-docs\classes` (signal names, method signatures,
   4.x renames). Cheap CPU work, teaches the exact API surface.
4. **Active learning for the reviewer.** Log the verdict's confidence (ask for it in the JSON)
   and have `override.py session` show the least confident ones first. You label where it
   matters most.
5. **Per-kind LoRAs.** One LoRA for characters, one for tiles, one for props; the artist role
   picks by job kind. Better than one LoRA doing everything once you pass 200 approved images.
6. **Palette snapping as a hard gate.** A 20-line script that quantises every incoming PNG to
   the 16 palette colours and rejects anything that changed by more than a few percent. Removes
   the most common rejection reason from the reviewer's plate entirely.
7. **Style-consistency pairs for the reviewer.** Show it two approved images and one rejected
   and ask which is the odd one out; a contrastive task that teaches consistency rather than
   "is this pretty".
8. **A test-writing fine-tune.** The coder's weakest habit is usually the gdUnit4 test. Train a
   small model only on the passed runs' test files, and have the coder call it as a tool.
9. **Nightly self-play backlog.** When the backlog is empty, generate tiny throwaway tasks
   ("add a signal to X", "write a test for Y") purely to farm coder traces on the server while
   the GPU box is off. Delete the branches, keep the traces.
10. **Distil the reviewer into a classifier.** Once you have 1,000 verdicts, a tiny CLIP-based
    approve/reject classifier can run per image in milliseconds and pre-filter before the VL
    model looks, cutting reviewer time on CPU by most of it.

