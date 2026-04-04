#!/usr/bin/env python3
"""
lf — Langfuse session management CLI

Commands:
  session resume [search]           List & resume sessions (interactive)
  session rename <target> <name>    Rename a session
  session merge <id1> <id2> [...]   Merge multiple sessions into one trace
  session archive <target>          Archive (tag as archived, hide from default list)
  session deposit <file|id>         Push a local JSONL to Langfuse
  session deposit-all               Push all local sessions to Langfuse

  project list [name]               List sessions for a project
  project combine <project>         Combine all sessions for a project into one view
  project associate <target> <proj> Associate a session with a project
"""

import json
import os
import sys
import glob
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# --- Config ---

LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://langfuse.karelin.ai")
LANGFUSE_PK = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-xsolla-main-2026")
LANGFUSE_SK = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-xsolla-main-2026-secret-changeme")
LANGFUSE_SSH = os.environ.get("LANGFUSE_SSH", "alex@34.162.201.120")
LANGFUSE_COMPOSE_DIR = os.environ.get("LANGFUSE_COMPOSE_DIR", "~/langfuse")

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"

# --- HTTP helpers ---

import urllib.request
import urllib.error
import base64


def _auth_header():
    creds = base64.b64encode(f"{LANGFUSE_PK}:{LANGFUSE_SK}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def api_get(path, params=None):
    url = f"{LANGFUSE_HOST}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url += f"?{qs}"
    req = urllib.request.Request(url, headers=_auth_header())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"❌ API error {e.code}: {body[:200]}", file=sys.stderr)
        sys.exit(1)


def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{LANGFUSE_HOST}{path}", data=body, headers=_auth_header(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"❌ API error {e.code}: {body[:200]}", file=sys.stderr)
        sys.exit(1)


def ingest_batch(events):
    """Send a batch of trace/generation events to Langfuse ingestion API."""
    return api_post("/api/public/ingestion", {"batch": events})


def ingest_trace_update(trace_id, **kwargs):
    """Upsert a trace (update name, tags, metadata, etc.).
    Note: trace-create upsert MERGES tags — it cannot remove them.
    Use clickhouse_set_tags() to replace tags entirely.
    """
    body = {"id": trace_id}
    body.update(kwargs)
    return ingest_batch([{
        "id": str(uuid.uuid4()),
        "type": "trace-create",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "body": body,
    }])


def clickhouse_set_tags(trace_id, tags):
    """Directly set tags in ClickHouse (replaces, not merges).
    Required for removing tags since the ingestion API only merges.
    """
    tags_str = "[" + ",".join(f"'{t}'" for t in tags) + "]"
    query = f"ALTER TABLE traces UPDATE tags = {tags_str} WHERE id = '{trace_id}'"
    cmd = f'ssh {LANGFUSE_SSH} "cd {LANGFUSE_COMPOSE_DIR} && docker compose exec -T clickhouse clickhouse-client --query \\"{query}\\""'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        print(f"⚠️  ClickHouse update failed: {result.stderr[:200]}", file=sys.stderr)
        return False
    # Optimize to merge versions
    opt_cmd = f'ssh {LANGFUSE_SSH} "cd {LANGFUSE_COMPOSE_DIR} && docker compose exec -T clickhouse clickhouse-client --query \\"OPTIMIZE TABLE traces FINAL\\""'
    subprocess.run(opt_cmd, shell=True, capture_output=True, text=True, timeout=15)
    return True


# --- Trace helpers ---

def fetch_traces(limit=50, tag=None):
    params = {"limit": str(limit)}
    data = api_get("/api/public/traces", params)
    traces = data.get("data", [])
    if tag:
        traces = [t for t in traces if tag in t.get("tags", [])]
    return traces


def fetch_trace(trace_id):
    return api_get(f"/api/public/traces/{trace_id}")


