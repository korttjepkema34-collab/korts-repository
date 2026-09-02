# 04 - Models

**Verify tags before pulling.** Model names below come from mid-2026 roundups and this
document's author's knowledge. Names and quantisation tags change; check the Ollama library or
Hugging Face for the current tag and update this file plus `decisions.md`. Prefer Apache 2.0 or
MIT licences.

## Recommended picks by role

| Role | Runs on | Primary pick | Why | Fallback |
|---|---|---|---|---|
| **Orchestrator** | server (CPU now, CPU+12 GB later) | **Qwen3.6-35B-A3B** (MoE, ~20 GB Q4, Apache 2.0) | Fast on CPU because only ~3B params are active per token. Good tool calling and planning. Fits RAM with room to spare. | **gpt-oss-120b** (MoE, ~60 GB mxfp4, Apache 2.0): smarter, slower on CPU, only viable because of 96 GB RAM. Becomes the pick once the 12 GB card lands and attention can sit on GPU. |
| **Coder** | **server** (CPU now) | **Qwen3-Coder MoE** (30B-A3B class, ~18 GB Q4) | Runs on CPU at usable speed because only ~3B params are active; the coder is file-based and headless so it needs no GPU | **Escalation: gpt-oss-120b** (~60 GB, ~5-10 tok/s on CPU). Slow, but unattended runs do not care. Used for deferred tasks once a day. |
| **Reviewer / QA** | server | **Qwen3-VL** small (~8B, ~6 GB Q4) | Sees the image, compares to style references, writes structured verdicts. Small enough to stay resident once the server GPU exists. | Same model on gpu box until then, or a larger VL model on CPU (slow). |
| **2D artist** | gpu (server later) | **SDXL** + pixel-art / style LoRAs in **ComfyUI** | Fits 12 GB easily, huge LoRA ecosystem, IP-Adapter for reference consistency | **FLUX** GGUF Q8 for backgrounds and concept art when quality matters more than speed |
| **3D artist** | gpu | **TRELLIS 2** (MIT) | Best quality among fully open, no usage restrictions, ~6 GB for shape | **Hunyuan3D 2.x** for texturing when VRAM allows; Blender addon exists; exports glTF/OBJ/FBX |
| **Music** | gpu (server later) | **ACE-Step 1.5** (~8 GB) | Full track in seconds on a 3090-class card, lyrics support, diffusion so easy to steer | YuE 7B for vocal-heavy tracks |
| **SFX** | gpu (server later) | **Stable Audio Open** | Built for short samples and effects | MusicGen for stingers |
| **Voice** (optional) | server | **Kokoro** or **Chatterbox** TTS | Small, fast, good enough for placeholder dialogue | |
| **Embeddings** (memory/RAG over docs and code) | server | **nomic-embed-text** or **bge-m3** | Tiny, fast on CPU | |
| **Animation** | gpu | No good open pick yet | Use Mixamo (free, closed) for humanoid rigs; Hunyuan3D Studio pipeline for rigging is worth testing | Track in `open-questions.md` |

## Placement rules

1. **The orchestrator must be a MoE model** while the server has no GPU. Dense models are too
   slow on DDR4.
2. **The coder should run on the GPU box when the GPU is idle** because it reads a lot of code
   (prompt processing) and that is where CPU inference hurts most. Fall back to the server MoE
   model when the GPU is busy generating assets.
3. **Only one generative model resident on the 3080 Ti at a time.** The worker groups jobs by
   kind so it does not thrash.
4. **Once the server has a 12 GB card**, move the reviewer there permanently, move SDXL and
   ACE-Step there as a second lane, and switch the orchestrator to a bigger MoE with attention on
   the GPU (llama.cpp `--n-cpu-moe` / tensor override to keep experts in RAM).

## Ollama pull list (verify tags first)

```bash
# server
ollama pull qwen3.6:35b-a3b          # orchestrator  (verify exact tag)
ollama pull qwen3-vl:8b              # reviewer      (verify exact tag)
ollama pull nomic-embed-text         # embeddings
# gpu box (optional, when idle)
ollama pull qwen3-coder:14b          # coder         (verify exact tag)
```

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
| TRELLIS 2 | MIT | Yes |
| Hunyuan3D 2.x | Tencent Hunyuan Community | Check current terms, has territory and MAU clauses |
| SDXL | CreativeML OpenRAIL++ | Yes with use restrictions |
| FLUX.1 dev | Non-commercial | **No** for shipped assets. Use schnell (Apache 2.0) or SDXL |
| ACE-Step | Apache 2.0 | Yes |
| Stable Audio Open | Stability Community | Free under revenue threshold; check |

Every generated asset gets a sidecar JSON recording generator, model, licence, prompt, and seed.
