"""LLM-facing planning: task -> jobs, and empty backlog -> new tasks from the design doc."""
from __future__ import annotations

import re
import time
from pathlib import Path

from shared.jobs import Job, JobKind, make_job_id

from . import llm

MAX_JOBS_PER_TASK = 8


def _ctx(repo: Path, *rel: str) -> str:
    parts = []
    for r in rel:
        p = repo / r
        if p.exists():
            parts.append(f"## {r}\n" + p.read_text())
    return "\n\n".join(parts)


def plan_jobs(repo: Path, task_path: Path, escalate: bool = False) -> list[Job]:
    system = llm.load_role(repo, "orchestrator")
    user = "\n\n".join([
        "## Task\n" + task_path.read_text(),
        _ctx(repo, "style/style-bible.md", "docs/14-world-bible.md", "docs/08-job-schema.md", "docs/10-game-design.md"),
        "Existing approved assets:\n" + "\n".join(str(p.relative_to(repo)) for p in (repo / "assets" / "approved").rglob("*") if p.is_file())[:4000],
        "Respond with JSON: {\"jobs\": [ ... ]}. Each job: kind (stub|image|music|sfx|code), "
        "role, spec (object), output_dir (under assets/incoming/<task-id>-<slug>/ for assets, or "
        "\"game\" for code), slug (short). For code jobs, spec.goal is the instruction to the coder "
        f"and spec.acceptance is a checklist. At most {MAX_JOBS_PER_TASK} jobs. Prefer few, small jobs. "
        "Optional keys: \"decisions\": [strings] for any choice you made on the owner's behalf "
        "(logged automatically), and \"style_bible\": full replacement text for style/style-bible.md "
        "when the task asks you to fill it in.",
    ])
    task_id = task_path.stem.split("-")[0]
    model = llm.escalation_model() if escalate else None
    data = llm.chat_json(system, user, model=model)
    for attempt in range(2):
        try:
            return _jobs_from_plan(repo, task_path, task_id, data)
        except Exception as e:  # validation repair loop: show the model its own error once
            if attempt == 1:
                raise
            data = llm.chat_json(system, user + f"\n\nYour previous plan failed validation: {e}\n"
                                 "Return the corrected JSON only.", model=model)
    return []


def _jobs_from_plan(repo: Path, task_path: Path, task_id: str, data) -> list[Job]:
    raw = data["jobs"] if isinstance(data, dict) else data
    if not isinstance(raw, list) or not raw:
        raise ValueError("plan has no jobs list")
    if isinstance(data, dict):
        record_side_effects(repo, task_path, data)
    jobs: list[Job] = []
    for rj in raw[:MAX_JOBS_PER_TASK]:
        if not isinstance(rj, dict):
            raise ValueError("job entries must be objects")
        slug = re.sub(r"[^a-z0-9]+", "-", str(rj.pop("slug", "job")).lower()).strip("-")[:30] or "job"
        for k in ("id", "task_id", "created_at", "attempt"):
            rj.pop(k, None)
        rj.setdefault("output_dir", f"assets/incoming/{task_id}-{slug}")
        normalize_job(repo, rj)
        jobs.append(Job(id=make_job_id(task_id, slug), task_id=task_id, **rj))
    return jobs


# Fill-in-the-blank templates: the planner names the asset type and subject; the mechanics
# (workflow, sizes, postprocess, references, acceptance boilerplate) come from here.
ASSET_TYPES = {
    "character": {"workflow": "character_sheet", "width": 1024, "height": 512, "downscale": 8, "final": (96, 48), "transparent_bg": True, "normal_map": True},
    "sheet":     {"workflow": "character_sheet", "width": 1024, "height": 1024, "downscale": 8, "final": (128, 128), "transparent_bg": True, "normal_map": True},
    "tile":      {"workflow": "tileset", "width": 1024, "height": 256, "downscale": 8, "final": (128, 32), "transparent_bg": False, "normal_map": True},
    "prop":      {"workflow": "tileset", "width": 512, "height": 512, "downscale": 8, "final": (64, 64), "transparent_bg": True, "normal_map": True},
    "building":  {"workflow": "tileset", "width": 1024, "height": 1024, "downscale": 4, "final": (256, 256), "transparent_bg": True, "normal_map": True},
    "background": {"workflow": "default", "width": 1920, "height": 1080, "downscale": 2, "final": (960, 540), "transparent_bg": False, "normal_map": False},
    "ui":        {"workflow": "tileset", "width": 512, "height": 512, "downscale": 8, "final": (64, 64), "transparent_bg": True, "normal_map": False},
    "icon":      {"workflow": "tileset", "width": 256, "height": 256, "downscale": 16, "final": (16, 16), "transparent_bg": True, "normal_map": False},
}
POSITIVE_SUFFIX = ("pixel art, 32px tiles, three-quarter top-down RPG, 16 colour limited palette, 1px dark outline, "
                   "flat 3-tone shading, no anti-aliasing, weathered post-collapse medieval, scavenged technology, "
                   "ash and rust and tarnished gold, transparent background")
NEGATIVE = ("photo, realistic, blurry, text, watermark, signature, gradient, 3d render, extra limbs, anime, chibi, "
            "purple glow, neon, skeleton, smooth shading, jpeg artifacts, bright saturated colours")


