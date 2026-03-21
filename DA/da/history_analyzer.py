"""Claude Code history analyzer — extracts patterns from your .claude directory.

Analyzes 7,042 history entries and 157,800 session lines across 10 machines.
Used to derive agent specializations and tool priorities.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_jsonl(path: Path) -> list[dict]:
    """Parse JSONL file, skip bad lines."""
    items = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return items


def analyze_history(claude_dir: str) -> dict[str, Any]:
    """Full analysis of Claude Code history directory."""
    claude_path = Path(claude_dir)
    if not claude_path.exists():
        return {"error": f"Directory not found: {claude_dir}"}

    results: dict[str, Any] = {
        "machines": [],
        "total_prompts": 0,
        "projects": Counter(),
        "slash_commands": Counter(),
        "task_categories": Counter(),
        "tool_usage": Counter(),
        "bash_commands": Counter(),
        "file_types": Counter(),
        "workflow_patterns": Counter(),
        "session_count": 0,
    }

    # Analyze history.jsonl files
    for hf in claude_path.glob("*/history.jsonl"):
        machine = hf.parent.name
        results["machines"].append(machine)
        items = parse_jsonl(hf)

        for item in items:
            display = item.get("display", "")
            project = item.get("project", "")

            if project:
                results["projects"][project] += 1

            if display.startswith("/"):
                results["slash_commands"][display.split()[0]] += 1
            elif display and not display.startswith("<"):
                results["total_prompts"] += 1
                _categorize(display, results["task_categories"])

    # Analyze session files
    for sf in claude_path.glob("*/projects/*/*.jsonl"):
        results["session_count"] += 1
        items = parse_jsonl(sf)

        for item in items:
            msg = item.get("message", {})
            if item.get("type") == "assistant" and isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool = block.get("name", "unknown")
                            results["tool_usage"][tool] += 1
                            inp = block.get("input", {})
                            if isinstance(inp, dict):
                                if "command" in inp:
                                    cmd = inp["command"][:50].split()[0]
                                    results["bash_commands"][cmd] += 1
                                if "file_path" in inp:
                                    ext = Path(inp["file_path"]).suffix
                                    if ext:
                                        results["file_types"][ext] += 1

    return results


def _categorize(text: str, counter: Counter) -> None:
    """Categorize a prompt into task types."""
    lower = text.lower()
    categories = {
        "git": ["git", "commit", "push", "pull", "merge", "branch", "rebase"],
        "files": ["file", "move", "copy", "rename", "delete", "create", "mkdir"],
        "debug": ["fix", "bug", "error", "debug", "broken", "issue", "wrong", "fail"],
        "deploy": ["deploy", "docker", "server", "nginx", "ssl", "service", "container"],
        "code": ["implement", "write", "add", "build", "make", "generate"],
        "config": ["config", "setup", "install", "configure", "setting", "env", "dotfile"],
        "docs": ["document", "changelog", "readme", "describe", "explain"],
        "research": ["analyze", "research", "compare", "review", "check", "look", "find", "search"],
        "homeauto": ["home", "assistant", "hass", "appdaemon", "automation", "sensor"],
        "pipeline": ["etl", "pipeline", "airflow", "dag", "ingest", "transform", "data"],
        "network": ["network", "firewall", "vpn", "wireguard", "ssh", "proxy"],
        "sync": ["sync", "backup", "rsync", "dotfile", "chezmoi"],
    }
    for cat, kws in categories.items():
        if any(kw in lower for kw in kws):
            counter[cat] += 1
            return
    counter["other"] += 1


def format_report(results: dict[str, Any]) -> str:
    """Format analysis results as markdown report."""
    if "error" in results:
        return f"Error: {results['error']}"

    lines = [
        "# Claude Code History Analysis",
        f"\n**Machines:** {', '.join(results['machines'])}",
        f"**Total Prompts:** {results['total_prompts']}",
        f"**Sessions Analyzed:** {results['session_count']}",
        "\n## Top Projects",
    ]
    for proj, count in results["projects"].most_common(15):
        lines.append(f"- {proj}: {count}")

    lines.append("\n## Task Categories")
    for cat, count in results["task_categories"].most_common():
        lines.append(f"- {cat}: {count}")

    lines.append("\n## Tool Usage (Top 15)")
    for tool, count in results["tool_usage"].most_common(15):
        lines.append(f"- {tool}: {count}")

    lines.append("\n## Bash Commands (Top 15)")
    for cmd, count in results["bash_commands"].most_common(15):
        lines.append(f"- {cmd}: {count}")

    lines.append("\n## File Types (Top 10)")
    for ext, count in results["file_types"].most_common(10):
        lines.append(f"- {ext}: {count}")

    return "\n".join(lines)
