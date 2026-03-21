"""Session management tools — delegates to ClaudeSessionManager."""

from typing import Any

from da.claude_sessions import ClaudeSessionManager

session_tool_defs = [
    {
        "name": "list_hosts",
        "description": "List all known hosts from Claude Code history.",
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
        "description": "Delete a Claude Code session by ID.",
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


def execute_session_tool(name: str, inputs: dict[str, Any]) -> str:
    claude_dir = inputs.get("claude_dir", "/mnt/d/SD/.claude")
    mgr = ClaudeSessionManager(claude_dir)

    if name == "list_hosts":
        hosts = mgr.list_hosts()
        if not hosts:
            return "No hosts found."
        return "\n".join(f"{h['label']}: {h['projects']} projects, {h['sessions']} sessions" for h in hosts)

    elif name == "list_sessions":
        host_filter = inputs.get("host", "").lower()
        proj_filter = inputs.get("project", "").lower()
        limit = inputs.get("limit", 20)
        data = mgr.scan_all()
        results = []
        for machine, projects in sorted(data.items()):
            if host_filter and host_filter not in machine.lower():
                continue
            for proj, sessions in sorted(projects.items()):
                if proj_filter and proj_filter not in proj.lower():
                    continue
                for s in sessions:
                    results.append(f"{machine}/{proj.split('/')[-1]}  {s['id'][:12]}  {s.get('date','')}  {s['name']}")
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break
        return "\n".join(results) or "No sessions found."

    elif name == "delete_claude_session":
        return mgr.delete_session(inputs["session_id"])

    elif name == "move_claude_session":
        sid = inputs["session_id"]
        dest = inputs["destination"]
        if inputs.get("copy"):
            return mgr.copy_session(sid, dest)
        return mgr.move_session(sid, dest)

    return f"Unknown session tool: {name}"
