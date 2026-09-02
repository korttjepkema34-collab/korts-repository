#!/usr/bin/env bash
# Linux/macOS equivalent of install_gdunit4.ps1.
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
url="$(curl -fsSL https://api.github.com/repos/MikeSchulze/gdUnit4/releases/latest | grep -oE '"zipball_url": *"[^"]+"' | cut -d'"' -f4)"
curl -fsSL "$url" -o "$tmp/gdunit4.zip"
unzip -q "$tmp/gdunit4.zip" -d "$tmp"
src="$(find "$tmp" -type d -path '*/addons/gdUnit4' | head -1)"
rm -rf "$repo/game/addons/gdUnit4"; mkdir -p "$repo/game/addons"
cp -r "$src" "$repo/game/addons/gdUnit4"
echo "gdUnit4 installed to game/addons/gdUnit4; enable it in project.godot [editor_plugins]"
