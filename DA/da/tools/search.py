"""Search tools — Grep (999) + Glob (619) in your history."""

import subprocess
from pathlib import Path
from typing import Any

search_tool_defs = [
    {
        "name": "grep_search",
        "description": "Search file contents using ripgrep (regex supported).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search"},
                "path": {"type": "string", "description": "Directory or file to search"},
                "glob": {"type": "string", "description": "File glob filter (e.g. '*.py')"},
                "case_insensitive": {"type": "boolean", "description": "Case-insensitive search"},
                "context": {"type": "integer", "description": "Lines of context around match"},
                "max_results": {"type": "integer", "description": "Max matches (default 50)"},
            },
            "required": ["pattern", "path"],
        },
    },
    {
        "name": "glob_find",
        "description": "Find files by glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. '**/*.yaml')"},
                "path": {"type": "string", "description": "Root directory to search from"},
            },
            "required": ["pattern", "path"],
        },
    },
]


def execute_search_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute search tools."""
    if name == "grep_search":
        args = ["rg", "--no-heading", "--line-number"]
        if inputs.get("case_insensitive"):
            args.append("-i")
        if inputs.get("context"):
            args.extend(["-C", str(inputs["context"])])
        if inputs.get("glob"):
            args.extend(["--glob", inputs["glob"]])
        max_r = inputs.get("max_results", 50)
        args.extend(["--max-count", str(max_r)])
        args.append(inputs["pattern"])
        args.append(str(Path(inputs["path"]).expanduser()))

        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=15)
            output = r.stdout.strip()
            if not output and r.returncode == 1:
                return "No matches found."
            return output[:10000] or "No matches found."
        except FileNotFoundError:
            # Fallback to grep if rg not available
            args = ["grep", "-rn"]
            if inputs.get("case_insensitive"):
                args.append("-i")
            if inputs.get("glob"):
                args.extend(["--include", inputs["glob"]])
            args.append(inputs["pattern"])
            args.append(str(Path(inputs["path"]).expanduser()))
            try:
                r = subprocess.run(args, capture_output=True, text=True, timeout=15)
                return r.stdout.strip()[:10000] or "No matches found."
            except Exception as e:
                return f"Error: {e}"
        except Exception as e:
            return f"Error: {e}"

    elif name == "glob_find":
        p = Path(inputs["path"]).expanduser()
        try:
            matches = sorted(p.glob(inputs["pattern"]))[:200]
            if not matches:
                return "No files matched."
            lines = [str(m.relative_to(p)) for m in matches]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown search tool: {name}"
