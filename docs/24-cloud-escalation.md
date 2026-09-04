# 24 - Free cloud escalation: Ollama Cloud and OpenRouter

The main loop stays local. Escalation, the rare work where a better model changes the outcome,
climbs a **ladder** of free cloud rungs and lands on the local big model if every rung is out.

## What escalates

- A deferred task's daily retry (planning with a stronger model).
- Code jobs after the same failure class repeats 3 times in 24 h.
- The engineer fixing the studio's own code.
- Planning repair when the fast model's plan failed validation twice.
- Playtest reports and proof-run judgements when `VISION_LADDER` is set.

Routine planning, coding, review and content never touch the cloud.

## The ladder

`ESCALATION_LADDER` in `server/.env`, provider:model rungs in order:

| Provider | Example rung | Needs | Free limits (2026) |
|---|---|---|---|
| `ollama` | `ollama:qwen3-coder:480b-cloud`, `ollama:gpt-oss:120b-cloud` | `ollama signin` once on the server; the model name ends in `-cloud` and runs through the same local daemon, so nothing else changes | Metered by GPU time; session caps that reset every few hours plus a weekly cap; one model at a time |
| `openrouter` | `openrouter:qwen/qwen3-coder:free`, `openrouter:deepseek/deepseek-chat-v3.1:free` | `OPENROUTER_API_KEY` | 20 requests/minute; 50 requests/day, or 1000/day forever after buying $10 of credit once |
| `local` | `local:gpt-oss:120b` | nothing | none; slow |

The local `ESCALATION_MODEL` is always appended, so escalation never fails for lack of a cloud.
When the gaming PC is online its coder is inserted before the local rung.

## How it behaves

- A rung that errors for any reason (quota, auth, outage, a free model that rejects tool calls)
  is cooled down for `LADDER_COOLDOWN_S` (default one hour) and the next rung is tried, inside
  the same run. Tool loops continue on the next rung mid-run; the OpenAI-compatible transcript
  carries over.
- Per-provider daily request caps (`OPENROUTER_DAILY_CAP` 40, `OLLAMA_CLOUD_DAILY_CAP` 60) are
  enforced from `reports/model_usage.json`, which also shows what was used today.
- Nothing retries a cooled rung within the hour, so a dead free model costs one failed call.

## Two honest caveats

1. **Free OpenRouter endpoints may keep your prompts.** Some providers offer free capacity as a
   data-gathering channel. The studio sends game code, task text and the world bible, none of
   which is secret, but do not put anything private in the repo if you use those rungs. Ollama
   Cloud states it does not retain prompts.
2. **Free models rotate.** A rung that disappears just cools down every hour and costs one
   request a day. Check `reports/model_usage.json` and the OpenRouter free list monthly and
   update the ladder. The `:free` IDs in the example env are current as of September 2026.

## Setup

1. Server: `ollama signin` (opens a browser once). Test: `ollama run gpt-oss:120b-cloud "say hi"`.
2. OpenRouter: create a key at openrouter.ai/keys, put it in `OPENROUTER_API_KEY`. Optional
   but recommended: buy $10 of credit once to lift the daily limit from 50 to 1000 for good.
3. Leave `ESCALATION_LADDER` as the example or edit the order. The doctor reports which rungs
   are configured.
