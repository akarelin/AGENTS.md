"""SSH tools — 786 ssh calls in your history, multi-machine is core to your workflow."""

import subprocess
from typing import Any

ssh_tool_defs = [
    {
        "name": "ssh_exec",
        "description": "Execute command on remote host via SSH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "SSH host alias (e.g. 'five', 'seven')"},
                "command": {"type": "string", "description": "Command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
            },
            "required": ["host", "command"],
        },
    },
    {
        "name": "ssh_batch",
        "description": "Execute same command on multiple hosts in parallel.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hosts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of SSH host aliases",
                },
                "command": {"type": "string", "description": "Command to execute on all hosts"},
                "timeout": {"type": "integer", "description": "Timeout per host (default 30)"},
            },
            "required": ["hosts", "command"],
        },
    },
    {
        "name": "ssh_copy",
        "description": "Copy file to/from remote host via SCP.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path (host:path or local path)"},
                "dest": {"type": "string", "description": "Destination path (host:path or local path)"},
            },
            "required": ["source", "dest"],
        },
    },
]


def _ssh_run(host: str, command: str, timeout: int = 30) -> str:
    """Run command on host via SSH."""
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", host, command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = r.stdout
        if r.stderr:
            out += f"\nSTDERR: {r.stderr}"
        if r.returncode != 0:
            out += f"\nExit code: {r.returncode}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[{host}] Timed out after {timeout}s"
    except Exception as e:
        return f"[{host}] Error: {e}"


def execute_ssh_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute SSH tools."""
    if name == "ssh_exec":
        return _ssh_run(inputs["host"], inputs["command"], inputs.get("timeout", 30))

    elif name == "ssh_batch":
        # Sequential for now — could parallelize with threads
        results = []
        timeout = inputs.get("timeout", 30)
        for host in inputs["hosts"]:
            result = _ssh_run(host, inputs["command"], timeout)
            results.append(f"[{host}]\n{result}")
        return "\n\n".join(results)

    elif name == "ssh_copy":
        try:
            r = subprocess.run(
                ["scp", "-o", "ConnectTimeout=5", inputs["source"], inputs["dest"]],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode == 0:
                return f"Copied {inputs['source']} -> {inputs['dest']}"
            return f"SCP failed: {r.stderr}"
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown SSH tool: {name}"