def resolve_target(target, traces=None):
    """Resolve 'last', '#N', or partial ID to a trace dict."""
    if traces is None:
        traces = fetch_traces(limit=30)

    # Filter out archived by default
    active = [t for t in traces if "archived" not in t.get("tags", [])]

    if target == "last" and active:
        return active[0]

    # Try as 1-indexed number
    try:
        idx = int(target) - 1
        if 0 <= idx < len(active):
            return active[idx]
    except ValueError:
        pass

    # Partial session/trace ID match
    for t in traces:  # search all, including archived
        sid = t.get("sessionId", "")
        tid = t.get("id", "")
        if sid.startswith(target) or tid.startswith(target):
            return t

    return None


def format_trace_line(i, t, show_project=False):
    name = t.get("name", "unnamed")[:38]
    skip_tags = {"claude-code", "openclaw", "codex", "archived"}
    tags = ", ".join([tg for tg in t.get("tags", []) if tg not in skip_tags])[:28]
    ts = t.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        when = dt.strftime("%b %d %H:%M")
    except:
        when = ts[:16]
    meta = t.get("metadata", {}) or {}
    tok_in = meta.get("total_input_tokens", 0) or 0
    tok_out = meta.get("total_output_tokens", 0) or 0
    tok = f" ({tok_in // 1000}k/{tok_out // 1000}k)" if tok_in else ""
    archived = " 📦" if "archived" in t.get("tags", []) else ""
    src = "cc" if "claude-code" in t.get("tags", []) else "oc" if "openclaw" in t.get("tags", []) else "??"
    return f"  {i:<4} [{src}] {name:<38} {tags:<28} {when}{tok}{archived}"


def print_trace_list(traces, title="Sessions"):
    if not traces:
        print("  No sessions found.")
        return
    print(f"\n  📋 {title} ({len(traces)} found)\n")
    print(f'  {"#":<4} {"src":<4} {"Name":<38} {"Tags":<28} {"When"}')
    print(f'  {"-" * 4} {"-" * 4} {"-" * 38} {"-" * 28} {"-" * 20}')
    for i, t in enumerate(traces, 1):
        print(format_trace_line(i, t))
    print()


# --- Session commands ---

def cmd_session_resume(args):
    """List recent sessions; interactively pick one to resume."""
    search = None
    source = None
    limit = 30
    show_archived = False

    i = 0
    while i < len(args):
        if args[i] == "--all":
            source = None
        elif args[i] == "--oc":
            source = "openclaw"
        elif args[i] == "--cc":
            source = "claude-code"
        elif args[i] == "--archived":
            show_archived = True
        elif args[i] == "--limit":
            i += 1
            limit = int(args[i])
        else:
            search = args[i]
        i += 1

    traces = fetch_traces(limit=limit, tag=source)

    # Filter archived
    if not show_archived:
        traces = [t for t in traces if "archived" not in t.get("tags", [])]

    # Search filter
    if search:
        search_l = search.lower()
        traces = [t for t in traces if search_l in f"{t.get('name','')} {' '.join(t.get('tags',[]))} {t.get('sessionId','')}".lower()]

    print_trace_list(traces)

    for i, t in enumerate(traces, 1):
        src = "cc" if "claude-code" in t.get("tags", []) else "oc" if "openclaw" in t.get("tags", []) else "??"
        print(f"  {i}. [{src}] {t.get('sessionId', '?')}")
    print()

    # Interactive picker
    if sys.stdin.isatty() and sys.stdout.isatty():
        pick = input("  Resume # (Enter to cancel): ").strip()
        if pick and pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(traces):
                t = traces[idx]
                sid = t.get("sessionId", "")
                if "claude-code" in t.get("tags", []):
                    print(f"  → claude --resume {sid}")
                    os.execvp("claude", ["claude", "--resume", sid])
                else:
                    print(f"  ⚠️  Not a Claude Code session")
                    print(f"  Session ID: {sid}")


