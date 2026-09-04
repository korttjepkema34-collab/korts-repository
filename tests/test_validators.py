"""The studio's own gate: these must pass before any change to server/, worker/ or shared/ merges."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_level_validator_accepts_the_keep():
    from orchestrator import levels
    m = json.loads((ROOT / "game/data/maps/keep.json").read_text())
    assert levels.validate(ROOT, "keep", m["rows"], 30, 17, ["PlayerSpawn", "Exit", "NpcSpawn"]) == []


def test_level_validator_catches_split_and_open_edges():
    from orchestrator import levels
    split = ["WWWWWWWWWW", "WP..W...XW", "W...W....W", "WWWWWWWWWW"]
    errs = levels.validate(ROOT, "test_split", split, 10, 4, ["PlayerSpawn", "Exit"])
    assert any("not reachable" in e for e in errs)
    open_edge = ["..........", ".P........", "..........", ".........."]
    assert any("Exit" in e for e in levels.validate(ROOT, "test_edge", open_edge, 10, 4, ["PlayerSpawn"]))


def test_writer_validator_voice_rules():
    from orchestrator import writer
    assert writer.validate("dialogue", {"hesper": [{"id": "a", "text": "Sit. The lamps are failing.", "when": "x"}]}, 90) == []
    errs = writer.validate("dialogue", {"hesper": [{"id": "a", "text": "Welcome, hero! The wizard waits.", "when": "x"}]}, 90)
    assert any("exclamation" in e for e in errs) and any("wizard" in e for e in errs)


def test_planner_templates_fill_mechanics():
    from orchestrator import planner
    rj = {"kind": "image", "role": "artist-2d", "spec": {"asset_type": "character", "prompt": "the Reaper"}, "output_dir": "x"}
    planner.normalize_job(ROOT, rj)
    s = rj["spec"]
    assert s["workflow"] == "character_sheet" and s["postprocess"]["final_width"] == 96 and "pixel art" in s["prompt"]
    cj = {"kind": "code", "role": "coder", "spec": {"goal": "g", "scene": "res://x.tscn", "acceptance": ["a"]}}
    planner.normalize_job(ROOT, cj)
    assert cj["spec"]["proof"]["scene"] == "res://x.tscn" and any("feedback" in a for a in cj["spec"]["acceptance"])
    lj = {"kind": "level", "role": "coder", "spec": {"name": "fallows", "goal": "x"}}
    planner.normalize_job(ROOT, lj)
    assert lj["role"] == "level-designer" and "PlayerSpawn" in lj["spec"]["markers_required"]


def test_reviewer_rubric_rule(monkeypatch):
    from orchestrator import reviewer, llm

    class R:
        def __init__(self, content):
            self.choices = [type("c", (), {"message": type("m", (), {"content": content})()})()]

    def fake_client(content):
        c = type("cl", (), {})(); c.chat = type("ch", (), {})(); c.chat.completions = type("co", (), {})()
        c.chat.completions.create = lambda **k: R(content)
        return c
    good = json.dumps({"answers": {k: (v) for k, _, v in reviewer.RUBRIC}})
    monkeypatch.setattr(reviewer.llm, "client", lambda slot="default": fake_client(good))
    assert reviewer._ask("s", [], "m")[0] == "approved"
    bad = json.dumps({"answers": {**{k: v for k, _, v in reviewer.RUBRIC}, "has_text_or_watermark": True}})
    monkeypatch.setattr(reviewer.llm, "client", lambda slot="default": fake_client(bad))
    assert reviewer._ask("s", [], "m")[0] == "rejected"
    monkeypatch.setattr(reviewer.llm, "client", lambda slot="default": fake_client("not json"))
    assert reviewer._ask("s", [], "m")[0] == "rejected"


def test_image_checks(tmp_path):
    from PIL import Image
    from orchestrator import checks
    good = tmp_path / "g.png"; Image.new("RGBA", (32, 48), (58, 42, 34, 255)).save(good)
    bad = tmp_path / "b.png"; Image.new("RGBA", (32, 48), (123, 99, 200, 255)).save(bad)
    assert checks.check_image(ROOT, good, {"final_width": 32, "final_height": 48})[0]
    assert not checks.check_image(ROOT, bad, {})[0]
    assert not checks.check_image(ROOT, good, {"final_width": 16, "final_height": 16})[0]


def test_failure_signature_and_escalation(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_ROOT", str(tmp_path)); (tmp_path / "tasks").mkdir()
    import importlib
    from orchestrator import main as m
    from orchestrator.state import State
    st = State(tmp_path)
    msg = "SCRIPT ERROR: Invalid call. Nonexistent function 'set_cellv' in base 'TileMapLayer'.\n at: res://x.gd:42"
    assert "set_cellv" in m.failure_signature(msg)
    for _ in range(3):
        m.note_failure(st, msg)
    assert m.should_escalate(st)


def test_generated_items_consistent():
    w = json.loads((ROOT / "game/data/weapons.json").read_text()); c = json.loads((ROOT / "game/data/classes.json").read_text())
    ids = {x["id"] for x in w}
    assert len(w) == 25 and len(ids) == 25 and all(cl["starting_weapon"] in ids for cl in c)


def test_postprocess_palette(tmp_path):
    from PIL import Image
    import postprocess
    im = Image.new("RGBA", (64, 64), (200, 200, 210, 255))
    for x in range(16, 48):
        for y in range(16, 48):
            im.putpixel((x, y), (60, 45, 35, 255))
    p = tmp_path / "t.png"; im.save(p)
    out = Image.open(postprocess.process(p, ROOT, {"palette": True, "downscale": 4, "transparent_bg": True}))
    pal = set(postprocess.load_palette(ROOT))
    px = list(out.getdata())
    assert out.size == (16, 16) and px[0][3] == 0 and all(c[:3] in pal for c in px if c[3] > 0)


def test_queue_round_trip_with_fakeredis():
    try:
        import fakeredis
    except ImportError:
        import pytest; pytest.skip("fakeredis not installed")
    from shared import queue as q
    from shared.jobs import Job, JobKind, Role, Result, ResultStatus, make_job_id
    r = fakeredis.FakeRedis(decode_responses=True)
    job = Job(id=make_job_id("000", "s"), task_id="000", kind=JobKind.STUB, role=Role.ORCHESTRATOR, spec={}, output_dir="assets/incoming/x")
    q.enqueue(r, job)
    got = q.claim(r, [JobKind.STUB], timeout_s=1)
    assert got.id == job.id and r.llen(got.processing_key) == 1
    q.complete(r, got, Result(job_id=got.id, status=ResultStatus.OK, worker="t", started_at="x"))
    assert r.llen(got.processing_key) == 0 and q.next_result(r, 1).job_id == job.id
