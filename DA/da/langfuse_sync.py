#!/usr/bin/env python3
"""
Claude Code SessionEnd hook → Langfuse
Parses a Claude Code JSONL session file and ships it to Langfuse as a trace
with individual generations for each assistant turn.

Receives JSON on stdin from the SessionEnd hook event.
"""

import json
import os
import sys
import glob
from datetime import datetime, timezone
from pathlib import Path

# Langfuse config
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://langfuse.karelin.ai")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-xsolla-main-2026")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-xsolla-main-2026-secret-changeme")

# Claude Code session storage
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Log file for debugging
LOG_FILE = Path.home() / ".claude" / "hooks" / "langfuse-hook.log"


def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def find_session_file(session_id: str) -> Path | None:
    """Find the JSONL file for a given session ID across all project dirs."""
    for jsonl_file in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
        # Check if filename matches session ID
        if jsonl_file.stem == session_id:
            return jsonl_file
    # Also check by reading first few lines for sessionId field
    for jsonl_file in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
        try:
            with open(jsonl_file) as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get("sessionId") == session_id:
                        return jsonl_file
                    break  # Only check first line
        except (json.JSONDecodeError, OSError):
            continue
    return None


def parse_session(jsonl_path: Path) -> dict:
    """Parse a Claude Code JSONL session into structured data."""
    messages = []
    session_id = None
    session_cwd = None
    model = None
    git_branch = None
    start_time = None
    end_time = None
    total_input_tokens = 0
    total_output_tokens = 0
    generations = []

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type")
            timestamp = entry.get("timestamp")

            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]
            if not session_cwd and entry.get("cwd"):
                session_cwd = entry["cwd"]
            if not git_branch and entry.get("gitBranch"):
                git_branch = entry["gitBranch"]

            if timestamp:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if start_time is None or ts < start_time:
                    start_time = ts
                if end_time is None or ts > end_time:
                    end_time = ts

            # User messages
            if entry_type == "user":
                msg = entry.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, list):
                    # Extract text from content blocks
                    content = "\n".join(
                        block.get("text", str(block))
                        for block in content
                        if isinstance(block, dict)
                    )
                messages.append({
                    "role": "user",
                    "content": content,
                    "timestamp": timestamp,
                })

            # Assistant messages (generations)
            elif entry_type == "assistant":
                msg = entry.get("message", {})
                msg_model = msg.get("model", model)
                if msg_model:
                    model = msg_model

                # Extract text content (skip thinking blocks)
                content_blocks = msg.get("content", [])
                text_parts = []
                tool_uses = []
                for block in content_blocks:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_uses.append({
                                "name": block.get("name", "unknown"),
                                "input": block.get("input", {}),
                            })

                content = "\n".join(text_parts)

                # Token usage
                usage = msg.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_create = usage.get("cache_creation_input_tokens", 0)
                total_input_tokens += input_tokens + cache_read + cache_create
                total_output_tokens += output_tokens

                # Find the preceding user message for this generation
                last_user_msg = ""
                for m in reversed(messages):
                    if m["role"] == "user":
                        last_user_msg = m["content"]
                        break

                gen = {
                    "model": msg_model,
                    "input": last_user_msg,
                    "output": content,
                    "tool_uses": tool_uses,
                    "timestamp": timestamp,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_read_input_tokens": cache_read,
                        "cache_creation_input_tokens": cache_create,
                    },
                    "request_id": entry.get("requestId"),
                }
                generations.append(gen)

                messages.append({
                    "role": "assistant",
                    "content": content,
                    "timestamp": timestamp,
                })

            # Tool results
            elif entry_type == "tool_result":
                msg = entry.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        block.get("text", str(block))
                        for block in content
                        if isinstance(block, dict)
                    )
                messages.append({
                    "role": "tool",
                    "content": content[:500],  # Truncate tool outputs
                    "timestamp": timestamp,
                })

    # Derive project name from cwd or directory
    project_name = None
    if session_cwd:
        project_name = Path(session_cwd).name
    if not project_name:
        # Use the project directory slug
        project_name = jsonl_path.parent.name.replace("-Users-alex-", "").replace("-", "/")

    return {
        "session_id": session_id or jsonl_path.stem,
        "project": project_name,
        "cwd": session_cwd,
        "model": model,
        "git_branch": git_branch,
        "start_time": start_time,
        "end_time": end_time,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "generations": generations,
        "messages": messages,
        "file": str(jsonl_path),
    }


