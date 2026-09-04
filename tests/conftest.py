import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "server"), str(ROOT / "worker")):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("ORCHESTRATOR_MODEL", "fake")
os.environ.setdefault("REPO_ROOT", str(ROOT))
