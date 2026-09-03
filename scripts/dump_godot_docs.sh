#!/usr/bin/env bash
# Linux/macOS: dump the installed Godot's class reference into server/godot-docs for the coder's search tool.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$repo/server/.env" ] && export $(grep -E '^GODOT_BIN=' "$repo/server/.env" | xargs) || true
: "${GODOT_BIN:?GODOT_BIN not set}"
mkdir -p "$repo/server/godot-docs"
"$GODOT_BIN" --headless --doctool "$repo/server/godot-docs" --no-docbase
echo "class reference dumped: $(find "$repo/server/godot-docs" -name '*.xml' | wc -l) files"
