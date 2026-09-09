> **Setup migration notice:** For the personal/business/game assistant, [assistant/SETUP.md](assistant/SETUP.md) and [assistant/DECISIONS.md](assistant/DECISIONS.md) supersede older model, hardware, autonomy and installation choices below. Game design remains preserved.

# 02 - Hardware

## Machines

### `server` (home server, always on)

| Part | Spec |
|---|---|
| CPU | Intel Core i7-10700K, 8 cores / 16 threads, 3.8 GHz, AVX2 (no AVX-512). **Has Intel UHD 630 integrated graphics**, enough to run the Godot editor and windowed scenes for screenshots. |
| RAM | 96 GB DDR4 |
| GPU | None today. **Planned: 12 GB Nvidia card, RTX 3060 12 GB preferred.** |
| Platform | Z490-era, PCIe 3.0 |
| OS | Windows. Ollama, Syncthing and the orchestrator run natively; Redis and Forgejo in Docker Desktop (`docs/06-setup-server.md`) |

What it is good at: holding large models in RAM, running 24/7, git, queue, headless Godot.
What it is bad at: CPU inference is slow at **reading** long inputs (prompt processing is
compute-bound) and slow at generating with dense models (memory-bandwidth-bound). Use
mixture-of-experts models here. Nothing that needs CUDA runs here until the GPU arrives.

Rough CPU inference expectations (DDR4, dual channel):

| Model type | Expected speed |
|---|---|
| Dense 27B, Q4 | 2-3 tokens/s, painful |
| MoE ~35B total / ~3B active, Q4 | 15-20 tokens/s, fine for an orchestrator |
| MoE ~120B total / ~5B active, mxfp4 (~60 GB) | 5-10 tokens/s, fits only because of 96 GB RAM |

### `gpu` (gaming PC, online when not gaming)

| Part | Spec |
|---|---|
| CPU | AMD Ryzen 9 7900X, 12 cores / 24 threads |
| RAM | 32 GB DDR5 |
| GPU | Nvidia RTX 3080 Ti, **12 GB VRAM** |
| OS | Windows |

What fits in 12 GB, one at a time:

| Task | Fits? | Notes |
|---|---|---|
| SDXL + LoRAs | Yes | Comfortable |
| FLUX | Borderline | Use GGUF quant or schnell, not full dev fp8 |
| ACE-Step 1.5 | Yes | ~8 GB |
| Stable Audio Open | Yes | |
| 14B LLM, Q4 | Yes | ~9 GB, but blocks asset jobs while loaded |
| 27B LLM, Q4 | Partial | 14-17 GB, spills into system RAM, slower |

## Why both machines, not one

Asset generation needs CUDA, so it lives on `gpu`. Planning, code review, queue, git, and tests
do not, so they live on `server` and keep running while the gaming PC is off or in use. With a
12 GB card added to the server, sprites and music can also run there, leaving the 3080 Ti
for the heavier image workflows.

## Planned upgrade: 12 GB card for the server

Decision: **yes, worth it.** A 6 GB card is not (only fits tiny models). Stay on Nvidia; every
tool assumes CUDA. Avoid Tesla P40/P100: cheap 24 GB but aging, needs a cooling shroud, and newer
PyTorch builds are dropping support.

What it buys:

1. **Fast prompt processing for the orchestrator.** llama.cpp can keep MoE experts in system RAM
   and put attention + KV cache on the GPU. The server then runs a model far larger than 12 GB at
   usable speed. This is the single biggest upgrade to the orchestrator.
2. **A second asset lane.** SDXL and ACE-Step fit. Sprites and music without waking the gaming PC.
3. **Always-resident reviewer.** A small vision model stays loaded to QA every asset.

Check before buying: physical slot clearance in the server case, PSU wattage and a spare 8-pin
connector, and that the PCIe x16 slot is free.

## Networking

Both machines are on the same **Tailscale** tailnet and the same physical LAN. Services bind to
the Tailscale interface. The server can send Wake-on-LAN packets to the gaming PC over the LAN.
See `docs/03-architecture.md` and `scripts/`.