def cmd_session_rename(args):
    """Rename a session. Usage: session rename <target> <new-name> [--tag t1 ...]"""
    if len(args) < 2:
        print("Usage: sm session rename <target> <new-name> [--tag t1 ...]")
        return

    target = args[0]
    new_name = None
    extra_tags = []

    i = 1
    while i < len(args):
        if args[i] == "--tag":
            i += 1
            extra_tags.append(args[i])
        else:
            new_name = args[i]
        i += 1

    trace = resolve_target(target)
    if not trace:
        print(f"❌ No trace matching '{target}'")
        return

    old_name = trace.get("name", "")
    display_name = new_name or old_name
    merged_tags = list(set(trace.get("tags", []) + extra_tags))

    ingest_trace_update(trace["id"], name=display_name, tags=merged_tags)
    print(f'✅ "{old_name}" → "{display_name}"')
    if extra_tags:
        print(f"   Tags: +{', '.join(extra_tags)}")
    print(f"   {LANGFUSE_HOST}/traces/{trace['id']}")


def cmd_session_merge(args):
    """Merge multiple sessions into one trace group.
    Creates a parent trace that links to all specified sessions.
    Usage: session merge <id1> <id2> [...] [--name "Merged name"]
    """
    if len(args) < 2:
        print("Usage: sm session merge <target1> <target2> [...] [--name name]")
        return

    targets = []
    merge_name = None
    i = 0
    while i < len(args):
        if args[i] == "--name":
            i += 1
            merge_name = args[i]
        else:
            targets.append(args[i])
        i += 1

    all_traces = fetch_traces(limit=50)
    resolved = []
    for t in targets:
        trace = resolve_target(t, all_traces)
        if trace:
            resolved.append(trace)
        else:
            print(f"⚠️  Could not find trace matching '{t}'")

    if len(resolved) < 2:
        print("❌ Need at least 2 valid sessions to merge")
        return

    # Create a merged session ID
    merged_session_id = f"merged-{uuid.uuid4().hex[:12]}"
    if not merge_name:
        names = [t.get("name", "unnamed") for t in resolved]
        merge_name = f"Merged: {' + '.join(names[:3])}"

    # Collect all tags
    all_tags = set()
    for t in resolved:
        all_tags.update(t.get("tags", []))
    all_tags.add("merged")

    # Collect project info
    projects = set()
    for t in resolved:
        meta = t.get("metadata", {}) or {}
        if meta.get("project"):
            projects.add(meta["project"])

    # Update all child traces to share the merged session ID
    events = []
    child_ids = []
    for t in resolved:
        child_ids.append(t["id"])
        events.append({
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "body": {
                "id": t["id"],
                "sessionId": merged_session_id,
                "tags": list(set(t.get("tags", []) + ["merged"])),
            },
        })

    ingest_batch(events)

    print(f"✅ Merged {len(resolved)} sessions")
    print(f"   Name: {merge_name}")
    print(f"   Session: {merged_session_id}")
    for t in resolved:
        print(f"   ← {t['id'][:16]}... ({t.get('name', 'unnamed')})")
    print(f"   {LANGFUSE_HOST}/sessions/{merged_session_id}")


def cmd_session_archive(args):
    """Archive a session (add 'archived' tag). Usage: session archive <target>"""
    if not args:
        print("Usage: sm session archive <target>")
        return

    target = args[0]
    unarchive = "--undo" in args

    all_traces = fetch_traces(limit=50)
    if unarchive:
        # Search including archived
        trace = resolve_target(target, all_traces)
    else:
        trace = resolve_target(target, all_traces)
    if not trace:
        # Fallback: search all including archived
        for t in all_traces:
            sid = t.get("sessionId", "")
            tid = t.get("id", "")
            if target == "last":
                trace = t  # last of all
                break
            if sid.startswith(target) or tid.startswith(target):
                trace = t
                break
    if not trace:
        print(f"❌ No trace matching '{target}'")
        return

    tags = set(trace.get("tags", []))
    if unarchive:
        tags.discard("archived")
        action = "Unarchived"
        # Must use ClickHouse to remove tags (ingestion API only merges)
        if not clickhouse_set_tags(trace["id"], list(tags)):
            print("❌ Failed to unarchive (ClickHouse update failed)")
            return
    else:
        tags.add("archived")
        action = "Archived"
        ingest_trace_update(trace["id"], tags=list(tags))

    print(f"📦 {action}: {trace.get('name', 'unnamed')}")
    print(f"   {LANGFUSE_HOST}/traces/{trace['id']}")