def ship_to_langfuse(session: dict):
    """Ship parsed session to Langfuse using SDK v4 (OpenTelemetry-based)."""
    from langfuse import Langfuse, propagate_attributes

    langfuse = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
    )

    # Generate a deterministic trace ID from the session ID
    trace_id = Langfuse.create_trace_id(seed=session["session_id"])

    project = session["project"] or "unknown"
    tags = ["claude-code", project]
    if session.get("git_branch"):
        tags.append(f"branch:{session['git_branch']}")

    # Create a root span as the trace, with session/user propagation
    with propagate_attributes(
        user_id="alex",
        session_id=session["session_id"],
        tags=tags,
        trace_name=f"claude-code: {project}",
        metadata={
            "source": "claude-code",
            "project": project,
            "cwd": session["cwd"],
            "model": session["model"],
            "git_branch": session["git_branch"],
            "file": session["file"],
        },
    ):
        with langfuse.start_as_current_observation(
            name=f"claude-code: {project}",
            as_type="span",
            input=session["messages"][0]["content"][:3000] if session["messages"] else None,
            output=session["messages"][-1]["content"][:3000] if session["messages"] else None,
            metadata={
                "total_generations": len(session["generations"]),
                "total_messages": len(session["messages"]),
                "total_input_tokens": session["total_input_tokens"],
                "total_output_tokens": session["total_output_tokens"],
            },
        ) as root_span:
            # Create generations for each assistant turn
            for i, gen in enumerate(session["generations"]):
                output = gen["output"]
                if gen["tool_uses"]:
                    tool_summary = "\n".join(
                        f"[tool: {t['name']}]" for t in gen["tool_uses"]
                    )
                    if output:
                        output = f"{output}\n\n{tool_summary}"
                    else:
                        output = tool_summary

                usage_details = {}
                if gen["usage"]:
                    input_tokens = gen["usage"].get("input_tokens", 0)
                    output_tokens = gen["usage"].get("output_tokens", 0)
                    cache_read = gen["usage"].get("cache_read_input_tokens", 0)
                    cache_create = gen["usage"].get("cache_creation_input_tokens", 0)

                    usage_details = {
                        "input": input_tokens,
                        "output": output_tokens,
                    }
                    if cache_read:
                        usage_details["cache_read_input_tokens"] = cache_read
                    if cache_create:
                        usage_details["cache_creation_input_tokens"] = cache_create

                gen_obs = langfuse.start_observation(
                    name=f"turn-{i + 1}",
                    as_type="generation",
                    model=gen["model"],
                    input=gen["input"][:2000] if gen["input"] else None,
                    output=output[:5000] if output else None,
                    usage_details=usage_details if usage_details else None,
                    metadata={
                        "request_id": gen["request_id"],
                        "tool_calls": [t["name"] for t in gen["tool_uses"]] if gen["tool_uses"] else None,
                    },
                )
                gen_obs.end()

    langfuse.flush()
    log(f"Shipped session {session['session_id']} to Langfuse ({len(session['generations'])} generations)")


def main():
    try:
        # Read hook input from stdin
        stdin_data = sys.stdin.read()
        log(f"Hook fired. stdin: {stdin_data[:500]}")

        hook_input = json.loads(stdin_data) if stdin_data.strip() else {}

        session_id = hook_input.get("session_id") or hook_input.get("sessionId")
        session_file = hook_input.get("session_file")

        # Try to find the session file
        jsonl_path = None
        if session_file:
            jsonl_path = Path(session_file)
        elif session_id:
            jsonl_path = find_session_file(session_id)

        if not jsonl_path or not jsonl_path.exists():
            log(f"Session file not found for session_id={session_id}, file={session_file}")
            # Try to find the most recently modified JSONL as fallback
            all_jsonl = sorted(
                CLAUDE_PROJECTS_DIR.rglob("*.jsonl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if all_jsonl:
                jsonl_path = all_jsonl[0]
                log(f"Falling back to most recent JSONL: {jsonl_path}")
            else:
                log("No JSONL files found at all. Exiting.")
                return

        log(f"Parsing session from {jsonl_path}")
        session = parse_session(jsonl_path)

        if not session["generations"]:
            log(f"No generations found in session. Skipping.")
            return

        ship_to_langfuse(session)
        log("Done.")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        log(traceback.format_exc())


if __name__ == "__main__":
    main()
