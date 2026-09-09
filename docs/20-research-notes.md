> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 20 - Research notes: models, prior art, and what changed because of them (2026-09-03)

## Model re-check

| Slot | Was | Now | Why |
|---|---|---|---|
| Coder on the CPU server | `qwen3.6:35b-a3b-coding` | unchanged | A dense 27B would run at 2-3 tokens/s on DDR4. On CPU the MoE is still the only usable coder. |
| **Coder on the gaming PC (new)** | none | `qwen3.6:27b` via `CODER_BASE_URL_GPU` | Current top local coder (77.2 SWE-bench Verified, 17 GB). Partially offloaded on the 12 GB card it is still far better than the CPU MoE. The orchestrator routes code jobs there whenever the gaming PC is online and holds a VRAM lock so image jobs wait. Alternatives: `glm-4.7-flash` (19 GB MoE), `devstral:24b` (14 GB, agentic), `gpt-oss:20b` (13 GB). |
| Orchestrator | `qwen3.6:35b-a3b` | unchanged | Planning is now mostly template filling; speed matters more than depth. |
| Escalation | `gpt-oss:120b` | unchanged on CPU; the GPU coder takes escalated code jobs when online | |
| Reviewer | `qwen3-vl:8b` | unchanged model, changed method | The gain was in how it is asked, not which model: binary rubric, nearest-neighbour upscale, deterministic checks first. Candidates to A/B with the eval set later: MiniCPM-V, Molmo2 8B, Gemma 4 vision variants. |
| Image generation | SDXL + Pixel Art XL LoRA | SDXL stays the default; **FLUX.2 klein 4B is the recommended upgrade** | Distilled 4-step model that fits 12 GB, with a pixel-art LoRA trained for transparent sprite output, a **4-direction walk-cycle sprite-sheet LoRA for 32x32 characters**, and a single-image-to-4-view LoRA. The walk-cycle LoRA directly attacks our weakest art problem (animation consistency). Needs a ComfyUI workflow exported from the FLUX.2 klein template with our node titles; see `worker/workflows/README.md`. |
| Audio | ACE-Step 1.5, Stable Audio Open | unchanged | |
| GDScript fine-tune | (training branch) | unchanged | godot-dodo and GD-Copilot-finetune show the recipe works: filter to Godot 4 projects, split per function, caption with an LLM. `training/collect_godot4_code.py` already follows it. |

## Prior art on autonomous game development

- **godogen** (Claude Code / Codex driving Godot, Bevy, Babylon.js): the one rule worth stealing is
  *proof over claims*: judge the running game from a recording or live view, never from a clean
  compile. Unattended runs end with a short proof recording. Now in this repo as `proof_run`
  (coder tool) and the post-merge proof check on any code job with a `scene`.
- **GameCraft-Bench** (140 Godot tasks, 15 game families): the best agent scores 41%. Agents get
  mechanics working but fail on *content completeness, functional visual feedback, and coherent
  presentation*. Verification replays recorded input and judges with a rubric and a multimodal
  model. Now in this repo: every code job's acceptance list gets "every state change has visible
  feedback", proof runs replay input and are judged by the vision model.
- **GameDevBench**: tutorial-derived localized edits only; confirms that small, local edits are
  what agents do reliably. Our planner already splits work that way; the templates make it stricter.
- **"Full game in one day with sub-agents"** (dev.to, 2026): the value was in the orchestration,
  not any single agent. Matches our design.
- **Godot AI agent guides (Summer Engine, 2026)**: agents that can run the project and read
  runtime errors beat file-only agents. We have both paths.

## Where small local models are weak, and the mechanism that covers each

