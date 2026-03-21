"""Docker tools — 926 docker bash calls in your history."""

import subprocess
from typing import Any

docker_tool_defs = [
    {
        "name": "docker_ps",
        "description": "List containers (running or all).",
        "input_schema": {
            "type": "object",
            "properties": {
                "all": {"type": "boolean", "description": "Include stopped containers"},
                "host": {"type": "string", "description": "Remote host (ssh alias) or local"},
            },
        },
    },
    {
        "name": "docker_compose",
        "description": "Run docker compose command in a project directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Compose action: up, down, restart, logs, ps, pull, build",
                },
                "project_dir": {"type": "string", "description": "Path to compose project"},
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific services (optional)",
                },
                "flags": {"type": "string", "description": "Extra flags (e.g. '-d', '--tail 50')"},
                "host": {"type": "string", "description": "Remote host (ssh alias) or local"},
            },
            "required": ["action", "project_dir"],
        },
    },
    {
        "name": "docker_exec",
        "description": "Execute command inside a running container.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "command": {"type": "string", "description": "Command to execute"},
                "host": {"type": "string", "description": "Remote host (ssh alias) or local"},
            },
            "required": ["container", "command"],
        },
    },
    {
        "name": "docker_logs",
        "description": "Get container logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Container name or ID"},
                "tail": {"type": "integer", "description": "Number of lines (default 50)"},
                "host": {"type": "string", "description": "Remote host (ssh alias) or local"},
            },
            "required": ["container"],
        },
    },
]


def _run(cmd: str, host: str | None = None, timeout: int = 30) -> str:
    """Run command locally or via SSH."""
    if host and host != "local":
        cmd = f"ssh {host} '{cmd}'"
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout
        if r.stderr:
            out += f"\n{r.stderr}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def execute_docker_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute docker tools."""
    host = inputs.get("host")

    if name == "docker_ps":
        flag = "-a" if inputs.get("all") else ""
        return _run(f"docker ps {flag} --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'", host)

    elif name == "docker_compose":
        action = inputs["action"]
        project = inputs["project_dir"]
        services = " ".join(inputs.get("services", []))
        flags = inputs.get("flags", "")
        return _run(f"cd {project} && docker compose {action} {flags} {services}", host, timeout=120)

    elif name == "docker_exec":
        container = inputs["container"]
        command = inputs["command"]
        return _run(f"docker exec {container} {command}", host)

    elif name == "docker_logs":
        container = inputs["container"]
        tail = inputs.get("tail", 50)
        return _run(f"docker logs --tail {tail} {container}", host)

    return f"Unknown docker tool: {name}"
