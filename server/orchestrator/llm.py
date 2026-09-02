"""LLM client. OpenAI-compatible chat format against native Ollama. Everything is free and local.

Three model slots (env):
  ORCHESTRATOR_MODEL  fast MoE for planning and routine work
  CODER_MODEL         coding model (defaults to the orchestrator model)
  ESCALATION_MODEL    biggest model that fits in RAM; slow but used only when the fast one fails.
                      Unattended runs do not care about latency, so slow-and-smart is fine here.
  REVIEWER_MODEL      vision model
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
                         api_key=os.environ.get("LLM_API_KEY", "ollama"), timeout=3600)
    return _client


def orchestrator_model() -> str: return os.environ["ORCHESTRATOR_MODEL"]
def coder_model() -> str: return os.environ.get("CODER_MODEL") or orchestrator_model()
def escalation_model() -> str: return os.environ.get("ESCALATION_MODEL") or orchestrator_model()
def reviewer_model() -> str: return os.environ.get("REVIEWER_MODEL") or orchestrator_model()


def load_role(repo_root: Path, role: str) -> str:
    return (repo_root / "agents" / f"{role}.md").read_text()


def chat(system: str, user: str, model: str | None = None, json_mode: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = client().chat.completions.create(
        model=model or orchestrator_model(), temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kwargs)
    return resp.choices[0].message.content or ""


def chat_json(system: str, user: str, model: str | None = None) -> dict | list:
    text = chat(system, user, model=model, json_mode=True).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
