"""LLM client. Speaks the OpenAI-compatible chat format so it works against Ollama locally and
against a paid provider for escalation with only an env change (LLM_BASE_URL, LLM_API_KEY)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
            api_key=os.environ.get("LLM_API_KEY", "ollama"),
        )
    return _client


def load_role(repo_root: Path, role: str) -> str:
    return (repo_root / "agents" / f"{role}.md").read_text()


def chat(system: str, user: str, model: str | None = None, json_mode: bool = False) -> str:
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client().chat.completions.create(
        model=model or os.environ["ORCHESTRATOR_MODEL"],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def chat_json(system: str, user: str, model: str | None = None) -> dict | list:
    text = chat(system, user, model=model, json_mode=True)
    # Models sometimes wrap JSON in fences despite json mode.
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)
