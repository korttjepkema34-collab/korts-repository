# Current decisions and continuity record

Confirmed from this conversation, 2026-09-09:

- Build a personal assistant, business helper and video game team, with separate project context.
- Own custom interface and Claude Code skill/MCP familiarity are priorities.
- No new subscriptions or paid inference. Existing $10 OpenRouter purchase enables the higher free
  allowance; it is not a paid-model budget.
- Strong free cloud models lead, decompose, delegate, diagnose, review and direct repairs.
- Local workers never take over leadership or approve themselves. Cloud loss pauses decisions.
- User's heavy daily OpenRouter usage has reached about 600; assume 1,000/day is workable initially.
- Two Windows PCs via Tailscale; server i7-10700K/96 GB/no dedicated GPU; gaming PC
  Ryzen 9 7900X/32 GB/RTX 3080 Ti 12 GB. There is no additional or planned purchased GPU.
- Godot is preferred. Existing repository already contains Reaper's Relics Godot 4 design/code,
  world bible, style references, gameplay systems and tests; preserve them.
- Overnight work needs evidence, repair attempts, honest blockers and morning reports.
- Learning means useful memory and proposed skills, not uncontrolled self-modification.
- Correct GitHub account is korttjepkema34-collab; current repository is public.
- Server uses GitHub as a versioned source of code/setup/knowledge, with private live memory locally.

Implementation decisions for this setup revision:

- SQLite FTS5 plus Markdown/Obsidian vault; no mandatory vector database or paid Sync.
- Standard-library Python controller and native desktop shell to keep installation simple/free.
- Cloud planning/review calls run through Claude Code without arbitrary tools; local workers get
  explicit bounded input. Advanced interactive MCP/tool flows are separate qualification work.
- Code candidates live in isolated clones and require configured checks plus cloud review.
- Legacy unattended loop disabled because local leadership/auto-approval contradicts current policy.
- Media adapters, visual evidence transport and cross-project integration are tracked gaps, not
  described as completed. No live device/model tests claimed without access.

Open details needed during setup: free disk; actual installed versions; eligible Ollama cloud models;
OpenRouter candidate behavior; private business checkout; pinned Godot/add-on versions; GPU gaming
schedule; final UI taste; authenticated service connections; actual overnight recovery behavior.
