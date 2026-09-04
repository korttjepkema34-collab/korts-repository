# 04 - Models

**Tags verified against the Ollama library on 2026-09-02** (via search results; the library
site itself was not reachable from the scaffolding session). Re-check with `ollama pull` before
the first run; if a tag has moved, update this file, `server/.env` and `decisions.md`. Prefer
Apache 2.0 or MIT licences.

## Recommended picks by role

| Role | Runs on | Primary pick | Why | Fallback |
|---|---|---|---|---|
| **Orchestrator** | server (CPU now, CPU+12 GB later) | **`qwen3.6:35b-a3b`** (MoE, ~20 GB, Apache 2.0) | Fast on CPU because only ~3B params are active per token. Good tool calling and planning. Fits RAM with room to spare. | **gpt-oss-120b** (MoE, ~60 GB mxfp4, Apache 2.0): smarter, slower on CPU, only viable because of 96 GB RAM. Becomes the pick once the 12 GB card lands and attention can sit on GPU. |
| **Coder** | **server** (CPU now) | **`qwen3.6:35b-a3b-coding`** (same MoE, code-tuned) or `qwen3-coder:30b` | Runs on CPU at usable speed because only ~3B params are active; the coder is file-based and headless so it needs no GPU | **Escalation: gpt-oss-120b** (~60 GB, ~5-10 tok/s on CPU). Slow, but unattended runs do not care. Used for deferred tasks once a day. |
| **Reviewer / QA** | server | **`qwen3-vl:8b`** (6.1 GB) | Sees the image, compares to style references, writes structured verdicts. Small enough to stay resident once the server GPU exists. | Same model on gpu box until then, or a larger VL model on CPU (slow). |
| **2D artist** | gpu (server later) | **SDXL** + pixel-art / style LoRAs in **ComfyUI** | Fits 12 GB easily, huge LoRA ecosystem, IP-Adapter for reference consistency | **FLUX** GGUF Q8 for backgrounds and concept art when quality matters more than speed |
| **Music** | gpu (server later) | **ACE-Step 1.5** (~8 GB) | Full track in seconds on a 3090-class card, lyrics support, diffusion so easy to steer | YuE 7B for vocal-heavy tracks |
| **SFX** | gpu (server later) | **Stable Audio Open** | Built for short samples and effects | MusicGen for stingers |
| **Voice** (optional) | server | **Kokoro** or **Chatterbox** TTS | Small, fast, good enough for placeholder dialogue | |
| **Embeddings** (memory/RAG over docs and code) | server | **nomic-embed-text** or **bge-m3** | Tiny, fast on CPU | |
| **Animation (2D)** | gpu | SDXL + character reference sheet, frame by frame, with the reviewer checking consistency | No dedicated open sprite-animation model is reliable yet | Open sprite bases (LPC) as a fallback for walk cycles; see docs/10-game-design.md |

## Fine-tuned slots (docs/15-training.md)

| Slot | After training | Served by | `.env` |
|---|---|---|---|
| Coder | `reapers-coder` (7B dense QLoRA merged, q4_K_M) | Ollama on the server, or the GPU box when idle | `CODER_MODEL`, optional `CODER_BASE_URL` |
| Reviewer | fine-tuned Qwen2.5-VL-3B / Qwen3-VL-4B | `training/serve_reviewer.py` on the GPU box (server once it has a card) | `REVIEWER_MODEL`, `REVIEWER_BASE_URL` |
| 2D artist | SDXL + `rrstyle` LoRA | ComfyUI, `STYLE_LORA` node in `worker/workflows/default.json` | none |

## Placement rules

1. **The orchestrator must be a MoE model** while the server has no GPU. Dense models are too
   slow on DDR4.
2. **The coder agent always runs on the server**; only its model can live elsewhere. When the
   GPU box is idle, point `CODER_BASE_URL` at an Ollama there so prompt processing (reading a lot
   of code, where CPU inference hurts most) is fast; leave it empty to use the server's own
   Ollama, which is the default and what happens whenever the GPU is busy or off.
