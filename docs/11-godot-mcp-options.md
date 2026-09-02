# 11 - Godot MCP server options

The coder agent needs hands inside Godot. Three viable choices as of Sept 2026. Findings from
public roundups; verify current features before installing.

| Option | Licence / cost | Can run the game and read errors? | Reads and edits scenes/scripts? | Notes |
|---|---|---|---|---|
| **Coding-Solo `godot-mcp`** | Open source (MIT) | **Yes**: launch editor, run project, capture debug output, create scenes | Basic | Small, clean codebase, easy to extend with our own tools. The original Godot MCP. |
| **GDAI MCP** | Open source | No (file-level only) | **Yes, best in class**: parses `.tscn` hierarchies and signals, rewrites scripts with project context | Cleanest setup docs. Cannot press play. |
| **StraySpark Godot MCP** | Commercial | **Yes**: live editor connection over WebSocket, auto-reconnect | Yes, 137 tools, 18 categories, works with editor closed too | Most complete. Costs money; price not verified here. |

## Recommendation

**Run both open-source servers side by side: Coding-Solo `godot-mcp` for running the game and
reading runtime errors, GDAI MCP for reading and editing scenes and scripts.** They are
complementary, both free, and MCP clients can load several servers at once. The self-correct
loop (edit, run, read the real error, fix) is the single most valuable thing for a local coder
model, and only `godot-mcp` or StraySpark provide it among these.

Switch to StraySpark later if the two-server setup proves fiddly and the price is acceptable.
It is the one that would need the "spend money" decision from the human.

Install the chosen server **on the home server**, not the gaming PC, and set `GODOT_MCP_CMD` in
`server/.env`. The coder loop bridges its tools in automatically (`server/orchestrator/mcp_bridge.py`).
The server's integrated Intel graphics is enough to run the editor. The coder keeps file tools,
the headless gate and windowed screenshots regardless, so MCP is additive, never a dependency.
