"""Escalation ladder: falls through on errors, respects cooldowns and daily caps, never strands."""
import json
import time


class _Resp:
    def __init__(self, text):
        self.choices = [type("c", (), {"message": type("m", (), {"content": text})()})()]


class _Client:
    def __init__(self, name, fail=None):
        self.name, self.fail, self.calls = name, fail, 0
        self.chat = type("ch", (), {})(); self.chat.completions = type("co", (), {})()
        self.chat.completions.create = self._create

    def _create(self, **kw):
        self.calls += 1
        if self.fail:
            raise self.fail
        return _Resp(f"{self.name}:{kw['model']}")


def test_route_falls_through_and_cools_down(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path)); (tmp_path / "reports").mkdir()
    from orchestrator import llm
    llm._cooldown.clear()
    cloud = _Client("cloud", fail=RuntimeError("429 quota"))
    local = _Client("local")
    r = llm.Route([("openrouter", "x/y:free", cloud), ("local", "gpt-oss:120b", local)], "t")
    out = r.chat.completions.create(model="ignored", messages=[])
    assert out.choices[0].message.content == "local:gpt-oss:120b"
    assert cloud.calls == 1 and llm._cooldown["openrouter:x/y:free"] > time.time()
    r.chat.completions.create(model="ignored", messages=[])
    assert cloud.calls == 1  # cooled down: not retried
    usage = json.loads((tmp_path / "reports" / "model_usage.json").read_text())
    assert usage["counts"]["local"] == 2


def test_daily_cap_skips_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path)); (tmp_path / "reports").mkdir()
    monkeypatch.setenv("OPENROUTER_DAILY_CAP", "1")
    from orchestrator import llm
    llm._cooldown.clear()
    cloud, local = _Client("cloud"), _Client("local")
    r = llm.Route([("openrouter", "x/y:free", cloud), ("local", "big", local)], "t")
    assert r.chat.completions.create(messages=[]).choices[0].message.content == "cloud:x/y:free"
    assert r.chat.completions.create(messages=[]).choices[0].message.content == "local:big"
    assert cloud.calls == 1


def test_parse_ladder_skips_openrouter_without_key(monkeypatch):
    from orchestrator import llm
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ESCALATION_LADDER", "ollama:qwen3-coder:480b-cloud, openrouter:qwen/qwen3-coder:free ,local:gpt-oss:120b")
    assert llm.parse_ladder() == [("ollama", "qwen3-coder:480b-cloud"), ("local", "gpt-oss:120b")]
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    assert ("openrouter", "qwen/qwen3-coder:free") in llm.parse_ladder()


def test_all_rungs_failing_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path)); (tmp_path / "reports").mkdir()
    from orchestrator import llm
    llm._cooldown.clear()
    r = llm.Route([("local", "a", _Client("a", fail=RuntimeError("down")))], "t")
    import pytest
    with pytest.raises(RuntimeError):
        r.chat.completions.create(messages=[])
