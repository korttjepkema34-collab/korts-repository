# Where everything belongs

## Branches

`main` is the canonical reviewed source. Task branches are temporary work areas, not separate installations. Use one branch per active change and remove it after integration when no unique work remains. Do not maintain parallel copies of the whole setup.

At the 2026-09-09 audit, `claude/ai-game-dev-team-godot-0ir8yf` was identical to main at 0544154; `claude/local-ai-game-model-0x7ko1` was 14 commits behind main with zero unique commits. Both are obsolete branch pointers, not missing features. `assistant/cloud-led-memory-setup` held the six newer assistant commits and is the consolidation source.

## Directory ownership

| Location | Purpose |
|---|---|
| `assistant/` | Current assistant runtime (runner, dashboard `web.py` + `web_static/`, backups, health) |
| `scripts/` (assistant) | `install-runner-service.ps1`, `gpu-tunnel.ps1`, `synthetic_e2e.py`, `check_private_leak.py`, `make_sample_project.py` |
| `config/assistant/` | Shareable configuration and worker templates |
| `docs/assistant/authority/` | Approved studio authority documents |
| `docs/assistant/` | Current setup, architecture, acceptance and memory guidance |
| `tests/assistant/` | Current assistant tests |
| `game/`, `style/` | Preserved game source and design references |
| `server/`, `worker/`, `shared/` | Legacy system retained for migration; not the approved unattended entry point |

Private Obsidian vaults, task databases, mailbox records, secrets and business artifacts remain outside this public repository. The privately hosted office demo source is retained separately; it is not implemented under assistant/ or silently included in this consolidation. Office follow-up is issue #2.

Start with docs/assistant/SETUP.md and docs/assistant/authority/README.md. Older numbered documentation can describe historical behavior; the current assistant decisions and authority take precedence.