| Weakness | Mechanism (all live) |
|---|---|
| Invents APIs | `search_godot_api` (exact class reference) + `search_docs` (tutorials, repo code) + cookbook in every prompt |
| Cannot hold a long plan | Planner templates: it names an asset type and a subject, the mechanics are filled in; code jobs get boilerplate acceptance; at most 8 small jobs |
| Emits invalid JSON / schema | Repair loop: the validation error goes back to the model once |
| Repeats the same mistake | `docs/lessons.md`: every failure-then-success is distilled to one line and fed to the coder; failure-class escalation after 3 repeats |
| Holistic judgements are unreliable | Reviewer answers 8 yes/no questions; the verdict is computed by rule |
| Cannot see small sprites | Candidates are upscaled with nearest-neighbour before the vision call |
| Claims success from a clean compile | Proof runs: replayed input, screenshots per second, vision model checks the expected behaviour |
| Palette / size drift | Worker quantises to the 16 colours; orchestrator rejects off-palette or wrong size before any model looks |
| Weak tool calling | JSON-in-text fallback; low temperature |
| Sloppy syntax | gdformat auto-fix, gdlint, Godot 3 pattern scan in the gate |
| Slow, weak CPU coder | GPU routing to a dense 27B on the gaming PC when it is online, with a VRAM lock |
| Everything else | Traces of every run, the eval set, and the training branch's fine-tune recipes |

## Is it hands-off?

The orchestrator does not talk to ComfyUI or the audio tools directly, and should not: it puts
jobs on the queue and the GPU worker's handlers drive ComfyUI's HTTP API and the audio API. Once
the tools are installed, nothing in the loop needs a person. What still needs a person, once:
installing the tools and downloading model files. `scripts/bootstrap_gpu.ps1` and
`scripts/bootstrap_server.ps1` now do most of that; the remaining manual items are in `docs/13`.

## Sources

- [Best Ollama Models 2026 (Morph)](https://www.morphllm.com/best-ollama-models)
- [Best Local LLM for Coding 2026 (WhatLLM)](https://whatllm.org/best-local-llm-for-coding)
- [Best Ollama Models September 2026 (BenchLM)](https://benchlm.ai/best/ollama-models)
- [Best Local LLMs for 24GB VRAM (LocalLLM.in)](https://localllm.in/blog/best-local-llms-24gb-vram)
- [Best Vision-Language Models 2026 (Mixpeek)](https://mixpeek.com/curated-lists/best-vision-language-models)
- [Open-source VLMs 2026 (BentoML)](https://www.bentoml.com/blog/multimodal-ai-a-guide-to-open-source-vision-language-models)
- [Open-source image generation models 2026 (BentoML)](https://www.bentoml.com/blog/a-guide-to-open-source-image-generation-models)
- [FLUX.2 klein pixel-art LoRA (Limbicnation)](https://huggingface.co/Limbicnation/pixel-art-lora)
- [FLUX.2 klein 4-walk pixel sprite-sheet LoRA (svntax-dev)](https://huggingface.co/svntax-dev/pixel_spritesheet_4walk_small_lora_v1/blob/main/README.md)
- [FLUX.2 klein sprite-sheet 4-view LoRA (fal)](https://huggingface.co/fal/flux-2-klein-4b-spritesheet-lora)
- [Fine-tune FLUX.2 klein with a LoRA (Black Forest Labs)](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora)
- [Pixel Art XL with ComfyUI (Kokutech)](https://www.kokutech.com/blog/gamedev/tips/art/pixel-art-generation-with-comfyui)
- [godogen: autonomous game development](https://github.com/htdt/godogen)
- [GameCraft-Bench](https://arxiv.org/abs/2606.17861) and its [code](https://github.com/FreedomIntelligence/gamecraft-bench)
- [GameDevBench](https://arxiv.org/pdf/2602.11103)
- [Gamedev AI for Godot 4.6+ (Asset Library)](https://godotengine.org/asset-library/asset/5086)
- [I built a full game in one day using AI agents (dev.to)](https://dev.to/maxxmini/i-built-a-full-game-in-one-day-using-ai-agents-heres-what-happened-3c3o)
- [Godot AI Agent Guide 2026 (Summer Engine)](https://www.summerengine.com/blog/godot-ai-agent-guide)
- [godot-dodo: fine-tuning LLMs for GDScript](https://github.com/minosvasilias/godot-dodo)
- [GD-Copilot-finetune](https://github.com/kparasha/GD-Copilot-finetune)

