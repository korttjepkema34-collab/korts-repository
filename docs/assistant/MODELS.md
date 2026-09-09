# Models and free-only routing

## Decisions

The cloud is the brain. Local models are bounded workers. Cloud unavailable means waiting for
cloud decisions, never local takeover. User reports approximately 600 requests during heavy daily
OpenRouter use; use the 1,000/day entitlement as the initial planning baseline and measure actual
automation traffic. Do not waste model calls polling job status.

## Initial candidates, not benchmark winners

| Role | Candidate | Where | Qualification needed |
|---|---|---|---|
| Cloud coordinator and separate review session | `qwen/qwen3-coder:free` if still listed | OpenRouter | JSON plans, critique, tool/harness compatibility, adequate reasoning |
| Alternative cloud brain | An actually eligible cloud model in the user's Ollama account | Ollama cloud via local daemon | Included free allowance, reasoning, no paid overflow |
| Lightweight writing/operations | `qwen3.5:4b` | Server CPU | Correctness, latency, memory |
| Bounded coding/vision | `qwen3.5:9b` | RTX 3080 Ti | 12 GB VRAM fit at selected context; correctness |
| Optional future semantic indexing | `nomic-embed-text` already referenced by legacy code | Local Ollama | Retrieval value over FTS, not required initially |

The 9B quantized Ollama download is about 6.6 GB; runtime/context add memory. Do not infer a 30B
model fits entirely in 12 GB VRAM. The proposed 8K worker context differs from a full Claude Code
repo session: Ollama recommends larger context for that use. Prefer small file scopes and measured
latency. No GPU purchase or local 120B coordinator is part of the current setup.

## Qualification, in order

1. Configure the key/eligible cloud model as SETUP describes. Leave qualification false.
2. Run `python -m assistant.qualify`. This explicitly makes live calls through Claude Code using
   the chosen free route. It checks ordering, rejection of fake test success, cloud-only authority,
   and a small debugging case. Results are saved privately; config is not changed automatically.
3. Inspect every answer and provider account usage. Confirm no paid route or Claude subscription
   was consumed. A smoke pass is a starting check, not proof of universal competence.
4. Try a real bounded task with a deliberately flawed worker answer, then a corrected answer.
5. Record model ID, provider, date, versions, latency, outputs, failures and review quality.
6. Only then set `qualified:true`; keep only qualified fallbacks. If no candidate qualifies, pause.

The current catalog price check covers OpenRouter model pricing. CLI/tool/provider behavior must
still be observed during live qualification. Automatic top-up stays disabled; paid fallback is
never configured. A local counter counts controller invocations and attempts, while the provider
counts actual requests; other applications share the account allowance.

Ollama's current free plan describes included starter usage and limited concurrency. Account
allowances and eligible models can change. `included_usage_confirmed:true` is a user configuration
attestation, not a programmatic billing guarantee. When allowance is exhausted, wait or use another
qualified free cloud route.

## Capability routing

A cloud endpoint is not automatically smarter. Keep tests representative of your business and game.
Workers may share the same underlying model but have different prompts, context, skills and checks.
Vision input support is not image generation. SFX needs an audio generator, not text-to-speech.

Sources checked during preparation: [Ollama Claude Code integration](https://docs.ollama.com/integrations/claude-code),
[Ollama pricing](https://ollama.com/pricing), [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits),
[OpenRouter Claude Code integration](https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration),
[Qwen 4B](https://ollama.com/library/qwen3.5:4b), [Qwen 9B](https://ollama.com/library/qwen3.5:9b).
Recheck account/model facts when installing; no changing model ID is treated as permanently available.

## Expanded specialist research bench

The owner approved retaining the expanded bench in [WORKFORCE-PLAN.md](WORKFORCE-PLAN.md), not activating every model. That table covers larger server MoE/background candidates, smaller GPU coding/vision/review candidates and ComfyUI media. The initial candidates above describe the earlier setup; neither list is a measured winner roster. Runtime defaults and private profiles are unchanged by this documentation.

The cloud shortlist includes Nemotron Ultra, Nex-N2.5-Pro and Inkling, with other candidates retained for evaluation. Recheck exact free endpoint IDs and privacy terms. Do not convert names directly into executable configuration. File size does not establish runtime memory fit; record exact artifact revision, quant, runtime compatibility, measured context, peak RAM/VRAM, load time and quality.

Use 15–20 representative orchestration cases covering dependencies, hardware contention, gaming, cloud outage, privacy, failed evidence, review, restart and model handoff. Test image delivery through the actual adapter separately. Different model families offer review diversity, not guaranteed correctness. Keep vendor claims and transcript opinion scores separate from observed measurements. No automatic promotion or model downloads are authorized here.
