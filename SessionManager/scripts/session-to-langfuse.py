#!/usr/bin/env python3
"""
Claude Code / OpenClaw SessionEnd hook → Langfuse

Parses a Claude Code or OpenClaw (chmo) JSONL session file and ships it to
Langfuse as a trace with individual generations for each assistant turn.

Two modes:
  1. Hook mode (default): reads JSON from stdin (SessionEnd hook event)
  2. Backfill mode: --backfill [--since YYYY-MM-DD] [--project NAME] [file.jsonl]

When an OTEL trace already exists in Langfuse for the session, the script
upserts (enriches) it with metadata instead of creating a duplicate.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Langfuse config — override via env for different workspaces
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://langfuse.karelin.ai")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-xsolla-main-2026")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-xsolla-main-2026-secret-changeme")

# Session file locations
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"

# Log file for debugging
LOG_FILE = Path.home() / ".claude" / "hooks" / "langfuse-hook.log"


def log(msg):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except OSError:
        pass


def find_session_file(session_id: str) -> Path | None:
    """Find the JSONL file for a given session ID across all project dirs."""
    for jsonl_file in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
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
    """Parse a Claude Code or OpenClaw JSONL session into structured data."""
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
    # chmo-specific metadata
    provider = None
    thinking_level = None
    session_version = None

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

            # Normalise chmo format: type:"session" carries id/cwd,
            # type:"message" wraps role inside message.role
            if entry_type == "session":
                if not session_id and entry.get("id"):
                    session_id = entry["id"]
                if not session_cwd and entry.get("cwd"):
                    session_cwd = entry["cwd"]
                if entry.get("version"):
                    session_version = entry["version"]

            # chmo model_change and thinking_level_change entries
            if entry_type == "model_change":
                if entry.get("provider"):
                    provider = entry["provider"]
                if entry.get("modelId"):
                    model = entry["modelId"]
            if entry_type == "thinking_level_change":
                if entry.get("thinkingLevel"):
                    thinking_level = entry["thinkingLevel"]

            if not session_id and entry.get("sessionId"):
                session_id = entry["sessionId"]
            if not session_cwd and entry.get("cwd"):
                session_cwd = entry["cwd"]
            if not git_branch and entry.get("gitBranch"):
                git_branch = entry["gitBranch"]

            # Normalise chmo "message" entries into cc-style types
            if entry_type == "message":
                msg = entry.get("message", {})
                role = msg.get("role", "")
                if role == "user":
                    entry_type = "user"
                elif role == "assistant":
                    entry_type = "assistant"
                elif role in ("tool", "tool_result"):
                    entry_type = "tool_result"

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
                # Skip delivery-mirror entries (chmo channel echoes)
                if msg_model and "mirror" in str(msg_model):
                    continue
                if msg_model:
                    model = msg_model
                # Capture provider from chmo assistant messages
                if msg.get("provider"):
                    provider = msg["provider"]

                # Extract text content (skip thinking blocks)
                content_blocks = msg.get("content", [])
                text_parts = []
                tool_uses = []
                for block in content_blocks:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") in ("tool_use", "toolCall"):
                            tool_uses.append({
                                "name": block.get("name", block.get("toolName", "unknown")),
                                "input": block.get("input", block.get("args", {})),
                            })

                content = "\n".join(text_parts)

                # Token usage — handle both cc and chmo field names
                usage = msg.get("usage", {})
                input_tokens = usage.get("input_tokens", 0) or usage.get("input", 0)
                output_tokens = usage.get("output_tokens", 0) or usage.get("output", 0)
                cache_read = usage.get("cache_read_input_tokens", 0) or usage.get("cacheRead", 0)
                cache_create = usage.get("cache_creation_input_tokens", 0) or usage.get("cacheWrite", 0)
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
                    "provider": msg.get("provider") or provider,
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
                    "cost": msg.get("usage", {}).get("cost"),
                    "stop_reason": msg.get("stopReason"),
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

    # Detect source: chmo (openclaw) vs claude-code
    is_chmo = "openclaw" in str(jsonl_path)

    # Extract agent name from chmo path: .../agents/<name>/sessions/...
    agent_name = None
    if is_chmo:
        parts = jsonl_path.parts
        if "agents" in parts:
            agent_idx = parts.index("agents")
            if agent_idx + 1 < len(parts):
                agent_name = parts[agent_idx + 1]

    # Derive project name from agent name, cwd, or directory slug
    project_name = agent_name  # chmo: agent name is the project
    if not project_name and session_cwd:
        project_name = Path(session_cwd).name
    if not project_name:
        project_name = jsonl_path.parent.name.replace("-Users-alex-", "").replace("-", "/")

    return {
        "session_id": session_id or jsonl_path.stem,
        "source": "chmo" if is_chmo else "claude-code",
        "project": project_name,
        "agent": agent_name,
        "provider": provider,
        "thinking_level": thinking_level,
        "session_version": session_version,
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


# -- Langfuse helpers -------------------------------------------------------

def _langfuse_headers():
    """Build auth headers for Langfuse REST API."""
    import base64
    creds = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def _make_trace_id(session_id: str) -> str:
    """Deterministic trace ID from session ID."""
    import hashlib
    return hashlib.sha256(session_id.encode()).hexdigest()[:32]


def _make_obs_id(session_id: str, kind: str, index: int = 0) -> str:
    """Deterministic observation ID. Keeps deposits idempotent: re-depositing
    the same JSONL upserts the same observation rows instead of appending
    duplicates."""
    import hashlib
    key = f"{session_id}:{kind}:{index}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def find_otel_traces(session_id: str) -> list[str]:
    """Find all existing OTEL traces for a sessionId. Returns list of trace IDs.

    Claude Code emits one OTEL trace per user prompt (claude_code.interaction),
    all sharing the same sessionId — so a session usually has many bare OTEL
    traces that need enrichment, not just one. We page through results and
    return every trace whose metadata is OTEL-shaped (no top-level "source"
    key, which the hook always sets when it creates traces itself).
    """
    import urllib.parse
    import urllib.request

    found: list[str] = []
    page = 1
    while True:
        params = urllib.parse.urlencode({
            "sessionId": session_id,
            "limit": 100,
            "page": page,
        })
        url = f"{LANGFUSE_HOST}/api/public/traces?{params}"
        req = urllib.request.Request(url, headers=_langfuse_headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            log(f"find_otel_traces: error querying Langfuse page {page}: {e}")
            break

        rows = data.get("data", []) or []
        if not rows:
            break

        for trace in rows:
            metadata = trace.get("metadata") or {}
            # OTEL traces have no top-level "source" key (hook-created ones do).
            if not metadata.get("source"):
                found.append(trace["id"])

        meta = data.get("meta") or {}
        total_pages = meta.get("totalPages") or 1
        if page >= total_pages:
            break
        page += 1

    return found


def find_otel_trace(session_id: str) -> str | None:
    """Backwards-compatible single-trace lookup. Returns first OTEL trace ID."""
    traces = find_otel_traces(session_id)
    return traces[0] if traces else None


def _build_trace_body(session: dict, trace_id: str) -> dict:
    """Build the trace body dict used in both upsert and full-create paths."""
    source = session.get("source", "claude-code")
    project = session["project"] or "unknown"

    tags = [source, project]
    if session.get("agent"):
        tags.append(f"agent:{session['agent']}")
    if session.get("git_branch"):
        tags.append(f"branch:{session['git_branch']}")

    start_ts = session["start_time"].isoformat() if session["start_time"] else None

    return {
        "id": trace_id,
        "name": f"{source}: {project}",
        "timestamp": start_ts,
        "userId": "alex",
        "sessionId": session["session_id"],
        "tags": tags,
        "input": session["messages"][0]["content"][:3000] if session["messages"] else None,
        "output": session["messages"][-1]["content"][:3000] if session["messages"] else None,
        "metadata": {
            "source": source,
            "project": project,
            "agent": session.get("agent"),
            "provider": session.get("provider"),
            "thinking_level": session.get("thinking_level"),
            "session_version": session.get("session_version"),
            "cwd": session["cwd"],
            "model": session["model"],
            "git_branch": session["git_branch"],
            "file": session["file"],
            "total_generations": len(session["generations"]),
            "total_messages": len(session["messages"]),
            "total_input_tokens": session["total_input_tokens"],
            "total_output_tokens": session["total_output_tokens"],
        },
    }


_INGEST_MAX_BYTES = 3 * 1024 * 1024  # Langfuse ingestion endpoint rejects payloads
                                     # >~4 MB; stay under that with headroom.
_INGEST_MAX_EVENTS = 100             # Soft cap on events per POST.


def _post_ingestion(events: list):
    """POST a single ingestion batch."""
    import urllib.request

    body = json.dumps({"batch": events}).encode()
    req = urllib.request.Request(
        f"{LANGFUSE_HOST}/api/public/ingestion",
        data=body, headers=_langfuse_headers(), method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()


def _send_batch(batch: list):
    """Send events to Langfuse, splitting into chunks under size + count caps.

    Sessions with hundreds of generations exceed Langfuse's ingestion payload
    limit if posted as a single batch. We greedily pack events until the next
    one would push us over either bound, then flush.
    """
    chunk: list = []
    chunk_size = 2  # account for `{"batch":[]}` envelope

    for ev in batch:
        ev_bytes = len(json.dumps(ev).encode()) + 1  # +1 for the comma separator
        if chunk and (
            chunk_size + ev_bytes > _INGEST_MAX_BYTES
            or len(chunk) >= _INGEST_MAX_EVENTS
        ):
            _post_ingestion(chunk)
            chunk = []
            chunk_size = 2
        chunk.append(ev)
        chunk_size += ev_bytes

    if chunk:
        _post_ingestion(chunk)


def ship_to_langfuse(session: dict, force_full: bool = False):
    """Ship parsed session to Langfuse, upserting an existing OTEL trace if found.

    Path 1 (OTEL trace found, force_full=False): send a single trace-create upsert with metadata.
            Skip span/generation creation — OTEL already has those with accurate timing.
            Use datetime.now() as event timestamp so the upsert wins ClickHouse merge ordering.

    Path 2 (no OTEL trace, OR force_full=True): create full trace + span + generations
            with a deterministic trace ID derived from session_id. Use force_full when
            the OTEL upsert path silently drops trace-level fields (Langfuse OTEL-vs-
            ingestion-API merge limitation), or for fresh backfills.
    """
    import uuid

    source = session.get("source", "claude-code")

    # Try to find existing OTEL traces for this session, unless force_full bypasses.
    # Claude Code emits one OTEL trace per interaction, all sharing the sessionId.
    otel_trace_ids = [] if force_full else find_otel_traces(session["session_id"])

    if otel_trace_ids:
        # -- Path 1: upsert every OTEL trace with the session metadata --
        now_iso = datetime.now(timezone.utc).isoformat()  # CURRENT time wins ClickHouse merge ordering
        batch = [
            {
                "id": str(uuid.uuid4()),
                "type": "trace-create",
                "timestamp": now_iso,
                "body": _build_trace_body(session, tid),
            }
            for tid in otel_trace_ids
        ]
        _send_batch(batch)
        log(
            f"Upserted {len(otel_trace_ids)} OTEL trace(s) for session "
            f"{session['session_id']}: {otel_trace_ids[:3]}{'...' if len(otel_trace_ids) > 3 else ''}"
        )
        return

    # -- Path 2: no OTEL trace — full creation --
    trace_id = _make_trace_id(session["session_id"])
    start_ts = session["start_time"].isoformat() if session["start_time"] else None
    end_ts = session["end_time"].isoformat() if session["end_time"] else None

    batch = []

    # Trace event
    trace_body = _build_trace_body(session, trace_id)
    batch.append({
        "id": str(uuid.uuid4()),
        "type": "trace-create",
        "timestamp": start_ts,
        "body": trace_body,
    })

    # Root span covering the whole session (deterministic ID = idempotent)
    span_id = _make_obs_id(session["session_id"], "span", 0)
    batch.append({
        "id": str(uuid.uuid4()),
        "type": "span-create",
        "timestamp": start_ts,
        "body": {
            "id": span_id,
            "traceId": trace_id,
            "name": f"{source}: {session['project'] or 'unknown'}",
            "startTime": start_ts,
            "endTime": end_ts,
            "input": session["messages"][0]["content"][:3000] if session["messages"] else None,
            "output": session["messages"][-1]["content"][:3000] if session["messages"] else None,
            "metadata": {
                "total_generations": len(session["generations"]),
                "total_messages": len(session["messages"]),
                "total_input_tokens": session["total_input_tokens"],
                "total_output_tokens": session["total_output_tokens"],
            },
        },
    })

    # Generation events for each assistant turn
    for i, gen in enumerate(session["generations"]):
        output = gen["output"]
        if gen["tool_uses"]:
            tool_summary = "\n".join(
                f"[tool: {t['name']}]" for t in gen["tool_uses"]
            )
            output = f"{output}\n\n{tool_summary}" if output else tool_summary

        usage = {}
        if gen["usage"]:
            input_tokens = gen["usage"].get("input_tokens", 0)
            output_tokens = gen["usage"].get("output_tokens", 0)
            cache_read = gen["usage"].get("cache_read_input_tokens", 0)
            cache_create = gen["usage"].get("cache_creation_input_tokens", 0)
            usage = {"input": input_tokens, "output": output_tokens}
            if cache_read:
                usage["cache_read_input_tokens"] = cache_read
            if cache_create:
                usage["cache_creation_input_tokens"] = cache_create

        gen_ts = gen.get("timestamp") or start_ts

        batch.append({
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": gen_ts,
            "body": {
                "id": _make_obs_id(session["session_id"], "gen", i),
                "traceId": trace_id,
                "parentObservationId": span_id,
                "name": f"turn-{i + 1}",
                "startTime": gen_ts,
                "endTime": gen_ts,
                "model": gen["model"],
                "input": gen["input"][:2000] if gen["input"] else None,
                "output": output[:5000] if output else None,
                "usage": usage if usage else None,
                "metadata": {
                    "source": source,
                    "provider": gen.get("provider"),
                    "stop_reason": gen.get("stop_reason"),
                    "cost": gen.get("cost"),
                    "request_id": gen["request_id"],
                    "tool_calls": [t["name"] for t in gen["tool_uses"]] if gen["tool_uses"] else None,
                },
            },
        })

    _send_batch(batch)
    log(f"Shipped session {session['session_id']} to Langfuse ({len(session['generations'])} generations)")


# -- Backfill ----------------------------------------------------------------

def collect_jsonl_files(project_filter: str | None = None) -> list[Path]:
    """Collect all JSONL session files from Claude Code and OpenClaw directories."""
    files = []

    # Claude Code sessions
    if CLAUDE_PROJECTS_DIR.exists():
        for f in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
            if project_filter and project_filter.lower() not in str(f).lower():
                continue
            files.append(f)

    # OpenClaw sessions
    if OPENCLAW_AGENTS_DIR.exists():
        for f in OPENCLAW_AGENTS_DIR.rglob("*.jsonl"):
            if project_filter and project_filter.lower() not in str(f).lower():
                continue
            files.append(f)

    return sorted(files, key=lambda p: p.stat().st_mtime)


def backfill(args):
    """Backfill mode: process JSONL files and ship to Langfuse."""
    deposited = 0
    skipped = 0
    failed = 0

    since_dt = None
    if args.since:
        since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Determine files to process
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"File not found: {p}", file=sys.stderr)
            sys.exit(1)
        files = [p]
    else:
        files = collect_jsonl_files(project_filter=args.project)

    print(f"Found {len(files)} JSONL files to process")

    for jsonl_path in files:
        try:
            session = parse_session(jsonl_path)

            # Filter by --since using parsed session start_time
            if since_dt and session["start_time"]:
                if session["start_time"] < since_dt:
                    continue
            # If start_time is None and --since is set, skip (can't determine age)
            if since_dt and not session["start_time"]:
                continue

            if not session["generations"]:
                skipped += 1
                continue

            ship_to_langfuse(session, force_full=args.force_full)
            deposited += 1
            print(f"  deposited: {session['source']}: {session['project']} ({len(session['generations'])} gens) — {jsonl_path.name}")

        except Exception as e:
            failed += 1
            print(f"  FAILED: {jsonl_path.name} — {e}", file=sys.stderr)
            log(f"Backfill error for {jsonl_path}: {e}")

    print(f"\nSummary: {deposited} deposited, {skipped} skipped (no generations), {failed} failed")


# -- Hook mode (stdin) -------------------------------------------------------

def hook_mode():
    """Default mode: read SessionEnd hook event from stdin."""
    try:
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
            log("No generations found in session. Skipping.")
            return

        ship_to_langfuse(session)
        log("Done.")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        log(traceback.format_exc())


# -- CLI entrypoint ----------------------------------------------------------

def main():
    # Quick check: if no args at all, run in hook mode (backwards compatible)
    if len(sys.argv) == 1:
        hook_mode()
        return

    parser = argparse.ArgumentParser(
        description="Ship Claude Code / OpenClaw sessions to Langfuse",
    )
    parser.add_argument(
        "--backfill", action="store_true",
        help="Backfill mode: scan session directories and deposit to Langfuse",
    )
    parser.add_argument(
        "--since", type=str, default=None,
        help="Only process sessions starting on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--project", type=str, default=None,
        help="Filter files by project name substring",
    )
    parser.add_argument(
        "--force-full", dest="force_full", action="store_true",
        help="Always create full trace + span + generations with a deterministic "
             "ID derived from session_id, bypassing the OTEL-trace upsert path. "
             "Use when the OTEL upsert silently drops trace-level fields.",
    )
    parser.add_argument(
        "file", nargs="?", default=None,
        help="Specific JSONL file to deposit (backfill mode only)",
    )

    args = parser.parse_args()

    if args.backfill or args.file:
        backfill(args)
    else:
        # Unknown args but not backfill — fall back to hook mode
        hook_mode()


if __name__ == "__main__":
    main()
