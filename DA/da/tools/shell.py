"""Shell execution tool — the #1 tool in your Claude Code usage (9,872 calls)."""

import subprocess
from typing import Any

shell_tool_defs = [
    {
        "name": "shell_exec",
        "description": "Execute a shell command locally. Returns stdout/stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (optional)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120)",
                },
            },
            "required": ["command"],
        },
    },
]


def execute_shell_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute shell command and return output."""
    command = inputs["command"]
    cwd = inputs.get("cwd")
    timeout = inputs.get("timeout", 120)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\nExit code: {result.returncode}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"
