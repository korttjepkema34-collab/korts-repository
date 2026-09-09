> **Repository navigation:** [Where everything belongs](docs/assistant/REPOSITORY-MAP.md) · [Approved studio rules](docs/assistant/authority/README.md)

# Kort's personal assistant, business helper, and game studio

A cloud-led assistant running on two existing Windows PCs, with editable local workers,
a custom desktop UI, and an Obsidian-compatible memory vault. No new GPU or paid inference.

**Start with [the complete setup guide](docs/assistant/SETUP.md).** This branch implements a
working foundation for cloud planning/review, local drafts, isolated code candidates, persistent
queues, and reports. It is **not yet a complete autonomous multimedia studio**. Read the
[acceptance checklist and remaining implementation](docs/assistant/ACCEPTANCE.md) before overnight use.

| Piece | Current choice |
|---|---|
| Brain and reviewer | Qualified free cloud model through Claude Code; never local takeover |
| Server | i7-10700K, 96 GB RAM, Windows, no dedicated GPU |
| Gaming PC | Ryzen 9 7900X, 32 GB RAM, RTX 3080 Ti 12 GB |
| Connection | Tailscale plus localhost SSH forwarding for GPU Ollama |
| Workers | 13 editable specialist profiles; native media adapters remain to be connected |
| Memory | Private Markdown vault + SQLite search/state; optional Obsidian editor |
| UI | Custom Python/Tkinter desktop shell; richer chat design documented |
| Game | Existing Reaper's Relics Godot design and source preserved |

## Read in order

1. [Setup](docs/assistant/SETUP.md) and [hardware](docs/assistant/HARDWARE.md).
2. [Models and qualification](docs/assistant/MODELS.md), [workers](docs/assistant/WORKERS.md).
3. [Memory](docs/assistant/MEMORY.md), [GitHub synchronization](docs/assistant/GITHUB.md).
4. [Code and Godot](docs/assistant/CODE-AND-GAME.md), [art and audio](docs/assistant/ASSETS.md).
5. [Integrations](docs/assistant/INTEGRATIONS.md), [UI design](docs/assistant/UI-DESIGN.md).
6. [Decisions](docs/assistant/DECISIONS.md), [acceptance](docs/assistant/ACCEPTANCE.md), [verification](docs/assistant/VERIFICATION.md).

AI contributors: read [AGENTS.md](AGENTS.md). New entry point: `python -m assistant.run`.
The older `server/orchestrator/main.py` entry point is disabled because its local-led automatic
approval/merge behavior conflicts with current requirements. Older studio modules remain migration
material, not a second setup path. This public repository stores source and templates; actual
personal/business notes, keys, tasks, and reports live outside the checkout.

Reaper's Relics references: [game design](docs/10-game-design.md), [world bible](docs/14-world-bible.md),
[style bible](style/style-bible.md), [Godot conventions](docs/09-godot-conventions.md).

Owner requirements: [REQUIREMENTS.md](docs/assistant/REQUIREMENTS.md).
Model discovery/switching: [routing design](docs/assistant/OPENROUTER-ROUTING.md).
Reusable worker procedures: [skill catalog](docs/assistant/SKILLS.md).
