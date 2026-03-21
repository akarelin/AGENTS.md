"""Session management tools — list, delete, move sessions; list hosts."""

import json
import shutil
from pathlib import Path
from typing import Any

session_tool_defs = [
    {
        "name": "list_hosts",
        "description": "List all known hosts from Claude Code history and DA config.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claude_dir": {"type": "string", "description": "Path to .claude directory (optional)"},
            },
        },
    },
    {
        "name": "list_sessions",
        "description": "List Claude Code sessions, optionally filtered by host or project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Filter by host/machine name"},
                "project": {"type": "string", "description": "Filter by project path substring"},
                "claude_dir": {"type": "string", "description": "Path to .claude directory"},
                "limit": {"type": "integer", "description": "Max sessions to return (default 20)"},
            },
        },
    },
    {
        "name": "delete_claude_session",
        "description": "Delete a Claude Code session by ID. Removes JSONL and associated subagent/tool-result files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session UUID"},
                "claude_dir": {"type": "string", "description": "Path to .claude directory"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "move_claude_session",
        "description": "Move/copy a Claude Code session to a different directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session UUID"},
                "destination": {"type": "string", "description": "Destination directory path"},
                "copy": {"type": "boolean", "description": "Copy instead of move (default false)"},
                "claude_dir": {"type": "string", "description": "Path to .claude directory"},
            },
            "required": ["session_id", "destination"],
        },
    },
]


def _find_session_file(session_id: str, claude_dir: str) -> Path | None:
    """Find session JSONL by ID across all machines/projects."""
    cpath = Path(claude_dir)
    for f in cpath.glob(f"*/projects/*/{session_id}.jsonl"):
        return f
    return None


def _first_user_msg(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "user" and not d.get("isMeta"):
                    c = d.get("message", {}).get("content", "")
                    if isinstance(c, str) and len(c) > 3 and not c.startswith("<"):
                        return c[:80]
    except Exception:
        pass
    return ""


def execute_session_tool(name: str, inputs: dict[str, Any]) -> str:
    claude_dir = inputs.get("claude_dir", "/mnt/d/SD/.claude")
    cpath = Path(claude_dir)

    if name == "list_hosts":
        if not cpath.exists():
            return f"Directory not found: {claude_dir}"
        hosts = []
        for d in sorted(cpath.iterdir()):
            if d.is_dir() and (d / "projects").is_dir():
                projects = list((d / "projects").iterdir())
                sessions = sum(1 for p in projects if p.is_dir() for _ in p.glob("*.jsonl"))
                hosts.append(f"{d.name}: {len(projects)} projects, {sessions} sessions")
        return "\n".join(hosts) or "No hosts found."

    elif name == "list_sessions":
        if not cpath.exists():
            return f"Directory not found: {claude_dir}"
        host_filter = inputs.get("host", "").lower()
        proj_filter = inputs.get("project", "").lower()
        limit = inputs.get("limit", 20)
        results = []
        for mdir in sorted(cpath.iterdir()):
            if not mdir.is_dir():
                continue
            if host_filter and host_filter not in mdir.name.lower():
                continue
            pdir = mdir / "projects"
            if not pdir.is_dir():
                continue
            for projd in sorted(pdir.iterdir()):
                if not projd.is_dir():
                    continue
                if proj_filter and proj_filter not in projd.name.lower():
                    continue
                for sf in sorted(projd.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                    if sf.name.startswith("."):
                        continue
                    size = sf.stat().st_size
                    msg = _first_user_msg(sf)
                    results.append(f"{mdir.name}/{projd.name}  {sf.stem[:12]}  {size:>8,}B  {msg}")
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        return "\n".join(results) or "No sessions found."

    elif name == "delete_claude_session":
        sid = inputs["session_id"]
        fpath = _find_session_file(sid, claude_dir)
        if not fpath:
            return f"Session not found: {sid}"
        session_dir = fpath.parent / fpath.stem
        deleted = [str(fpath)]
        fpath.unlink()
        if session_dir.is_dir():
            shutil.rmtree(session_dir)
            deleted.append(str(session_dir))
        return f"Deleted: {', '.join(deleted)}"

    elif name == "move_claude_session":
        sid = inputs["session_id"]
        dest = Path(inputs["destination"]).expanduser()
        is_copy = inputs.get("copy", False)
        fpath = _find_session_file(sid, claude_dir)
        if not fpath:
            return f"Session not found: {sid}"
        dest.mkdir(parents=True, exist_ok=True)
        session_dir = fpath.parent / fpath.stem
        op = shutil.copy2 if is_copy else shutil.move
        op(str(fpath), str(dest / fpath.name))
        if session_dir.is_dir():
            dest_session = dest / fpath.stem
            if is_copy:
                shutil.copytree(str(session_dir), str(dest_session))
            else:
                shutil.move(str(session_dir), str(dest_session))
        verb = "Copied" if is_copy else "Moved"
        return f"{verb} session {sid[:12]} to {dest}"

    return f"Unknown session tool: {name}"
