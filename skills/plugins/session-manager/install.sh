#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST_DIR="$HOME/.claude/skills/session-manager"

mkdir -p "$DST_DIR"
cp -f "$SRC_DIR"/SKILL.md "$DST_DIR"/
cp -f "$SRC_DIR"/claude_session_manager.py "$DST_DIR"/
cp -f "$SRC_DIR"/claude_session_map.json "$DST_DIR"/
cp -f "$SRC_DIR"/plugin.json "$DST_DIR"/
chmod +x "$DST_DIR"/claude_session_manager.py

echo "Installed to $DST_DIR"
