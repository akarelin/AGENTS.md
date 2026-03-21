"""Git and GitHub CLI tools — git (757 calls) + gh (345 calls) in your history."""

import subprocess
from typing import Any

git_tool_defs = [
    {
        "name": "git_status",
        "description": "Get git status of a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to git repo"},
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "git_diff",
        "description": "Show git diff (staged, unstaged, or between refs).",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to git repo"},
                "ref": {"type": "string", "description": "Git ref or range (e.g. HEAD~3..HEAD)"},
                "staged": {"type": "boolean", "description": "Show staged changes"},
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "git_commit_push",
        "description": "Stage, commit, and optionally push changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to git repo"},
                "message": {"type": "string", "description": "Commit message"},
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to stage (default: all modified)",
                },
                "push": {"type": "boolean", "description": "Push after commit"},
            },
            "required": ["repo_path", "message"],
        },
    },
    {
        "name": "git_log",
        "description": "Show recent git log.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Path to git repo"},
                "count": {"type": "integer", "description": "Number of commits (default 10)"},
                "oneline": {"type": "boolean", "description": "One-line format"},
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "gh_cli",
        "description": "Run GitHub CLI command (PRs, issues, releases, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "gh command (e.g. 'pr list')"},
                "repo_path": {"type": "string", "description": "Repo context path"},
            },
            "required": ["command"],
        },
    },
]


def _run_git(args: list[str], cwd: str | None = None) -> str:
    """Run a git command."""
    try:
        r = subprocess.run(
            ["git"] + args, capture_output=True, text=True, cwd=cwd, timeout=30
        )
        out = r.stdout
        if r.stderr:
            out += f"\n{r.stderr}"
        return out.strip() or "(no output)"
    except Exception as e:
        return f"Error: {e}"


def execute_git_tool(name: str, inputs: dict[str, Any]) -> str:
    """Execute git tools."""
    repo = inputs.get("repo_path", ".")

    if name == "git_status":
        return _run_git(["status", "--short", "--branch"], cwd=repo)

    elif name == "git_diff":
        args = ["diff"]
        if inputs.get("staged"):
            args.append("--staged")
        if inputs.get("ref"):
            args.append(inputs["ref"])
        return _run_git(args, cwd=repo)

    elif name == "git_commit_push":
        files = inputs.get("files", ["."])
        _run_git(["add"] + files, cwd=repo)
        result = _run_git(["commit", "-m", inputs["message"]], cwd=repo)
        if inputs.get("push"):
            result += "\n" + _run_git(["push"], cwd=repo)
        return result

    elif name == "git_log":
        count = str(inputs.get("count", 10))
        fmt = ["--oneline"] if inputs.get("oneline") else ["--format=%h %s (%cr)"]
        return _run_git(["log", f"-{count}"] + fmt, cwd=repo)

    elif name == "gh_cli":
        cmd = inputs["command"]
        try:
            r = subprocess.run(
                f"gh {cmd}",
                shell=True,
                capture_output=True,
                text=True,
                cwd=inputs.get("repo_path"),
                timeout=30,
            )
            return (r.stdout + r.stderr).strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"

    return f"Unknown git tool: {name}"