def normalize_job(repo: Path, rj: dict) -> None:
    spec = rj.setdefault("spec", {})
    kind = rj.get("kind")
    if kind == "image":
        at = ASSET_TYPES.get(str(spec.get("asset_type", "")).lower())
        if at:
            spec.setdefault("workflow", at["workflow"])
            spec.setdefault("width", at["width"]); spec.setdefault("height", at["height"])
            pp = spec.setdefault("postprocess", {})
            pp.setdefault("palette", True); pp.setdefault("downscale", at["downscale"])
            pp.setdefault("transparent_bg", at["transparent_bg"]); pp.setdefault("normal_map", at["normal_map"])
            fw, fh = spec.get("final_width"), spec.get("final_height")
            pp.setdefault("final_width", fw or at["final"][0]); pp.setdefault("final_height", fh or at["final"][1])
            spec.setdefault("final_width", pp["final_width"]); spec.setdefault("final_height", pp["final_height"])
            spec.setdefault("transparent_bg", at["transparent_bg"])
        prompt = str(spec.get("prompt", ""))
        if "pixel art" not in prompt.lower():
            spec["prompt"] = prompt.rstrip(", ") + ", " + POSITIVE_SUFFIX
        spec.setdefault("negative_prompt", NEGATIVE)
        spec.setdefault("count", 4)
        refs = spec.setdefault("references", [])
        for default in ("style/references/palette.png", "style/references/mock-day.png"):
            if default not in refs and (repo / default).exists():
                refs.append(default)
        if spec.get("workflow") == "character_sheet" and not any("sheet" in r for r in refs):
            sheet = repo / "style" / "references" / "reaper-sheet.png"
            if sheet.exists():
                refs.insert(0, "style/references/reaper-sheet.png")
    elif kind == "code":
        rj["output_dir"] = "game"
        acc = spec.setdefault("acceptance", [])
        if isinstance(acc, str):
            acc = spec["acceptance"] = [acc]
        if not any("headless" in str(a).lower() for a in acc):
            acc.append("project loads headless with no script errors")
        if not any("test" in str(a).lower() for a in acc):
            acc.append("a gdUnit4 test covers the new logic")
        if spec.get("scene") and not spec.get("proof"):
            spec["proof"] = {"scene": spec["scene"], "seconds": 4, "actions": ["move_right", "move_down"],
                             "expect": str(spec.get("goal", ""))[:200]}
        # GameCraft-Bench lesson: mechanics without visual feedback read as broken. Ask for it.
        if not any("visual" in str(a).lower() or "feedback" in str(a).lower() for a in acc):
            acc.append("every state change the player causes has visible feedback on screen")


def next_task_id(repo: Path) -> str:
    ids = [0]
    for d in ("backlog", "in-progress", "done", "deferred"):
        for p in (repo / "tasks" / d).glob("*.md"):
            m = re.match(r"(\d+)-", p.name)
            if m:
                ids.append(int(m.group(1)))
    return f"{max(ids) + 1:03d}"


def generate_backlog(repo: Path, count: int = 5) -> list[Path]:
    """Ask the orchestrator model for the next few tasks based on the design doc and what is done."""
    system = llm.load_role(repo, "orchestrator")
    done = "\n".join(p.name for p in sorted((repo / "tasks" / "done").glob("*.md")))
    deferred = "\n".join(p.name for p in sorted((repo / "tasks" / "deferred").glob("*.md")))
    user = "\n\n".join([
        _ctx(repo, "docs/10-game-design.md", "docs/14-world-bible.md", "docs/01-vision.md", "style/style-bible.md", "tasks/README.md"),
        "## Done tasks\n" + (done or "(none)"),
        "## Deferred tasks (do not repeat these)\n" + (deferred or "(none)"),
        f"The backlog is empty. Propose the next {count} tasks that move the prototype forward, "
        "smallest first, each doable by one or two roles in under an hour of worker time. "
        "Respond with JSON: {\"tasks\": [{\"title\": ..., \"priority\": 1-9, \"roles\": [...], "
        "\"goal\": ..., \"acceptance\": [...], \"notes\": ...}]}",
    ])
    data = llm.chat_json(system, user)
    created = []
    for t in data.get("tasks", [])[:count]:
        tid = next_task_id(repo)
        slug = re.sub(r"[^a-z0-9]+", "-", t["title"].lower()).strip("-")[:40]
        body = (f"# {tid} {t['title']}\npriority: {t.get('priority', 5)}\n"
                f"roles: {', '.join(t.get('roles', []))}\n\n## Goal\n{t.get('goal', '')}\n\n"
                "## Acceptance\n" + "\n".join(f"- {a}" for a in t.get("acceptance", [])) +
                f"\n\n## Notes\n{t.get('notes', '')}\n\n_generated by orchestrator {time.strftime('%Y-%m-%d %H:%M')}_\n")
        p = repo / "tasks" / "backlog" / f"{tid}-{slug}.md"
        p.write_text(body)
        created.append(p)
    return created


def record_side_effects(repo: Path, task_path: Path, data: dict) -> None:
    """Auto decisions and style-bible rewrites that came back with a plan."""
    day = time.strftime("%Y-%m-%d")
    decisions = [str(d) for d in data.get("decisions") or []][:10]
    if decisions:
        with (repo / "docs" / "decisions.md").open("a") as f:
            for d in decisions:
                f.write(f"| {day} | (auto) {d.replace('|', '/')} | orchestrator, task {task_path.stem} |\n")
        with task_path.open("a") as f:
            f.write("\n- auto decisions: " + "; ".join(decisions))
    sb = data.get("style_bible")
    if isinstance(sb, str) and len(sb) > 200 and "## Visual style" in sb:
        (repo / "style" / "style-bible.md").write_text(sb)
        with task_path.open("a") as f:
            f.write("\n- style bible rewritten by orchestrator")