3. **Only one generative model resident on the 3080 Ti at a time.** The worker groups jobs by
   kind so it does not thrash.
4. **Once the server has a 12 GB card**, move the reviewer there permanently, move SDXL and
   ACE-Step there as a second lane, and switch the orchestrator to a bigger MoE with attention on
   the GPU (llama.cpp `--n-cpu-moe` / tensor override to keep experts in RAM).

## Ollama pull list (verify tags first)

```bash
# all on the server (native Ollama, Windows)
ollama pull qwen3.6:35b-a3b          # orchestrator, MoE ~20 GB
ollama pull qwen3.6:35b-a3b-coding   # coder, same family tuned for code
ollama pull qwen3-vl:8b              # reviewer, vision, 6.1 GB
ollama pull gpt-oss:120b             # escalation, ~65 GB, slow on CPU, fits in 96 GB
ollama pull nomic-embed-text         # embeddings
# alternatives
# ollama pull qwen3-coder:30b        # coder alternative, MoE 3B active, 19 GB
# ollama pull gpt-oss:20b            # escalation fallback if RAM is tight, 13 GB
# ollama pull qwen3-vl:4b            # smaller reviewer, 3.3 GB
```

Total on disk for the primary set: roughly 115 GB. Ollama keeps at most two loaded
(`OLLAMA_MAX_LOADED_MODELS=2`), so RAM use peaks around 85 GB when the escalation model and the
reviewer are both resident. That fits 96 GB with little margin; if the box also runs Docker
Desktop, keep the WSL2 cap at 16 GB or drop to `gpt-oss:20b`.

## Coder on the GPU when it is online (2026-09-03)

`CODER_BASE_URL_GPU` + `CODER_MODEL_GPU=qwen3.6:27b`: Ollama on the gaming PC, bound to its
Tailscale IP. The orchestrator probes it every minute; when it answers, code jobs run there on the
current best local coder (dense 27B, partially offloaded on 12 GB) and a Redis lock makes the GPU
worker wait before loading image models. When the gaming PC is off, the CPU MoE takes over. Same
thing for escalated code jobs. Set it up: `ollama pull qwen3.6:27b` on the gaming PC and
`OLLAMA_HOST=0.0.0.0:11434` there; firewall the port to the tailnet. Research: `docs/20-research-notes.md`.

## Escalation climbs a free cloud ladder first (2026-09-04)

`ESCALATION_LADDER`: Ollama Cloud models (`-cloud`, after `ollama signin`) and OpenRouter `:free`
models are tried in order for escalated work only, with cooldowns and daily caps, and the local
`gpt-oss:120b` is always the last rung. `VISION_LADDER` does the same for playtest and proof
judgements. Details, limits and the privacy caveat: `docs/24-cloud-escalation.md`.

## Escalation is free too

Decision: strictly free. When the fast model fails a task (caps hit, task deferred), the daily
pass retries it with `ESCALATION_MODEL`: the biggest model that fits in 96 GB RAM. gpt-oss-120b
at ~60 GB is the current pick. It runs at a few tokens per second on CPU, which would be
unusable interactively and is perfectly fine unattended.

The LLM client still speaks the OpenAI-compatible format, so a paid endpoint remains a
one-line config change if the owner ever changes their mind. Nothing in the code assumes it.

## Licence notes

| Model | Licence | Commercial use |
|---|---|---|
| Qwen 3.x family | Apache 2.0 | Yes |
| gpt-oss | Apache 2.0 | Yes |
| SDXL | CreativeML OpenRAIL++ | Yes with use restrictions |
| FLUX.1 dev | Non-commercial | **No** for shipped assets. Use schnell (Apache 2.0) or SDXL |
| ACE-Step | Apache 2.0 | Yes |
| Stable Audio Open | Stability Community | Free under revenue threshold; check |

Every generated asset gets a sidecar JSON recording generator, model, licence, prompt, and seed.
