import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from assistant.web import Handler


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "ASSISTANT_HOME": self.tmp.name,
            "ASSISTANT_ALLOWED_ORIGINS": "http://dashboard.test",
            "ASSISTANT_SOURCE_REVISION": "test-revision",
        }, clear=False)
        self.env.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.env.stop()
        self.tmp.cleanup()

    def request(self, path, method="GET", data=None, origin=None):
        body = json.dumps(data).encode() if data is not None else None
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        request = urllib.request.Request(self.base + path, data=body, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as exc:
            response = exc
        return response.status, dict(response.headers), json.loads(response.read())

    def test_task_uses_canonical_store_and_hides_private_data(self):
        status, _, created = self.request("/api/tasks", "POST", {
            "project": "game", "subproject": "reapers-relics", "goal": "Prepare a safe draft"
        })
        self.assertEqual(201, status)
        self.assertEqual("planned", created["task"]["status"])
        self.assertNotIn("data", created["task"])
        status, _, listing = self.request("/api/tasks?project=game")
        self.assertEqual(200, status)
        self.assertEqual(created["task"]["id"], listing["tasks"][0]["id"])
        self.assertTrue((Path(self.tmp.name) / "state.sqlite").exists())

    def test_scope_and_origin_validation(self):
        status, _, result = self.request("/api/tasks", "POST", {
            "project": "wrong", "goal": "bad"
        })
        self.assertEqual(400, status)
        status, _, result = self.request("/api/health", origin="http://evil.test")
        self.assertEqual(403, status)
        status, headers, result = self.request("/api/health", origin="http://dashboard.test")
        self.assertEqual(200, status)
        self.assertEqual("http://dashboard.test", headers["Access-Control-Allow-Origin"])

    def test_search_returns_bounded_projection(self):
        vault = Path(self.tmp.name) / "vault" / "personal"
        vault.mkdir(parents=True)
        (vault / "note.md").write_text("private project telescope notes", encoding="utf-8")
        from assistant.core import Store
        store = Store()
        store.index(Path(self.tmp.name) / "vault")
        store.close()
        status, _, result = self.request("/api/search?project=personal&q=telescope")
        self.assertEqual(200, status)
        self.assertEqual(1, len(result["results"]))
        self.assertNotIn("digest", result["results"][0])

    @patch("assistant.web.ollama_models")
    def test_workforce_is_project_scoped_and_sanitized(self, models):
        models.side_effect = lambda endpoint: ["qwen3.5:9b"] if endpoint.endswith("11435") else []
        workers = {
            "game-coder": {"name": "Game engineer", "description": "Builds game candidates",
                           "projects": ["game"], "adapter": "code-sandbox",
                           "endpoint": "http://127.0.0.1:11435", "model": "qwen3.5:9b",
                           "instructions": "private instructions"},
            "personal-helper": {"name": "Personal helper", "projects": ["personal"],
                                "adapter": "ollama-draft", "endpoint": "http://127.0.0.1:11434",
                                "model": "qwen3.5:4b"},
        }
        Path(self.tmp.name, "workers.json").write_text(json.dumps(workers), encoding="utf-8")
        status, _, result = self.request("/api/workforce?project=game")
        self.assertEqual(200, status)
        self.assertEqual(["game-coder"], [agent["id"] for agent in result["agents"]])
        self.assertEqual("idle", result["agents"][0]["state"])
        self.assertNotIn("instructions", result["agents"][0])
        self.assertEqual("online", result["machines"][2]["state"])


if __name__ == "__main__":
    unittest.main()
