# Claude Code entry point

Read `AGENTS.md` first. Current setup: `docs/assistant/SETUP.md`; implementation status and
remaining work: `docs/assistant/ACCEPTANCE.md`. The brain is a qualified free cloud model;
local workers never take over. The old local-led studio runtime is disabled.

Current code lives in `assistant/`; editable profile templates in `config/assistant/`.
Run `python -m unittest discover -s tests/assistant -v` for its offline suite.
The legacy studio merge gate remains `pytest tests`; do not merge without required checks.

Memory: `docs/assistant/MEMORY.md`. Private vault/task data lives outside this public checkout.
MCP configuration is documented in `docs/assistant/INTEGRATIONS.md`; existing repository skills
under `.claude/skills/` are reference material and need their legacy assumptions reviewed before use.
Planning and review subprocesses deliberately load no repository skills or MCPs implicitly.

Preserve game design `docs/10-game-design.md`, world `docs/14-world-bible.md`, style
`style/style-bible.md`, and conventions `docs/09-godot-conventions.md`. Older `agents/` prompts
are game-studio references; current worker profiles take precedence for assistant operation.
