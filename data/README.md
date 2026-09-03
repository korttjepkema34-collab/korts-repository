# data/

Server-only working data, git-ignored. Nothing here is needed to run the studio; everything
here makes it better over time.

| Folder | Written by | Used by |
|---|---|---|
| `traces/coder/` | `server/orchestrator/traces.py` after every coder run (transcript + gate pass/fail) | `training/build_datasets.py coder` |
| `traces/reviewer/verdicts.jsonl` | every reviewer verdict | `training/build_datasets.py reviewer` |
| `traces/reviewer/overrides.jsonl` | you, via `scripts/override.py` | same; your decisions weigh 3x |
| `rag/index.json` | `scripts/build_rag_index.py` | the coder's `search_docs` tool and its prompt |
| `godot-docs/` | `scripts/fetch_godot_docs.py` | retrieval index |
| `godot4-code/` | `training/collect_godot4_code.py` | coder fine-tune (public MIT Godot 4 code) |
| `training/state.json` | `server/orchestrator/training.py` | what was trained when, and on how much |
| `training/latest.json` | `server/orchestrator/training.py` after a train job finishes | you: every finished model and where it is |

Back it up with the server: `traces/` is the only copy of the studio's labelled history.
