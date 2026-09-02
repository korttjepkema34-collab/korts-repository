"""Local audio API for the worker's `music` and `sfx` handlers.

  POST /music {prompt, duration_s, bpm?, lyrics?, seed?}  -> {"files": [...], "model": "..."}
  POST /sfx   {prompt, duration_s, count?, seed?}         -> {"files": [...], "model": "..."}
  POST /unload                                            -> frees VRAM

Run on the gaming PC (later the server) in its own venv:
  pip install fastapi uvicorn torch soundfile
  pip install acestep            # ACE-Step 1.5, see github.com/ace-step/ACE-Step-1.5
  pip install stable-audio-tools # Stable Audio Open, see github.com/Stability-AI/stable-audio-tools
  uvicorn audio_api:app --host 127.0.0.1 --port 8190

Only one model is resident at a time (12 GB VRAM). Each endpoint lazily loads its model and
unloads the other. The exact ACE-Step / stable-audio-tools call signatures move between
releases; the two `_generate_*` functions are the only places to touch if they do. Until they are
verified on real installs, treat this file as a scaffold: it starts, serves /health, and returns
a clear error if a backend import fails.
"""
from __future__ import annotations

import gc
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="studio audio api")
OUT = Path(os.environ.get("AUDIO_OUT_DIR", tempfile.gettempdir())) / "studio-audio"
OUT.mkdir(parents=True, exist_ok=True)

_loaded: dict = {"name": None, "obj": None}


class MusicReq(BaseModel):
    prompt: str
    duration_s: int = 60
    bpm: Optional[int] = None
    lyrics: Optional[str] = None
    seed: Optional[int] = None
    count: int = 2


class SfxReq(BaseModel):
    prompt: str
    duration_s: float = 1.5
    count: int = 3
    seed: Optional[int] = None


def _unload() -> None:
    _loaded["obj"] = None
    _loaded["name"] = None
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def _load(name: str):
    if _loaded["name"] == name:
        return _loaded["obj"]
    _unload()
    if name == "acestep":
        try:
            from acestep.pipeline_ace_step import ACEStepPipeline  # noqa
        except ImportError as e:
            raise HTTPException(500, f"ACE-Step not installed: {e}")
        obj = ACEStepPipeline(dtype="bfloat16", torch_compile=False)
    elif name == "stable-audio":
        try:
            from stable_audio_tools import get_pretrained_model  # noqa
        except ImportError as e:
            raise HTTPException(500, f"stable-audio-tools not installed: {e}")
        model, cfg = get_pretrained_model("stabilityai/stable-audio-open-1.0")
        obj = (model.to("cuda"), cfg)
    else:
        raise HTTPException(400, f"unknown backend {name}")
    _loaded.update(name=name, obj=obj)
    return obj


def _generate_music(req: MusicReq, i: int) -> str:
    pipe = _load("acestep")
    out = OUT / f"music-{int(time.time())}-{i}.wav"
    tags = req.prompt + (f", {req.bpm} bpm" if req.bpm else "")
    # ACE-Step pipeline call; adjust kwargs to the installed version's signature.
    pipe(prompt=tags, lyrics=req.lyrics or "[inst]", audio_duration=req.duration_s,
         manual_seeds=str(req.seed + i) if req.seed is not None else None, save_path=str(out))
    return str(out)


def _generate_sfx(req: SfxReq, i: int) -> str:
    import torch
    import soundfile as sf
    from stable_audio_tools.inference.generation import generate_diffusion_cond
    model, cfg = _load("stable-audio")
    sr = cfg["sample_rate"]
    if req.seed is not None:
        torch.manual_seed(req.seed + i)
    cond = [{"prompt": req.prompt, "seconds_start": 0, "seconds_total": req.duration_s}]
    audio = generate_diffusion_cond(model, steps=100, cfg_scale=7, conditioning=cond,
                                    sample_size=int(sr * req.duration_s), device="cuda")
    audio = audio.squeeze(0).T.float().cpu().numpy()
    out = OUT / f"sfx-{int(time.time())}-{i}.wav"
    sf.write(out, audio, sr)
    return str(out)


@app.get("/health")
def health():
    return {"ok": True, "loaded": _loaded["name"]}


@app.post("/music")
def music(req: MusicReq):
    files = [_generate_music(req, i) for i in range(max(1, req.count))]
    return {"files": files, "model": "ace-step-1.5", "loop_points": None}


@app.post("/sfx")
def sfx(req: SfxReq):
    files = [_generate_sfx(req, i) for i in range(max(1, req.count))]
    return {"files": files, "model": "stable-audio-open-1.0"}


@app.post("/unload")
def unload():
    _unload()
    return {"ok": True}
