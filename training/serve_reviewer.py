"""Serve a fine-tuned vision reviewer as an OpenAI-compatible endpoint (what reviewer.py speaks).

    python training/serve_reviewer.py --model assets/training/models/reviewer-.../merged --port 8191

Then in server/.env:  REVIEWER_BASE_URL=http://<gpu tailscale ip>:8191/v1   REVIEWER_MODEL=reapers-reviewer
Runs on the GPU box now, on the server once it has its 12 GB card. Handles one request at a time,
which is all the studio needs. Accepts `image_url` data URIs like Ollama does.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import threading
import time

import torch
import uvicorn
from fastapi import FastAPI
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

app = FastAPI()
LOCK = threading.Lock()
STATE: dict = {}


def _parse(messages: list[dict]) -> tuple[list[dict], list[Image.Image]]:
    """OpenAI content blocks -> HF chat content + PIL images."""
    images: list[Image.Image] = []
    out = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            out.append({"role": m["role"], "content": [{"type": "text", "text": c}]}); continue
        blocks = []
        for b in c or []:
            if b.get("type") == "text":
                blocks.append({"type": "text", "text": b["text"]})
            elif b.get("type") == "image_url":
                url = b["image_url"]["url"]
                if url.startswith("data:"):
                    raw = base64.b64decode(url.split(",", 1)[1])
                    images.append(Image.open(io.BytesIO(raw)).convert("RGB"))
                    blocks.append({"type": "image"})
        out.append({"role": m["role"], "content": blocks})
    return out, images


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": STATE["name"], "object": "model"}]}


@app.post("/v1/chat/completions")
def chat(body: dict):
    msgs, images = _parse(body.get("messages", []))
    proc, model = STATE["proc"], STATE["model"]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    with LOCK:
        inputs = proc(text=[text], images=images or None, return_tensors="pt").to(model.device)
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=int(body.get("max_tokens") or 300), do_sample=False)
        reply = proc.batch_decode(gen[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
    if (body.get("response_format") or {}).get("type") == "json_object":
        m = re.search(r"\{.*\}", reply, re.S)
        reply = m.group(0) if m else json.dumps({"verdict": "rejected", "reason": "model returned no JSON: " + reply[:200]})
    return {"id": f"chatcmpl-{int(time.time())}", "object": "chat.completion", "created": int(time.time()), "model": STATE["name"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": int(inputs["input_ids"].shape[1]), "completion_tokens": int(gen.shape[1] - inputs["input_ids"].shape[1])}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="merged model dir (or base id + --lora)")
    ap.add_argument("--lora", default=None)
    ap.add_argument("--name", default="reapers-reviewer")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8191)
    a = ap.parse_args()
    proc = AutoProcessor.from_pretrained(a.model)
    model = AutoModelForImageTextToText.from_pretrained(a.model, torch_dtype=torch.bfloat16, device_map="auto")
    if a.lora:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.lora).merge_and_unload()
    model.eval()
    STATE.update(proc=proc, model=model, name=a.name)
    print(f"reviewer {a.name} ready on {a.host}:{a.port}", flush=True)
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
