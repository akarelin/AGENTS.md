"""File tools — Read (4,585) + Edit (3,360) + Write (1,388) in your history."""

from pathlib import Path
from typing import Any

file_tool_defs = [
    {
        "name": "read_file",
        "description": "Read file contents. Supports line ranges.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "offset": {"type": "integer", "description": "Start line (1-based)"},
                "limit": {"type": "integer", "description": "Number of lines to read"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact string in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "old_string": {"type": "string", "description": "Text to find"},
                "new_string": {"type": "string", "description": "Replacement text"},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "list_dir",
        "description": "List directory contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
                "recursive": {"type": "boolean", "description": "List recursively"},
                "pattern": {"type": "string", "description": "Glob filter (e.g. '*.py')"},
            },
            "required": ["path"],
        },
    },
]


def execute_file_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute file tools."""
    if name == "read_file":
        p = Path(inputs["path"]).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            offset = inputs.get("offset", 1) - 1
            limit = inputs.get("limit", len(lines))
            selected = lines[offset : offset + limit]
            return "\n".join(
                f"{i + offset + 1:>5}\t{line}" for i, line in enumerate(selected)
            )
        except Exception as e:
            return f"Error reading {p}: {e}"

    elif name == "write_file":
        p = Path(inputs["path"]).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(inputs["content"], encoding="utf-8")
            return f"Written {len(inputs['content'])} bytes to {p}"
        except Exception as e:
            return f"Error writing {p}: {e}"

    elif name == "edit_file":
        p = Path(inputs["path"]).expanduser()
        if not p.exists():
            return f"File not found: {p}"
        try:
            content = p.read_text(encoding="utf-8")
            old = inputs["old_string"]
            new = inputs["new_string"]
            if old not in content:
                return f"String not found in {p}"
            if inputs.get("replace_all"):
                updated = content.replace(old, new)
            else:
                updated = content.replace(old, new, 1)
            p.write_text(updated, encoding="utf-8")
            count = content.count(old)
            replaced = count if inputs.get("replace_all") else 1
            return f"Replaced {replaced} occurrence(s) in {p}"
        except Exception as e:
            return f"Error editing {p}: {e}"

    elif name == "list_dir":
        p = Path(inputs["path"]).expanduser()
        if not p.is_dir():
            return f"Not a directory: {p}"
        try:
            pattern = inputs.get("pattern", "*")
            if inputs.get("recursive"):
                entries = sorted(p.rglob(pattern))
            else:
                entries = sorted(p.glob(pattern))
            lines = []
            for e in entries[:200]:
                rel = e.relative_to(p)
                suffix = "/" if e.is_dir() else ""
                lines.append(f"  {rel}{suffix}")
            total = len(entries)
            if total > 200:
                lines.append(f"  ... and {total - 200} more")
            return "\n".join(lines) or "(empty directory)"
        except Exception as e:
            return f"Error listing {p}: {e}"

    return f"Unknown file tool: {name}"
