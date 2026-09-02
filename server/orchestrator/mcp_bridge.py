"""Optional bridge to a Godot MCP server (e.g. Coding-Solo godot-mcp) so the coder gets editor
tools: launch the editor, run the project, read runtime errors, inspect scene trees.

Enabled when GODOT_MCP_CMD is set, e.g.  GODOT_MCP_CMD="node C:/tools/godot-mcp/build/index.js"
Requires the `mcp` Python package. If anything fails, the coder silently keeps its file tools.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import threading
from typing import Any

log = logging.getLogger("mcp")


class GodotMCP:
    def __init__(self, cmd: str, cwd: str | None = None, call_timeout_s: int = 180):
        self.cmd, self.cwd, self.timeout = cmd, cwd, call_timeout_s
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.session = None
        self.tools: list[dict] = []
        self._run(self._connect())

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=self.timeout + 30)

    async def _connect(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        parts = shlex.split(self.cmd)
        env = dict(os.environ)
        self._ctx = stdio_client(StdioServerParameters(command=parts[0], args=parts[1:], cwd=self.cwd, env=env))
        read, write = await self._ctx.__aenter__()
        self._sess_ctx = ClientSession(read, write)
        self.session = await self._sess_ctx.__aenter__()
        await self.session.initialize()
        listed = await self.session.list_tools()
        self.tools = [{"type": "function", "function": {
            "name": "mcp_" + t.name, "description": (t.description or "")[:800],
            "parameters": t.inputSchema or {"type": "object", "properties": {}}}} for t in listed.tools]
        log.info("connected to Godot MCP with %d tools", len(self.tools))

    def call(self, name: str, args: dict[str, Any]) -> str:
        async def go():
            res = await asyncio.wait_for(self.session.call_tool(name.removeprefix("mcp_"), args), self.timeout)
            parts = []
            for c in res.content:
                parts.append(getattr(c, "text", None) or json.dumps(getattr(c, "model_dump", lambda: str(c))()))
            return "\n".join(parts)[:12000]
        try:
            return self._run(go())
        except Exception as e:
            return f"MCP ERROR: {e}"

    def close(self):
        try:
            self._run(self._sess_ctx.__aexit__(None, None, None))
            self._run(self._ctx.__aexit__(None, None, None))
        except Exception:
            pass


def connect_if_configured(cwd: str) -> GodotMCP | None:
    cmd = os.environ.get("GODOT_MCP_CMD")
    if not cmd:
        return None
    try:
        return GodotMCP(cmd, cwd=cwd)
    except Exception as e:
        log.warning("Godot MCP unavailable, continuing with file tools: %s", e)
        return None
