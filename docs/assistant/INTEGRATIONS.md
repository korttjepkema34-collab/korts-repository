# Skills, MCP, connections and project access

## Available implementation

- Claude Code is the cloud planning/review harness via its programmatic CLI.
- Local workers use Ollama's local API; GPU requests use a localhost SSH tunnel.
- Existing `.claude/skills/` instructions can be assigned as explicit worker context.
- `scripts/memory-mcp.py` provides read-only scoped retrieval for separately configured Claude sessions.
- GitHub pull helper refreshes code between runs and never pushes the private brain.

The core cloud call has arbitrary tools disabled. This prevents a planner from bypassing validated
jobs or spending through unrelated tools. It does not claim full interactive Claude MCP/skill
feature parity. Tool-enabling changes need their own tested boundary and free-only routing checks.

## Connection inventory to complete on the server

| Connection | Setup | Verification |
|---|---|---|
| Personal GitHub | Correct account; clone this repo; SSH/Git credential manager locally | Read origin, fetch branch; no private vault upload |
| Business GitHub | Separate intended repository and access | Read existing instructions, run checks in isolated clone |
| OpenRouter | Local environment key, free model, no auto-top-up | Qualification report and provider activity |
| Ollama cloud | Server sign-in, eligible included allowance | Actual model invocation and allowance behavior |
| GPU Ollama | OpenSSH tunnel over Tailscale | API tags plus real model request |
| Memory MCP | Absolute Python/script paths; fixed project env | Discover tool and scoped query |
| Godot MCP | Optional reviewed server, pinned version, explicit project path | Discover tools; read scene; verify intended edits in disposable project |
| Browser QA | Reviewed Playwright setup on development target | Screenshot, interaction, console and assertion evidence |
| Business services | Exact service/API and minimum needed access | Read/test operations before consequential writes |

No email, calendar, payments, database, deployment or other person-directed connector is silently
inherited from ChatGPT by your home server. Each requires its own supported connection and local
credentials. Keep credentials outside Git; grant actual actions intentionally. The current runtime
creates drafts/candidates and does not send messages or mutate customer records.

Choose Godot MCP based on the pinned engine and actual tool behavior, not an assumption of perfect
AI compatibility. Existing `docs/11-godot-mcp-options.md` is historical research to recheck. A command
line engine test is still necessary even when editor tools are available.
