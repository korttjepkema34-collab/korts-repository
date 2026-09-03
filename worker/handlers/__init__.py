"""Handler registry. Each handler exposes run(job, out_dir, cfg) -> (outputs, sidecar_path)
and unload(cfg) to free VRAM. Add a kind here and in shared/jobs.py together."""
from shared.jobs import JobKind

from . import acestep, comfyui, stub, train

HANDLERS = {
    JobKind.STUB: stub,
    JobKind.IMAGE: comfyui,
    JobKind.MUSIC: acestep,
    JobKind.SFX: acestep,
    JobKind.TRAIN: train,
}
