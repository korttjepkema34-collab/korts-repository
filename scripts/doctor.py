#!/usr/bin/env python3
"""Preflight check. Run it, fix what it names, run it again until it says READY.

  server (from the repo root):   .\\studio.ps1 scripts\\doctor.py
  gaming PC:                     worker\\.venv\\Scripts\\python.exe scripts\\doctor.py --gpu

Prints PASS / WARN / FAIL per item with the exact fix. WARN never blocks a first run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "server")]
RESULTS: list[tuple[str, str, str]] = []


def rec(level: str, what: str, fix: str = "") -> None:
    RESULTS.append((level, what, fix))


def http_json(url: str, timeout: float = 4.0):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def load_env() -> dict:
    env = ROOT / "server" / ".env"
    if not env.exists():
        rec("FAIL", "server/.env missing", "copy server\\.env.example to server\\.env and fill it in")
        return {}
    d = {}
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = re.split(r"\s+#", v, 1)[0].strip()
            os.environ.setdefault(k.strip(), d[k.strip()])
    for k, bad in (("SERVER_TS_IP", "100.x"), ("REDIS_PASSWORD", "change-me"), ("GPU_MAC", "AA:BB")):
        if d.get(k, "").startswith(bad) or not d.get(k):
            rec("FAIL", f"server/.env {k} is still the placeholder", f"set {k} in server\\.env")
    return d


def check_ollama(env: dict, key: str, label: str, required: bool = True, base_key: str = "LLM_BASE_URL") -> None:
    base = env.get(base_key, "http://127.0.0.1:11434/v1").rstrip("/")
    host = base[:-3] if base.endswith("/v1") else base
    model = env.get(key, "")
    if not model:
        rec("WARN" if not required else "FAIL", f"{label}: {key} not set in server/.env", f"set {key}")
        return
    try:
        tags = http_json(host + "/api/tags")
        names = {m["name"] for m in tags.get("models", [])}
    except Exception as e:
        rec("FAIL", f"Ollama not reachable at {host} ({e})", "install Ollama, set OLLAMA_HOST, start it")
        return
    ok = model in names or (model + ":latest") in names
    rec("PASS" if ok else ("FAIL" if required else "WARN"), f"{label}: {model} {'present' if ok else 'not pulled'}", "" if ok else f"ollama pull {model}")


def check_server() -> None:
    env = load_env()
    for k, label, req in (("ORCHESTRATOR_MODEL", "orchestrator model", True), ("CODER_MODEL", "coder model", True),
                          ("REVIEWER_MODEL", "reviewer (vision) model", True), ("ESCALATION_MODEL", "escalation model", False)):
        check_ollama(env, k, label, req)
    try:
        from shared import queue as q
        r = q.connect(); r.ping()
        rec("PASS", "Redis reachable")
        hb = r.exists("worker:%s:heartbeat" % env.get("GPU_WORKER_NAME", "gpu"))
        status = r.get("worker:%s:status" % env.get("GPU_WORKER_NAME", "gpu"))
        rec("PASS" if hb else "WARN", f"GPU worker {'online (' + str(status) + ')' if hb else 'not online right now'}", "" if hb else "start worker\\run.ps1 on the gaming PC (or leave it; jobs wait)")
    except Exception as e:
        rec("FAIL", f"Redis not reachable ({e})", "cd server; docker compose up -d   (and check REDIS_PASSWORD / REDIS_HOST)")
    gb = env.get("GODOT_BIN", "")
    if gb and Path(gb).exists():
        import subprocess
        try:
            v = subprocess.run([gb, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
            rec("PASS", f"Godot found: {v}")
        except Exception as e:
            rec("FAIL", f"Godot at GODOT_BIN does not run ({e})", "reinstall Godot 4 and fix GODOT_BIN")
    else:
        rec("FAIL", "GODOT_BIN not set or file missing", "install Godot 4 and set GODOT_BIN in server\\.env")
    rec("PASS" if (ROOT / "game" / "addons" / "gdUnit4").exists() else "WARN", "gdUnit4 installed" if (ROOT / "game" / "addons" / "gdUnit4").exists() else "gdUnit4 missing (gate falls back to a load check)", "scripts\\install_gdunit4.ps1")
    n = len(list((ROOT / "server" / "godot-docs").rglob("*.xml"))) if (ROOT / "server" / "godot-docs").exists() else 0
    rec("PASS" if n else "WARN", f"engine class reference dump: {n} classes" if n else "engine class reference not dumped (coder loses search_godot_api)", "" if n else "scripts\\dump_godot_docs.ps1")
    rag = ROOT / "data" / "rag" / "index.json"
    rec("PASS" if rag.exists() else "WARN", "retrieval index built" if rag.exists() else "retrieval index missing (coder loses search_docs)", "" if rag.exists() else ".\\studio.ps1 scripts\\fetch_godot_docs.py  then  .\\studio.ps1 scripts\\build_rag_index.py")
    for mod, pipname in (("PIL", "pillow"), ("openai", "openai"), ("redis", "redis"), ("pydantic", "pydantic"), ("yaml", "pyyaml")):
        try:
            __import__(mod); rec("PASS", f"python package {pipname}")
        except ImportError:
            rec("FAIL", f"python package {pipname} missing", "pip install -r server\\orchestrator\\requirements.txt")
    rec("PASS" if shutil.which("gdlint") else "WARN", "gdtoolkit (gdlint) on PATH" if shutil.which("gdlint") else "gdtoolkit not on PATH (lint step skipped)", "" if shutil.which("gdlint") else "pip install gdtoolkit  (in the server venv)")
    free = shutil.disk_usage(ROOT).free / 1e9
    rec("PASS" if free > float(env.get("MIN_FREE_GB", 20)) else "FAIL", f"disk free {free:.0f} GB", "free space; the loop pauses below MIN_FREE_GB")
    backlog = list((ROOT / "tasks" / "backlog").glob("*.md"))
    rec("PASS" if backlog else "WARN", f"{len(backlog)} tasks in backlog", "" if backlog else "the orchestrator will generate tasks; fine")
    gpu_url = env.get("CODER_BASE_URL_GPU", "")
    if gpu_url:
        try:
            http_json(gpu_url.rstrip("/") + "/models"); rec("PASS", "GPU coder endpoint reachable")
        except Exception:
            rec("WARN", "GPU coder endpoint not reachable right now (falls back to CPU)", "start Ollama on the gaming PC with OLLAMA_HOST=0.0.0.0:11434")
    else:
        rec("WARN", "CODER_BASE_URL_GPU not set: code jobs stay on the CPU model", "optional: ollama pull qwen3.6:27b on the gaming PC and set CODER_BASE_URL_GPU")
    if not (ROOT / "style" / "references" / "palette.png").exists():
        rec("FAIL", "style/references/palette.png missing", "git checkout -- style/references")


def check_gpu() -> None:
    cfg_path = ROOT / "worker" / "config.yaml"
    if not cfg_path.exists():
        rec("FAIL", "worker/config.yaml missing", "copy worker\\config.example.yaml to worker\\config.yaml and edit it"); return
    import yaml
    cfg = yaml.safe_load(cfg_path.read_text())
    if str(cfg.get("redis", {}).get("host", "")).startswith("100.x") or str(cfg.get("redis", {}).get("password", "")).startswith("change-me"):
        rec("FAIL", "worker/config.yaml still has placeholders", "set redis.host to the server's Tailscale IP and the password")
    os.environ.setdefault("REDIS_HOST", str(cfg.get("redis", {}).get("host", "")))
    os.environ.setdefault("REDIS_PORT", str(cfg.get("redis", {}).get("port", 6379)))
    os.environ.setdefault("REDIS_PASSWORD", str(cfg.get("redis", {}).get("password", "")))
    try:
        from shared import queue as q
        q.connect().ping(); rec("PASS", "Redis on the server reachable over Tailscale")
    except Exception as e:
        rec("FAIL", f"cannot reach the server's Redis ({e})", "check Tailscale is up on both machines and the ACL allows 6379")
    comfy = cfg.get("tools", {}).get("comfyui", "http://127.0.0.1:8188").rstrip("/")
    try:
        http_json(comfy + "/system_stats"); rec("PASS", f"ComfyUI reachable at {comfy}")
        try:
            info = http_json(comfy + "/object_info/CheckpointLoaderSimple")
            ckpts = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
            want = json.loads((ROOT / "worker" / "workflows" / "default.json").read_text())["1"]["inputs"]["ckpt_name"]
            rec("PASS" if want in ckpts else "FAIL", f"checkpoint {want} {'present' if want in ckpts else 'missing'}", "" if want in ckpts else "scripts\\bootstrap_gpu.ps1 downloads it, or edit ckpt_name in worker\\workflows\\*.json")
            info = http_json(comfy + "/object_info/LoraLoader")
            loras = info["LoraLoader"]["input"]["required"]["lora_name"][0]
            wl = json.loads((ROOT / "worker" / "workflows" / "tileset.json").read_text())["10"]["inputs"]["lora_name"]
            rec("PASS" if wl in loras else "WARN", f"pixel-art LoRA {wl} {'present' if wl in loras else 'missing (tileset/character workflows will fail)'}", "" if wl in loras else "scripts\\bootstrap_gpu.ps1 downloads it")
            nodes = http_json(comfy + "/object_info")
            has_ip = "IPAdapterUnifiedLoader" in nodes
            rec("PASS" if has_ip else "WARN", "IP-Adapter nodes installed" if has_ip else "IP-Adapter node pack missing (character_sheet workflow will fail)", "" if has_ip else "scripts\\bootstrap_gpu.ps1 installs ComfyUI_IPAdapter_plus")
        except Exception as e:
            rec("WARN", f"could not inspect ComfyUI models ({e})", "")
    except Exception:
        rec("FAIL", f"ComfyUI not reachable at {comfy}", "scripts\\bootstrap_gpu.ps1, then start run-comfyui.ps1")
    audio = cfg.get("tools", {}).get("acestep", "http://127.0.0.1:8190").rstrip("/")
    try:
        http_json(audio + "/health"); rec("PASS", "audio API reachable")
    except Exception:
        rec("WARN", "audio API not running (audio tasks defer; fine for the prototype)", "worker\\services\\run-audio-api.ps1 when you want audio")
    for mod, pipname in (("PIL", "pillow"), ("redis", "redis"), ("pydantic", "pydantic"), ("requests", "requests"), ("yaml", "pyyaml")):
        try:
            __import__(mod); rec("PASS", f"python package {pipname}")
        except ImportError:
            rec("FAIL", f"python package {pipname} missing", "pip install -r worker\\requirements.txt")
    rec("PASS" if not (ROOT / "worker" / "GAMING_MODE").exists() else "WARN", "gaming mode off" if not (ROOT / "worker" / "GAMING_MODE").exists() else "gaming mode is ON: the worker will not pull jobs", "")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--gpu", action="store_true", help="run the gaming-PC checks instead of the server checks")
    a = ap.parse_args()
    (check_gpu if a.gpu else check_server)()
    width = max(len(w) for _, w, _ in RESULTS) + 2
    for level, what, fix in RESULTS:
        print(f"{level:4} {what:<{width}} {('-> ' + fix) if fix and level != 'PASS' else ''}")
    fails = [r for r in RESULTS if r[0] == "FAIL"]; warns = [r for r in RESULTS if r[0] == "WARN"]
    print()
    if fails:
        print(f"NOT READY: {len(fails)} item(s) to fix above, {len(warns)} optional.")
        return 1
    print(f"READY on this machine ({len(warns)} optional item(s) skipped). Next: START-HERE.md step by step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
