"""Small HTTP adapter for the canonical assistant runtime.

The browser receives a deliberately narrow projection. Private task data, prompts,
artifacts, credentials, and filesystem paths are never returned by this module.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import PROJECTS, Store, runtime_root, validate_subproject

REPO = Path(__file__).resolve().parents[1]
MAX_BODY = 64 * 1024


def now():
    return datetime.now(timezone.utc).isoformat()


def source_revision():
    configured = os.environ.get("ASSISTANT_SOURCE_REVISION", "").strip()
    if configured:
        return configured
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True,
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def public_task(task):
    return {
        "id": task["id"], "project": task["project"],
        "subproject": task.get("subproject", ""), "goal": task["goal"],
        "status": task["status"], "updated": task["updated"],
    }


def setup_state():
    config_path = runtime_root() / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = {}
    model_dir = Path(os.environ.get("ASSISTANT_MODEL_DIR", "/srv/models"))
    models = sorted(p.name for p in model_dir.glob("*.gguf")) if model_dir.is_dir() else []
    return {
        "initialized": config_path.exists(),
        "cloud_only_leadership": config.get("cloud_only_leadership") is True,
        "paid_inference_allowed": config.get("paid_inference_allowed", False),
        "openrouter_configured": bool(os.environ.get("OPENROUTER_API_KEY")),
        "local_models": models,
        "local_model_count": len(models),
        "projects": list(PROJECTS),
        "source_revision": source_revision(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "KortAssistantWeb/0.1"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def allowed_origin(self):
        origin = self.headers.get("Origin", "")
        configured = {
            value.strip() for value in os.environ.get("ASSISTANT_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        return origin if origin and origin in configured else ""

    def cors(self):
        origin = self.allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def respond(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def reject_bad_origin(self):
        origin = self.headers.get("Origin", "")
        if origin and not self.allowed_origin():
            self.respond({"ok": False, "error": "origin not allowed"}, HTTPStatus.FORBIDDEN)
            return True
        return False

    def do_OPTIONS(self):
        if self.reject_bad_origin():
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.reject_bad_origin():
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/health":
            self.respond({"ok": True, "service": "my-assistant", "time": now(),
                          "source_revision": source_revision()})
            return
        if parsed.path == "/api/setup":
            self.respond({"ok": True, **setup_state()})
            return
        if parsed.path == "/api/tasks":
            project = query.get("project", [""])[0]
            if project and project not in PROJECTS:
                self.respond({"ok": False, "error": "unknown project"}, HTTPStatus.BAD_REQUEST)
                return
            store = Store()
            try:
                tasks = [public_task(t) for t in store.list() if not project or t["project"] == project]
            finally:
                store.close()
            self.respond({"ok": True, "tasks": tasks})
            return
        if parsed.path == "/api/search":
            project = query.get("project", [""])[0]
            text = query.get("q", [""])[0]
            subproject = query.get("subproject", [""])[0]
            try:
                if project not in PROJECTS:
                    raise ValueError("unknown project")
                store = Store()
                try:
                    hits = store.search(project, text, subproject=subproject)
                finally:
                    store.close()
                safe = [{key: hit[key] for key in ("path", "scope", "subproject", "status", "kind", "body")}
                        for hit in hits]
                self.respond({"ok": True, "results": safe})
            except ValueError as exc:
                self.respond({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self.respond({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.reject_bad_origin():
            return
        if urlparse(self.path).path != "/api/tasks":
            self.respond({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("invalid request size")
            data = json.loads(self.rfile.read(length))
            project = str(data.get("project", "")).strip()
            goal = str(data.get("goal", "")).strip()
            subproject = validate_subproject(data.get("subproject", ""))
            store = Store()
            try:
                task_id = store.create(project, goal, subproject)
                task = public_task(store.get(task_id))
            finally:
                store.close()
            self.respond({"ok": True, "task": task}, HTTPStatus.CREATED)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.respond({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main():
    host = os.environ.get("ASSISTANT_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("ASSISTANT_WEB_PORT", "8772"))
    Store().close()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"My Assistant web adapter listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