def cmd_session_deposit(args):
    """Deposit a session to Langfuse. Usage: session deposit <file|session-id|all>"""
    if not args:
        print("Usage: sm session deposit <jsonl-file|session-id|all>")
        return

    target = args[0]
    source = "claude-code"  # default
    if "--oc" in args or "--openclaw" in args:
        source = "openclaw"

    if target == "all":
        return cmd_session_deposit_all(args[1:])

    # Find the file
    path = Path(target)
    if path.exists() and path.suffix == ".jsonl":
        jsonl_path = path
    else:
        # Search by session ID
        jsonl_path = _find_session_file(target)

    if not jsonl_path:
        print(f"❌ Cannot find session file for '{target}'")
        return

    # Use the existing deposit script
    hook_script = Path.home() / ".claude" / "hooks" / "session-to-langfuse.py"
    venv_python = Path.home() / ".claude" / "hooks" / ".venv" / "bin" / "python3"

    result = subprocess.run(
        [str(venv_python), str(hook_script)],
        input=json.dumps({"session_file": str(jsonl_path)}),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode == 0:
        print(f"✅ Deposited: {jsonl_path.name}")
    else:
        print(f"❌ Failed: {result.stderr[:200]}")

    # Check log
    log_file = Path.home() / ".claude" / "hooks" / "langfuse-hook.log"
    if log_file.exists():
        lines = log_file.read_text().strip().split("\n")
        for line in lines[-3:]:
            if "Shipped" in line or "ERROR" in line:
                print(f"   {line}")


def cmd_session_deposit_all(args):
    """Deposit all local sessions to Langfuse."""
    sources = []

    # Claude Code sessions
    if "--oc" not in args:
        for f in CLAUDE_PROJECTS_DIR.rglob("*.jsonl"):
            sources.append(("cc", f))

    # OpenClaw sessions
    if "--cc" not in args:
        for f in OPENCLAW_AGENTS_DIR.rglob("*.jsonl"):
            if f.name.endswith(".jsonl") and ".reset." not in f.name:
                sources.append(("oc", f))

    print(f"  Found {len(sources)} session files")

    hook_script = Path.home() / ".claude" / "hooks" / "session-to-langfuse.py"
    venv_python = Path.home() / ".claude" / "hooks" / ".venv" / "bin" / "python3"

    ok = 0
    fail = 0
    for src, f in sources:
        try:
            result = subprocess.run(
                [str(venv_python), str(hook_script)],
                input=json.dumps({"session_file": str(f)}),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                ok += 1
                print(f"  ✅ [{src}] {f.name[:40]}")
            else:
                fail += 1
                print(f"  ❌ [{src}] {f.name[:40]}")
        except Exception as e:
            fail += 1
            print(f"  ❌ [{src}] {f.name[:40]}: {e}")

    print(f"\n  Done: {ok} deposited, {fail} failed")


# --- Project commands ---

def cmd_project_list(args):
    """List sessions grouped by project. Usage: project list [project-name]"""
    project_filter = args[0] if args else None
    traces = fetch_traces(limit=100)

    # Filter out archived
    traces = [t for t in traces if "archived" not in t.get("tags", [])]

    # Group by project
    by_project = {}
    for t in traces:
        meta = t.get("metadata", {}) or {}
        project = meta.get("project", "unknown")
        tags = t.get("tags", [])
        # Also check tags for project name
        for tag in tags:
            if tag not in ("claude-code", "openclaw", "codex", "archived", "merged") and not tag.startswith("branch:"):
                if not project or project == "unknown":
                    project = tag
        by_project.setdefault(project, []).append(t)

    if project_filter:
        pf = project_filter.lower()
        matching = {k: v for k, v in by_project.items() if pf in k.lower()}
        if not matching:
            print(f"  No sessions found for project '{project_filter}'")
            return
        by_project = matching

    print(f"\n  📁 Projects ({len(by_project)} found)\n")
    for project, sessions in sorted(by_project.items()):
        total_in = sum((s.get("metadata", {}) or {}).get("total_input_tokens", 0) or 0 for s in sessions)
        total_out = sum((s.get("metadata", {}) or {}).get("total_output_tokens", 0) or 0 for s in sessions)
        tok = f" ({total_in // 1000}k/{total_out // 1000}k tok)" if total_in else ""
        print(f"  📂 {project} — {len(sessions)} session(s){tok}")
        for s in sessions[:5]:
            name = s.get("name", "unnamed")[:50]
            ts = s.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                when = dt.strftime("%b %d %H:%M")
            except:
                when = "?"
            print(f"     └ {name} ({when})")
        if len(sessions) > 5:
            print(f"     └ ... and {len(sessions) - 5} more")
    print()


def cmd_project_combine(args):
    """Combine all sessions for a project under one Langfuse session ID.
    Usage: project combine <project-name> [--name "Custom name"]
    """
    if not args:
        print("Usage: sm project combine <project-name> [--name name]")
        return

    project = args[0]
    custom_name = None
    i = 1
    while i < len(args):
        if args[i] == "--name":
            i += 1
            custom_name = args[i]
        i += 1

    traces = fetch_traces(limit=100)
    matching = []
    for t in traces:
        meta = t.get("metadata", {}) or {}
        p = meta.get("project", "")
        tags = t.get("tags", [])
        if project.lower() in p.lower() or project.lower() in " ".join(tags).lower():
            matching.append(t)

    if not matching:
        print(f"  No sessions found for project '{project}'")
        return

    combined_session_id = f"project-{project.lower().replace(' ', '-')}"
    display_name = custom_name or f"Project: {project}"

    events = []
    for t in matching:
        events.append({
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "body": {
                "id": t["id"],
                "sessionId": combined_session_id,
            },
        })

    ingest_batch(events)

    print(f"✅ Combined {len(matching)} sessions under project '{project}'")
    print(f"   Session ID: {combined_session_id}")
    print(f"   {LANGFUSE_HOST}/sessions/{combined_session_id}")


def cmd_project_associate(args):
    """Associate a session with a project.
    Usage: project associate <target> <project-name>
    """
    if len(args) < 2:
        print("Usage: sm project associate <target> <project-name>")
        return

    target = args[0]
    project = args[1]

    trace = resolve_target(target)
    if not trace:
        print(f"❌ No trace matching '{target}'")
        return

    # Update metadata with project, add project as tag
    meta = trace.get("metadata", {}) or {}
    meta["project"] = project
    tags = list(set(trace.get("tags", []) + [project]))

    # Use session ID based on project
    project_session = f"project-{project.lower().replace(' ', '-')}"

    ingest_trace_update(trace["id"], metadata=meta, tags=tags, sessionId=project_session)

    print(f"✅ Associated '{trace.get('name', 'unnamed')}' → project '{project}'")
    print(f"   Session: {project_session}")
    print(f"   {LANGFUSE_HOST}/traces/{trace['id']}")


# --- File helpers ---

def _find_session_file(session_id):
    """Find JSONL by session ID in Claude Code or OpenClaw dirs."""
    for base in [CLAUDE_PROJECTS_DIR, OPENCLAW_AGENTS_DIR]:
        for f in base.rglob("*.jsonl"):
            if f.stem == session_id:
                return f
            if ".reset." in f.name:
                continue
            try:
                with open(f) as fh:
                    first = json.loads(fh.readline())
                    if first.get("sessionId") == session_id or first.get("id") == session_id:
                        return f
            except:
                continue
    return None


# --- CLI router ---

def cmd_session_local(args):
    """List local JSONL sessions (not yet deposited). Usage: session local [--cc|--oc]"""
    show_cc = "--oc" not in args
    show_oc = "--cc" not in args

    if show_cc:
        cc_files = sorted(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"\n  📁 Claude Code ({len(cc_files)} sessions)\n")
        for f in cc_files[:20]:
            project = f.parent.name.replace("-Users-alex-", "").replace("-", "/")
            size = f.stat().st_size
            size_h = f"{size // 1024}K" if size < 1048576 else f"{size / 1048576:.1f}M"
            sid = f.stem[:12]
            print(f"    {project:<35} {size_h:>6}  {sid}...")
        if len(cc_files) > 20:
            print(f"    ... and {len(cc_files) - 20} more")

    if show_oc and OPENCLAW_AGENTS_DIR.exists():
        print(f"\n  📁 OpenClaw\n")
        total = 0
        for agent_dir in sorted(OPENCLAW_AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir():
                continue
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue
            files = [f for f in sessions_dir.glob("*.jsonl") if ".reset." not in f.name]
            if files:
                total += len(files)
                print(f"    {agent_dir.name:<35} {len(files)} session(s)")
        print(f"\n    Total: {total}")

    print()


COMMANDS = {
    ("session", "local"): cmd_session_local,
    ("session", "resume"): cmd_session_resume,
    ("session", "rename"): cmd_session_rename,
    ("session", "merge"): cmd_session_merge,
    ("session", "archive"): cmd_session_archive,
    ("session", "deposit"): cmd_session_deposit,
    ("session", "deposit-all"): cmd_session_deposit_all,
    ("project", "list"): cmd_project_list,
    ("project", "list_sessions"): cmd_project_list,
    ("project", "combine"): cmd_project_combine,
    ("project", "combine_sessions"): cmd_project_combine,
    ("project", "associate"): cmd_project_associate,
    ("session", "associate_project"): cmd_project_associate,
}

# Short aliases
ALIASES = {
    "local": ("session", "local"),
    "resume": ("session", "resume"),
    "rename": ("session", "rename"),
    "merge": ("session", "merge"),
    "archive": ("session", "archive"),
    "deposit": ("session", "deposit"),
    "deposit-all": ("session", "deposit-all"),
    "projects": ("project", "list"),
    "combine": ("project", "combine"),
    "assoc": ("project", "associate"),
}


def print_help():
    print("""
  sm — Session & Project Manager

  Session commands:
    sm session resume [search]              List & resume sessions
    sm session rename <target> <name>       Rename a session
    sm session merge <t1> <t2> [...]        Merge sessions (shared session ID)
    sm session archive <target>             Archive (--undo to unarchive)
    sm session deposit <file|id|all>        Push local JSONL to Langfuse
    sm session deposit-all                  Push all local sessions

  Project commands:
    sm project list [name]                  List sessions by project
    sm project combine <project>            Group all project sessions
    sm project associate <target> <proj>    Associate session → project

  Shortcuts:
    sm local | resume | rename | merge | archive | deposit | projects | combine | assoc

  Targets: 'last' | '#N' (1-indexed) | partial session/trace ID

  Examples:
    sm resume                               # interactive session picker
    sm rename last "Sprint 3 cleanup"       # rename most recent
    sm merge last 2 --name "Full sprint"    # merge top 2 sessions
    sm archive 5ccbb62b                     # archive by partial ID
    sm deposit all                          # bulk upload everything
    sm projects                             # show project breakdown
    sm assoc last neuronet                  # tag session to project
""")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        print_help()
        return

    # Try 2-word command first
    if len(args) >= 2:
        key = (args[0], args[1])
        if key in COMMANDS:
            return COMMANDS[key](args[2:])

    # Try alias
    if args[0] in ALIASES:
        key = ALIASES[args[0]]
        return COMMANDS[key](args[1:])

    # Try single group (e.g., "sm session" → help)
    if args[0] in ("session", "project"):
        print_help()
        return

    print(f"Unknown command: {' '.join(args[:2])}")
    print_help()


if __name__ == "__main__":
    main()
