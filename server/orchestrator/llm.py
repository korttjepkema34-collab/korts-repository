"""LLM client. OpenAI-compatible chat format. Local by default; free cloud rungs for escalation.

Model slots (env):
  ORCHESTRATOR_MODEL  fast MoE for planning and routine work (local)
  CODER_MODEL         coding model (local CPU); CODER_MODEL_GPU on the gaming PC when online
  ESCALATION_MODEL    biggest local model; the last rung of the escalation ladder
  REVIEWER_MODEL      local vision model

Escalation ladder (docs/24-cloud-escalation.md): ESCALATION_LADDER is a comma-separated list of
provider:model rungs tried in order, e.g.
  ollama:qwen3-coder:480b-cloud,ollama:gpt-oss:120b-cloud,openrouter:qwen/qwen3-coder:free
Providers: ollama (the local daemon; "-cloud" models need `ollama signin`), openrouter
(OPENROUTER_API_KEY), local (same as ollama). A rung that errors (quota, auth, outage, unsupported
request) is cooled down for LADDER_COOLDOWN_S and the next rung is tried; per-provider daily
request caps stop a bad morning from burning the free allowance. The local ESCALATION_MODEL is
always appended, so escalation never fails for lack of a cloud.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI

_clients: dict[str, OpenAI] = {}


def client(slot: str = "default") -> OpenAI:
    """One client per model slot. A slot may point at a different endpoint via
    CODER_BASE_URL / REVIEWER_BASE_URL (e.g. a fine-tuned model served from the gaming PC);
    otherwise every slot shares LLM_BASE_URL."""
    if slot not in _clients:
        default_url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        url = os.environ.get(f"{slot.upper()}_BASE_URL") or default_url
        _clients[slot] = OpenAI(base_url=url, api_key=os.environ.get("LLM_API_KEY", "ollama"), timeout=3600)
    return _clients[slot]


def orchestrator_model() -> str: return os.environ["ORCHESTRATOR_MODEL"]
def coder_model() -> str: return os.environ.get("CODER_MODEL") or orchestrator_model()
def escalation_model() -> str: return os.environ.get("ESCALATION_MODEL") or orchestrator_model()
def reviewer_model() -> str: return os.environ.get("REVIEWER_MODEL") or orchestrator_model()


def slot_for(model: str) -> str:
    """Which endpoint serves a model name: the coder or reviewer slot if it matches that slot's
    model and that slot has its own base URL, else the default."""
    if model == coder_model() and os.environ.get("CODER_BASE_URL"):
        return "coder"
    if model == reviewer_model() and os.environ.get("REVIEWER_BASE_URL"):
        return "reviewer"
    return "default"


# ---- GPU-hosted coder: use the gaming PC's Ollama when it is online; fall back to the CPU MoE ----
_gpu_probe = {"t": 0.0, "ok": False}


def gpu_coder_available() -> bool:
    """CODER_BASE_URL_GPU reachable (cached 60 s)."""
    import time
    import urllib.request
    url = os.environ.get("CODER_BASE_URL_GPU")
    if not url:
        return False
    if time.time() - _gpu_probe["t"] < 60:
        return _gpu_probe["ok"]
    ok = False
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=3) as r:
            ok = r.status == 200
    except Exception:
        ok = False
    _gpu_probe.update(t=time.time(), ok=ok)
    return ok


def coder_route(escalate: bool = False, allow_gpu: bool = True):
    """(model, route, on_gpu). Escalated: the cloud ladder, then the GPU coder, then the local
    escalation model. Not escalated: the GPU coder when reachable, else the local CPU coder.
    `route` exposes .chat.completions.create like a client."""
    if escalate:
        r = escalation_route(include_gpu=allow_gpu)
        return r.model, r, r.on_gpu
    if allow_gpu and gpu_coder_available():
        model = os.environ.get("CODER_MODEL_GPU") or coder_model()
        r = Route([("gpu", model, _gpu_client()), ("local", coder_model(), client(slot_for(coder_model())))], "coder")
        return model, r, True
    r = Route([("local", coder_model(), client(slot_for(coder_model())))], "coder")
    return coder_model(), r, False


def load_role(repo_root: Path, role: str) -> str:
    return (repo_root / "agents" / f"{role}.md").read_text()


def chat(system: str, user: str, model: str | None = None, json_mode: bool = False, escalate: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    if escalate or (model and model == escalation_model()):
        resp = escalation_route(include_gpu=False).chat.completions.create(
            model=escalation_model(), temperature=0.2,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kwargs)
        return resp.choices[0].message.content or ""
    resp = client(slot_for(model or orchestrator_model())).chat.completions.create(
        model=model or orchestrator_model(), temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kwargs)
    return resp.choices[0].message.content or ""


def chat_json(system: str, user: str, model: str | None = None, escalate: bool = False) -> dict | list:
    text = chat(system, user, model=model, json_mode=True, escalate=escalate).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


# ---------------------------------------------------------------- escalation ladder
import time as _time
import json as _json

_cooldown: dict[str, float] = {}
OPENROUTER_URL = "https://openrouter.ai/api/v1"


def _usage_path() -> Path:
    return Path(os.environ.get("REPO_ROOT", ".")) / "reports" / "model_usage.json"


def _usage() -> dict:
    p = _usage_path()
    try:
        d = _json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        d = {}
    day = _time.strftime("%Y-%m-%d")
    if d.get("day") != day:
        d = {"day": day, "counts": {}}
    return d


def record_usage(provider: str, model: str) -> None:
    d = _usage()
    d["counts"][provider] = d["counts"].get(provider, 0) + 1
    d["counts"][f"{provider}:{model}"] = d["counts"].get(f"{provider}:{model}", 0) + 1
    try:
        _usage_path().parent.mkdir(parents=True, exist_ok=True)
        _usage_path().write_text(_json.dumps(d, indent=2))
    except Exception:
        pass


def provider_cap(provider: str) -> int:
    default = {"openrouter": 40, "ollama-cloud": 60}.get(provider, 10 ** 9)
    return int(os.environ.get(f"{provider.upper().replace('-', '_')}_DAILY_CAP", default))


def _provider_of(provider: str, model: str) -> str:
    if provider in ("ollama", "local") and model.endswith("-cloud"):
        return "ollama-cloud"
    return provider


def _client_for(provider: str) -> OpenAI:
    if provider == "openrouter":
        if "openrouter" not in _clients:
            _clients["openrouter"] = OpenAI(base_url=os.environ.get("OPENROUTER_BASE_URL", OPENROUTER_URL),
                                            api_key=os.environ.get("OPENROUTER_API_KEY", "missing"), timeout=600,
                                            default_headers={"HTTP-Referer": "https://github.com/reapers-relics-studio", "X-Title": "Reapers Relics studio"})
        return _clients["openrouter"]
    return client("default")


def parse_ladder(env_key: str = "ESCALATION_LADDER") -> list[tuple[str, str]]:
    rungs: list[tuple[str, str]] = []
    for item in (os.environ.get(env_key, "") or "").split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        provider, model = item.split(":", 1)
        provider = provider.strip().lower()
        if provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
            continue
        rungs.append((provider, model.strip()))
    return rungs


class Route:
    """A model + client pair that falls through a ladder on failure. Exposes
    .chat.completions.create(**kw) so existing call sites keep working; `model` in kw is
    replaced by the active rung's model."""

    def __init__(self, rungs: list[tuple[str, str, OpenAI]], label: str = "route"):
        self.rungs = rungs
        self.i = 0
        self.label = label
        self.chat = type("chat", (), {})()
        self.chat.completions = type("completions", (), {})()
        self.chat.completions.create = self.create
        self.on_gpu = any(p == "gpu" for p, _, _ in rungs)  # hold the VRAM lock if the GPU may be used at all

    @property
    def model(self) -> str:
        return self.rungs[self.i][1] if self.rungs else ""

    @property
    def provider(self) -> str:
        return self.rungs[self.i][0] if self.rungs else ""

    def _usable(self, idx: int) -> bool:
        provider, model, _ = self.rungs[idx]
        key = f"{provider}:{model}"
        if _cooldown.get(key, 0) > _time.time():
            return False
        pv = _provider_of(provider, model)
        if _usage()["counts"].get(pv, 0) >= provider_cap(pv):
            return False
        return True

    def create(self, **kw):
        last: Exception | None = None
        for idx in range(self.i, len(self.rungs)):
            if not self._usable(idx):
                continue
            provider, model, oai = self.rungs[idx]
            self.i = idx
            kw["model"] = model
            try:
                resp = oai.chat.completions.create(**kw)
                record_usage(_provider_of(provider, model), model)
                return resp
            except Exception as e:  # quota, auth, outage, unsupported feature: cool this rung down
                last = e
                _cooldown[f"{provider}:{model}"] = _time.time() + int(os.environ.get("LADDER_COOLDOWN_S", "3600"))
                continue
        raise last or RuntimeError(f"{self.label}: no usable model")

    def describe(self) -> str:
        return " > ".join(f"{p}:{m}" for p, m, _ in self.rungs)


def escalation_route(include_gpu: bool = True) -> Route:
    rungs: list[tuple[str, str, OpenAI]] = [(p, m, _client_for(p)) for p, m in parse_ladder()]
    if include_gpu and gpu_coder_available():
        rungs.append(("gpu", os.environ.get("CODER_MODEL_GPU") or coder_model(), _gpu_client()))
    rungs.append(("local", escalation_model(), client(slot_for(escalation_model()))))
    return Route(rungs, "escalation")


def _gpu_client() -> OpenAI:
    if "gpu" not in _clients:
        _clients["gpu"] = OpenAI(base_url=os.environ["CODER_BASE_URL_GPU"], api_key=os.environ.get("LLM_API_KEY", "ollama"), timeout=3600)
    return _clients["gpu"]


def vision_route() -> Route:
    """Cloud vision rungs (VISION_LADDER) for the judgements that matter most (playtests, proofs),
    falling back to the local reviewer."""
    rungs = [(p, m, _client_for(p)) for p, m in parse_ladder("VISION_LADDER")]
    rungs.append(("local", reviewer_model(), client(slot_for(reviewer_model()))))
    return Route(rungs, "vision")
