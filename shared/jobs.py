"""Job and result models shared by the orchestrator (server) and the GPU worker.

This is the source of truth for the queue format. docs/08-job-schema.md describes it in prose.
Regenerate shared/schema/job.schema.json with `python -m shared.jobs` after changing this file.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobKind(str, Enum):
    STUB = "stub"        # echoes back; for testing the pipeline end to end
    IMAGE = "image"      # ComfyUI: sprites, tiles, backgrounds, concept art
    MUSIC = "music"      # ACE-Step: tracks and loops
    SFX = "sfx"          # Stable Audio Open: short effects
    CODE = "code"        # handled in-process by the orchestrator's coder loop, never queued to the GPU worker
    TRAIN = "train"      # fine-tune a model on the studio's own data (LoRA / QLoRA); GPU worker, see training/
    # `review` is not a job kind: the orchestrator reviews every asset result automatically.


class Role(str, Enum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    ARTIST_2D = "artist-2d"
    AUDIO = "audio"
    REVIEWER = "reviewer"
    TRAINER = "trainer"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_job_id(task_id: str, slug: str) -> str:
    return f"{task_id}-{slug}-{secrets.token_hex(3)}"


class Job(BaseModel):
    id: str
    task_id: str
    kind: JobKind
    role: Role
    priority: int = Field(default=5, ge=1, le=10, description="1 = highest")
    created_at: str = Field(default_factory=_now)
    attempt: int = 1
    max_attempts: int = 3
    spec: dict[str, Any] = Field(default_factory=dict)
    output_dir: str = Field(description="Relative to repo root, under assets/incoming/")
    notes: Optional[str] = Field(default=None, description="Reviewer feedback from earlier attempts")

    @property
    def queue_key(self) -> str:
        return f"jobs:{self.kind.value}"

    @property
    def processing_key(self) -> str:
        return f"jobs:{self.kind.value}:processing"

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str | bytes) -> "Job":
        return cls.model_validate_json(raw)


class ResultStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class Result(BaseModel):
    job_id: str
    status: ResultStatus
    worker: str
    started_at: str
    finished_at: str = Field(default_factory=_now)
    outputs: list[str] = Field(default_factory=list)
    sidecar: Optional[str] = None
    error: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str | bytes) -> "Result":
        return cls.model_validate_json(raw)


class Sidecar(BaseModel):
    """One per generated file. Records provenance and licence so assets can ship safely."""
    generator: str
    model: str
    licence: str
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    job_id: str
    extra: dict[str, Any] = Field(default_factory=dict)
    review: Optional[dict[str, Any]] = None  # {"verdict": "approved|rejected", "reason": "...", "by": "..."}

    def write(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))


RESULTS_KEY = "results"


def heartbeat_key(worker_name: str) -> str:
    return f"worker:{worker_name}:heartbeat"


def status_key(worker_name: str) -> str:
    return f"worker:{worker_name}:status"


if __name__ == "__main__":
    out = Path(__file__).parent / "schema"
    out.mkdir(exist_ok=True)
    (out / "job.schema.json").write_text(json.dumps(Job.model_json_schema(), indent=2))
    (out / "result.schema.json").write_text(json.dumps(Result.model_json_schema(), indent=2))
    (out / "sidecar.schema.json").write_text(json.dumps(Sidecar.model_json_schema(), indent=2))
    print("schemas written to", out)
