# The brain: Obsidian + retrieval + task state

Obsidian is the owner-selected knowledge editor and reference workspace for this setup.
The assistant retrieves its underlying notes directly; memory remains portable.
Its vault is a local folder of Markdown notes. The assistant reads those same files. No paid
Obsidian Sync/Publish or commercial license is required for this setup. Sources:
[Obsidian storage](https://obsidian.md/help/data-storage), [pricing](https://obsidian.md/pricing).

## Three layers

| Layer | Contents | Authority |
|---|---|---|
| GitHub checkout | Source, worker templates, setup, shareable decisions, game bibles | Versioned setup and code |
| Private Obsidian vault | Personal/business/game facts, evidence, approved decisions, lessons | Human-readable knowledge |
| Local SQLite | Search index, jobs, attempts, events, request counters | Runtime state; index rebuildable |

The graph in Obsidian helps you navigate notes. It does not automatically give the model semantic
reasoning or retrieval. The implemented search uses SQLite FTS5, is local/free, and returns paths,
text and content digests. Existing Godot embedding retrieval remains in the legacy studio; it is
not a requirement for the new memory system. Add semantic search only if tests show keyword search
misses useful notes. Do not require a separate vector database just to call it a brain.

## Folder structure inside the private vault

- `shared/`: operating rules and genuinely shared facts.
- `personal/`: preferences, projects, personal decisions. Empty template initially.
- `business/`: processes, calculations, administrative rules, decision history.
- `game/`: copied canonical game/world/style bibles and project lessons.

Avoid placing private data in `shared/`: it is available to every project. Default cloud sharing is
off per project until configured. Do not paste API keys into any vault. A separate private Git repo
could later version selected notes, but the currently connected repo is public and must not receive
private notes. Obsidian can open the server's local folder with no subscription.

## Note templates

A fact note should have: title, scope, source, observed date, confirmed/proposed status, content,
related note links and a supersedes field when needed. Use ordinary Markdown links for portability.

A failure lesson should have: symptom, reproduction, evidence, hypotheses tried, confirmed cause
(or unknown), repair, verification, regression check, scope, proposed skill, review status.
Do not promote a speculation into a permanent instruction. Do not automatically rewrite the
controller's own permissions. Skills are procedural memory, not model weight training.

## Retrieval and lifecycle

Run `python -m assistant.run index` after edits, or let each runner pass refresh the index. Searches
return only the selected project's notes and `shared/`. Removed notes disappear after reindexing.
Symlink escapes and oversized files are excluded. The index's snippets are data, not instructions.

Initialization copies bibles once without replacing edits. After a Git update, compare canonical
source changes with vault copies and explicitly merge them. If a decision changes, add its date
and preserve the former decision as superseded. Do not blindly replace the vault on every pull.

## Claude Code memory MCP

`config/assistant/mcp.example.json` shows the Windows command and path. Replace `C:\studio` if needed.
The helper is `scripts/memory-mcp.py`; it provides one read-only `memory_search(query)` tool. The
process's `ASSISTANT_PROJECT` determines its scope, not a query parameter chosen by a worker.
Launch separate configured sessions for game/business/personal. Reindex first.

The core controller retrieves memory itself and runs cloud planning with arbitrary tools disabled.
This MCP config is for separate interactive Claude Code sessions and later tool integration; simply
saving it does not make it active in every session. Verify tool discovery and one scoped query
before enabling it in the intended Claude session. Never share a personal-scoped server with a
worker intended to see only game data.

## Backup and restore

Stop the runner and close the UI; copy the entire private runtime folder, including SQLite and any
WAL/SHM companions, to an existing backup location. Restart afterward. Restore to a test folder,
set `ASSISTANT_HOME` to that folder, run status/search, and compare a known task and note. Git history
is not a substitute for a backup of private state. Do not live-sync an active SQLite file between PCs.
Only the server owns task state; the gaming PC is an execution resource.

## General side projects and model knowledge

The existing `personal` scope is the General / side projects section, including random projects.
Use named subfolders and project index notes; automated subproject isolation remains pending.
Store evaluated model strengths/weaknesses with dated evidence as OPENROUTER-ROUTING.md specifies.
Link lessons to task evidence and proposed skills in SKILLS.md.

## Approved knowledge policy

See [Obsidian and GitHub rules](authority/OBSIDIAN-AND-GITHUB.md) for authority ownership, proposed/approved knowledge, conflict-safe rule updates and mailbox projections. The current FTS implementation does not enforce note approval metadata or per-subproject boundaries. These remain implementation gates.
