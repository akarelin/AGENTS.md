#!/usr/bin/env python3
"""
sm-local — Interactive local session manager.

Run it. It scans, proposes, you decide.

Usage:
    sm-local                  # Full interactive scan + propose + act
    sm-local stats            # Just show stats
    sm-local name             # Just run LLM naming
    sm-local correlate        # Just run LLM correlation
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

TRASH_DIR = Path.home() / ".Trash"
SM_DIR = Path(__file__).resolve().parent.parent

# Source ID detection from folder names
SOURCE_IDS = {
    ".claude": ("cc", "Claude Code"),
    ".claude-vertex": ("cc", "Claude Code (Vertex)"),
    ".openclaw": ("oc", "OpenClaw"),
    ".codex": ("cx", "Codex"),
    ".continue": ("ct", "Continue"),
    ".cursor": ("cu", "Cursor"),
    ".gemini": ("gm", "Gemini"),
    ".aider": ("ai", "Aider"),
    ".codeium": ("ci", "Codeium"),
    "local-agent-mode-sessions": ("cd", "Claude Desktop"),
    "imported-chatgpt": ("gpt", "ChatGPT Export"),
    "imported-claude": ("cl", "Claude.ai Export"),
}

RULES_FILE = SM_DIR / "discovery_rules.yaml"


def load_discovery_rules():
    """Load discovery rules from YAML (preservator format)."""
    if RULES_FILE.exists():
        import yaml
        return yaml.safe_load(RULES_FILE.read_text()) or {}
    return {}


def discover_sessions(mode="quick"):
    """Discover all LLM session logs using rules (preservator pattern).
    
    mode: 'quick' (user home only) or 'exhaustive' (all drives)
    """
    rules = load_discovery_rules()
    skip_folders = set(rules.get("skip_folders", []))
    discovery_rules = rules.get("discovery_rules", [])

    # Determine search roots
    if mode == "quick":
        search_roots = [Path.home()]
    else:
        # All fixed drives
        search_roots = [Path("/")]

    found_files = []

    for rule in discovery_rules:
        search_mode = rule.get("search", {}).get(mode, "none")
        if search_mode == "none":
            continue

        find = rule.get("find", {})
        collect = rule.get("collect", {})
        find_type = find.get("type")

        if find_type == "folder_name":
            # Search for known folder names
            patterns = find.get("patterns", [])
            for root in search_roots:
                for folder_name in patterns:
                    candidates = []
                    # Direct check under home (fast)
                    direct = root / folder_name
                    if direct.exists():
                        candidates.append(direct)
                    # Also check platform-specific app dirs
                    for app_dir in [
                        root / "Library" / "Application Support",  # macOS
                        root / ".local" / "share",                 # Linux XDG
                        root / ".config",                          # Linux config
                    ]:
                        if app_dir.exists():
                            # Walk 3 levels deep in app dirs
                            for dirpath, dirnames, _ in os.walk(app_dir):
                                depth = str(dirpath).count(os.sep) - str(app_dir).count(os.sep)
                                if depth >= 3:
                                    dirnames.clear()
                                    continue
                                dirnames[:] = [d for d in dirnames if d not in skip_folders]
                                if folder_name in dirnames:
                                    candidates.append(Path(dirpath) / folder_name)
                    if search_mode != "user_home":
                        # Full walk for exhaustive mode
                        for dirpath, dirnames, _ in os.walk(root):
                            dirnames[:] = [d for d in dirnames if d not in skip_folders]
                            if folder_name in dirnames:
                                full = Path(dirpath) / folder_name
                                if full not in candidates:
                                    candidates.append(full)

                    for folder in candidates:
                        if not folder.exists():
                            continue
                        # Collect JSONL files
                        collect_patterns = collect.get("patterns", ["*.jsonl"])
                        exclude = collect.get("exclude", [])
                        for pattern in collect_patterns:
                            for f in folder.rglob(pattern):
                                if not f.is_file():
                                    continue
                                if any(exc in f.name for exc in exclude):
                                    continue
                                # Detect source
                                src_id, src_name = _detect_source(f, folder_name)
                                directory = _derive_directory(f, folder, src_id)
                                found_files.append((src_id, directory, f, src_name))

        elif find_type == "content_pattern" and mode == "exhaustive":
            # Content-based discovery (slow)
            extensions = set(find.get("file_extensions", [".jsonl"]))
            strong = find.get("strong_patterns", [])
            min_size = find.get("min_size", 500)

            for root in search_roots:
                for dirpath, dirnames, filenames in os.walk(root):
                    dirnames[:] = [d for d in dirnames if d not in skip_folders]
                    for fname in filenames:
                        if not any(fname.endswith(ext) for ext in extensions):
                            continue
                        fpath = Path(dirpath) / fname
                        try:
                            if fpath.stat().st_size < min_size:
                                continue
                            # Check content for LLM patterns
                            with open(fpath) as fh:
                                head = fh.read(2000)
                            if any(p in head for p in strong):
                                # Already found via folder rules?
                                if not any(f[2] == fpath for f in found_files):
                                    src_id, src_name = _detect_source(fpath)
                                    directory = fpath.parent.name
                                    found_files.append((src_id, directory, fpath, src_name))
                        except (OSError, UnicodeDecodeError):
                            continue

    return found_files


def _detect_source(file_path, folder_name=None):
    """Detect LLM source from path components."""
    parts = str(file_path).lower()
    if folder_name and folder_name in SOURCE_IDS:
        return SOURCE_IDS[folder_name]
    for name, (sid, sname) in SOURCE_IDS.items():
        if name in parts:
            return sid, sname
    return "??", "Unknown"


def _derive_directory(file_path, base_folder, src_id):
    """Derive a human-readable directory label."""
    if src_id == "cc":
        return file_path.parent.name.replace("-Users-alex-", "").replace("-home-alex-", "").replace("-", "/")
    elif src_id == "oc":
        # agents/<name>/sessions/<file> → agent name
        try:
            rel = file_path.relative_to(base_folder)
            return rel.parts[0] if len(rel.parts) > 2 else rel.parent.name
        except ValueError:
            return file_path.parent.parent.name
    elif src_id == "cd":
        try:
            rel = file_path.relative_to(base_folder)
            return rel.parts[0][:16] + "..." if rel.parts else "unknown"
        except ValueError:
            return file_path.parent.name
    else:
        return file_path.parent.name

VERTEX_PROJECT = os.environ.get("VERTEX_PROJECT", "ai-experiments-469513")
VERTEX_REGION = os.environ.get("VERTEX_REGION", "us-east5")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "claude-sonnet-4-6")



# ── Helpers ──────────────────────────────────────────────────────────────────

def format_size(size):
    if size < 1024:
        return f"{size}B"
    elif size < 1048576:
        return f"{size // 1024}K"
    else:
        return f"{size / 1048576:.1f}M"


def ask(prompt, options="yn", default=None):
    """Interactive single-char prompt."""
    opts = "/".join(o.upper() if o == default else o for o in options)
    while True:
        r = input(f"  {prompt} [{opts}] ").strip().lower()
        if not r and default:
            return default
        if r in options:
            return r


def ask_select(items, prompt="Pick #", allow_multi=False, allow_skip=True):
    """Let user pick from numbered list. Returns indices."""
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    if allow_skip:
        print(f"  0. Skip")
    print()
    while True:
        r = input(f"  {prompt}: ").strip()
        if not r or r == "0":
            return []
        if allow_multi:
            try:
                indices = []
                for part in r.replace(",", " ").split():
                    if "-" in part:
                        a, b = part.split("-", 1)
                        indices.extend(range(int(a) - 1, int(b)))
                    else:
                        indices.append(int(part) - 1)
                return [i for i in indices if 0 <= i < len(items)]
            except ValueError:
                pass
        else:
            try:
                idx = int(r) - 1
                if 0 <= idx < len(items):
                    return [idx]
            except ValueError:
                pass


def trash(path):
    """Move file to Trash."""
    dest = TRASH_DIR / path.name
    if dest.exists():
        dest = TRASH_DIR / f"{path.stem}.{datetime.now().strftime('%H%M%S')}{path.suffix}"
    shutil.move(str(path), str(dest))


def all_sessions(source=None):
    """Yield (source_id, directory, path) for all discovered LLM session logs."""
    for src_id, directory, path, src_name in discover_sessions(mode="quick"):
        if source and src_id != source:
            continue
        yield src_id, directory, path


def session_info(path):
    """Get info about a session file."""
    stat = path.stat()
    lines = 0
    messages = 0
    first_ts = last_ts = session_id = None
    user_preview = ""

    try:
        with open(path) as fh:
            for line in fh:
                lines += 1
                try:
                    d = json.loads(line.strip())
                    ts = d.get("timestamp")
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                    if not session_id:
                        session_id = d.get("sessionId") or d.get("id")
                    msg = d.get("message", d)
                    role = msg.get("role", d.get("type", ""))
                    if role in ("user", "user_message"):
                        messages += 1
                        if not user_preview:
                            content = msg.get("content", "")
                            if isinstance(content, list):
                                texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                                content = " ".join(texts)
                            user_preview = str(content)[:120]
                    elif role in ("assistant",):
                        messages += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return {
        "path": path,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime),
        "lines": lines,
        "messages": messages,
        "session_id": session_id or path.stem,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "preview": user_preview,
    }


def extract_session_summary(path, max_chars=3000):
    """Extract condensed summary for LLM."""
    messages = []
    with open(path) as fh:
        for line in fh:
            try:
                d = json.loads(line.strip())
                msg = d.get("message", d)
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, list):
                    texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    content = " ".join(texts)
                if role == "user" and content:
                    messages.append(f"USER: {content[:200]}")
                elif role == "assistant" and content:
                    messages.append(f"ASSISTANT: {content[:150]}")
            except json.JSONDecodeError:
                continue
    if len(messages) > 10:
        summary = messages[:5] + [f"... ({len(messages)} messages total) ..."] + messages[-3:]
    else:
        summary = messages
    return "\n".join(summary)[:max_chars]


def llm_call(prompt, max_tokens=200):
    """Call Claude via Vertex AI."""
    venv_python = SM_DIR / ".venv" / "bin" / "python3"
    script = f"""
from anthropic import AnthropicVertex
client = AnthropicVertex(project_id='{VERTEX_PROJECT}', region='{VERTEX_REGION}')
resp = client.messages.create(
    model='{VERTEX_MODEL}',
    max_tokens={max_tokens},
    messages=[{{'role':'user','content':'''{prompt.replace(chr(39), chr(39)+chr(34)+chr(39)+chr(34)+chr(39))}'''}}]
)
print(resp.content[0].text)
"""
    result = subprocess.run(
        [str(venv_python), "-c", script],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLM call failed: {result.stderr[:300]}")
    return result.stdout.strip()


# ── Scan & Propose ───────────────────────────────────────────────────────────

def scan_all():
    """Scan all sessions and return categorized findings."""
    sessions = []
    for src, project, path in all_sessions():
        info = session_info(path)
        info["src"] = src
        info["directory"] = project
        sessions.append(info)

    sessions.sort(key=lambda s: s["mtime"], reverse=True)

    # Categorize
    empty = [s for s in sessions if s["lines"] <= 2 or s["messages"] == 0]
    tiny = [s for s in sessions if s not in empty and s["size"] < 2048]
    subagents = [s for s in sessions if s not in empty and s not in tiny
                 and ("subagent" in s["directory"].lower() or s["path"].stem.startswith("agent-"))]
    dupes = find_dupes(sessions)
    normal = [s for s in sessions if s not in empty and s not in tiny
              and s not in subagents and s["session_id"] not in dupes]

    return {
        "all": sessions,
        "empty": empty,
        "tiny": tiny,
        "subagents": subagents,
        "dupes": dupes,
        "normal": normal,
    }


def find_dupes(sessions):
    """Find sessions with identical content."""
    hashes = {}
    for s in sessions:
        try:
            h = hashlib.md5(s["path"].read_bytes()).hexdigest()
            hashes.setdefault(h, []).append(s)
        except Exception:
            pass
    dupe_ids = set()
    for h, group in hashes.items():
        if len(group) > 1:
            for s in group[1:]:
                dupe_ids.add(s["session_id"])
    return dupe_ids


def print_session(s, idx=None):
    prefix = f"  {idx:>3}. " if idx is not None else "  "
    preview = s["preview"][:60] + "..." if s["preview"] else "(empty)"
    print(f"{prefix}[{s['src']}] {s['directory']:<25} {format_size(s['size']):>6}  {s['messages']:>3} msgs  {s['mtime'].strftime('%b %d %H:%M')}")
    if s["preview"]:
        print(f"       {preview}")


# ── Interactive Flow ─────────────────────────────────────────────────────────

def run_interactive():
    """Main interactive flow."""
    print("\n  🔍 Scanning local sessions...\n")
    findings = scan_all()

    total = len(findings["all"])
    total_size = sum(s["size"] for s in findings["all"])
    print(f"  Found {total} sessions ({format_size(total_size)} total)\n")

    # ── Stats ──
    projects = {}
    for s in findings["all"]:
        key = f"[{s['src']}] {s['directory']}"
        projects.setdefault(key, {"count": 0, "size": 0})
        projects[key]["count"] += 1
        projects[key]["size"] += s["size"]

    print(f"  {'Directory':<40} {'#':>4} {'Size':>8}")
    print(f"  {'-'*40} {'-'*4} {'-'*8}")
    for key in sorted(projects, key=lambda k: projects[k]["size"], reverse=True)[:15]:
        p = projects[key]
        print(f"  {key:<40} {p['count']:>4} {format_size(p['size']):>8}")
    if len(projects) > 15:
        print(f"  ... and {len(projects) - 15} more")
    print()

    actions_taken = 0

    # ── Empty sessions ──
    if findings["empty"]:
        print(f"  🗑  {len(findings['empty'])} empty sessions (no messages):\n")
        for i, s in enumerate(findings["empty"], 1):
            print_session(s, i)
        print()
        choice = ask(f"Trash all {len(findings['empty'])} empty sessions?", "yna", "y")
        # y=yes all, n=no, a=ask each
        if choice == "y":
            for s in findings["empty"]:
                trash(s["path"])
                actions_taken += 1
            print(f"  ✅ Trashed {len(findings['empty'])} empty sessions\n")
        elif choice == "a":
            for s in findings["empty"]:
                print_session(s)
                if ask("Trash?", "yn", "y") == "y":
                    trash(s["path"])
                    actions_taken += 1

    # ── Tiny sessions ──
    if findings["tiny"]:
        print(f"  📎 {len(findings['tiny'])} tiny sessions (<2KB):\n")
        for i, s in enumerate(findings["tiny"], 1):
            print_session(s, i)
        print()
        choice = ask(f"Trash all {len(findings['tiny'])} tiny sessions?", "yna", "n")
        if choice == "y":
            for s in findings["tiny"]:
                trash(s["path"])
                actions_taken += 1
            print(f"  ✅ Trashed {len(findings['tiny'])} tiny sessions\n")
        elif choice == "a":
            for s in findings["tiny"]:
                print_session(s)
                if ask("Trash?", "yn", "n") == "y":
                    trash(s["path"])
                    actions_taken += 1

    # ── Subagent sessions ──
    if findings["subagents"]:
        total_sub_size = sum(s["size"] for s in findings["subagents"])
        print(f"  🤖 {len(findings['subagents'])} subagent sessions ({format_size(total_sub_size)}):\n")
        for i, s in enumerate(findings["subagents"][:10], 1):
            print_session(s, i)
        if len(findings["subagents"]) > 10:
            print(f"       ... and {len(findings['subagents']) - 10} more")
        print()
        choice = ask(f"Trash all {len(findings['subagents'])} subagent sessions?", "yna", "n")
        if choice == "y":
            for s in findings["subagents"]:
                trash(s["path"])
                actions_taken += 1
            print(f"  ✅ Trashed {len(findings['subagents'])} subagent sessions\n")
        elif choice == "a":
            for s in findings["subagents"]:
                print_session(s)
                if ask("Trash?", "yn", "n") == "y":
                    trash(s["path"])
                    actions_taken += 1

    # ── Duplicates ──
    if findings["dupes"]:
        print(f"  ♊ {len(findings['dupes'])} duplicate sessions found")
        choice = ask("Trash duplicates (keep first)?", "yn", "y")
        if choice == "y":
            # Re-find to get the actual pairs
            hashes = {}
            for s in findings["all"]:
                try:
                    h = hashlib.md5(s["path"].read_bytes()).hexdigest()
                    hashes.setdefault(h, []).append(s)
                except Exception:
                    pass
            for h, group in hashes.items():
                if len(group) > 1:
                    print(f"    Keeping: [{group[0]['src']}] {group[0]['directory']}")
                    for s in group[1:]:
                        trash(s["path"])
                        actions_taken += 1
            print(f"  ✅ Trashed {len(findings['dupes'])} duplicates\n")

    # ── LLM naming ──
    unnamed = [s for s in findings["normal"] if s["messages"] > 2][:10]
    if unnamed:
        print(f"  🏷  {len(unnamed)} sessions could be named by LLM\n")
        choice = ask("Auto-name sessions with Claude?", "yn", "n")
        if choice == "y":
            run_naming(unnamed)
            actions_taken += len(unnamed)

    # ── LLM correlation ──
    if len(findings["normal"]) >= 3:
        print(f"\n  🔗 {len(findings['normal'])} sessions available for correlation\n")
        choice = ask("Find related sessions with Claude?", "yn", "n")
        if choice == "y":
            run_correlation(findings["normal"][:15])
            actions_taken += 1

    # ── Summary ──
    print(f"\n  Done. {actions_taken} actions taken.\n")


# ── LLM Actions ──────────────────────────────────────────────────────────────

def run_naming(sessions):
    """Name sessions interactively via LLM."""
    print(f"\n  Naming {len(sessions)} sessions via Claude...\n")
    results = []
    for s in sessions:
        summary = extract_session_summary(s["path"])
        if not summary.strip():
            continue

        prompt = f"""Given this LLM conversation transcript, generate:
1. A short descriptive name (5-8 words max)
2. A project category (1-2 words)
3. Up to 3 tags (single words, lowercase)

Reply in exactly this format (no other text):
NAME: <name>
PROJECT: <project>
TAGS: <tag1>, <tag2>, <tag3>

Transcript:
{summary}"""

        try:
            response = llm_call(prompt, max_tokens=100)
            name = proj = ""
            tags = []
            for line in response.strip().split("\n"):
                if line.startswith("NAME:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("PROJECT:"):
                    proj = line.split(":", 1)[1].strip()
                elif line.startswith("TAGS:"):
                    tags = [t.strip() for t in line.split(":", 1)[1].split(",")]

            print(f"  [{s['src']}] {s['directory']}")
            print(f"    → Name: {name}")
            print(f"    → Project: {proj} | Tags: {', '.join(tags)}")

            choice = ask("Apply to Langfuse?", "yns", "y")
            # y=yes, n=no, s=skip rest
            if choice == "s":
                break
            if choice == "y":
                cmd = ["sm", "deposit", str(s["path"])]
                subprocess.run(cmd, capture_output=True)
                # Rename after deposit
                cmd = ["sm", "rename", s["session_id"][:12], name]
                for t in tags:
                    cmd.extend(["--tag", t])
                subprocess.run(cmd, capture_output=True)
                print(f"    ✅ Deposited & named\n")
            else:
                print()

        except Exception as e:
            print(f"  ❌ {e}\n")


def run_correlation(sessions):
    """Find related sessions via LLM."""
    print(f"\n  Analyzing {len(sessions)} sessions for correlation...\n")

    summaries = []
    for s in sessions:
        summary = extract_session_summary(s["path"], max_chars=500)
        if summary.strip():
            summaries.append({
                "id": s["session_id"][:12],
                "src": s["src"],
                "directory": s["directory"],
                "summary": summary[:400],
            })

    if len(summaries) < 2:
        print("  Not enough sessions with content.")
        return

    session_text = ""
    for s in summaries[:20]:
        session_text += f"\n--- Session {s['id']} [{s['src']}] {s['directory']} ---\n{s['summary']}\n"

    prompt = f"""Analyze these {len(summaries)} LLM sessions and identify:
1. Groups of related sessions (same project/topic)
2. Sessions that should be merged (continuation of same work)
3. Suggested project names for ungrouped sessions

Reply in this format:
GROUP: <group_name>
  - <session_id>: <why>

MERGE: <session_id> + <session_id>: <reason>

{session_text}"""

    try:
        response = llm_call(prompt, max_tokens=1000)
        print(response)

        # Parse merge suggestions and offer to execute
        merge_pairs = []
        for line in response.split("\n"):
            if line.startswith("MERGE:"):
                merge_pairs.append(line)

        if merge_pairs:
            print()
            for merge in merge_pairs:
                choice = ask(f"Execute: {merge}?", "yn", "n")
                if choice == "y":
                    # Extract IDs
                    parts = merge.split(":")[1].split("+")
                    ids = [p.strip().split(":")[0].strip() for p in parts]
                    if len(ids) >= 2:
                        merge_sessions(ids)

    except Exception as e:
        print(f"  ❌ {e}")


def merge_sessions(session_ids):
    """Merge sessions by partial ID."""
    paths = []
    for sid in session_ids:
        for src, project, path in all_sessions():
            if path.stem.startswith(sid) or sid in path.stem:
                paths.append(path)
                break

    if len(paths) < 2:
        print("  Could not find all sessions.")
        return

    output = paths[0].parent / f"merged-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"

    all_lines = []
    for p in paths:
        print(f"  ← {p.name} ({format_size(p.stat().st_size)})")
        with open(p) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        d = json.loads(line)
                        if d.get("type") == "session" and all_lines:
                            continue
                        all_lines.append((d.get("timestamp", ""), line))
                    except json.JSONDecodeError:
                        all_lines.append(("", line))

    all_lines.sort(key=lambda x: x[0])

    with open(output, "w") as fh:
        for _, line in all_lines:
            fh.write(line + "\n")

    print(f"  → {output.name} ({format_size(output.stat().st_size)})")

    choice = ask("Trash originals?", "yn", "y")
    if choice == "y":
        for p in paths:
            trash(p)
        print("  ✅ Originals trashed")


# ── Stats (standalone) ───────────────────────────────────────────────────────

def run_stats():
    """Show storage stats."""
    by_source = {}
    by_dir = {}
    total_size = 0
    total_count = 0
    for src, directory, path in all_sessions():
        stat = path.stat()
        total_size += stat.st_size
        total_count += 1

        # Per source
        src_name = {v[0]: v[1] for v in SOURCE_IDS.values()}.get(src, src)
        by_source.setdefault(src, {"name": src_name, "count": 0, "size": 0})
        by_source[src]["count"] += 1
        by_source[src]["size"] += stat.st_size

        # Per directory
        key = f"[{src}] {directory}"
        by_dir.setdefault(key, {"count": 0, "size": 0})
        by_dir[key]["count"] += 1
        by_dir[key]["size"] += stat.st_size

    print(f"\n  📊 {total_count} sessions, {format_size(total_size)} total\n")

    # Source breakdown
    print(f"  {'Source':<25} {'#':>6} {'Size':>8}")
    print(f"  {'-'*25} {'-'*6} {'-'*8}")
    for src_id, s in sorted(by_source.items(), key=lambda x: x[1]["size"], reverse=True):
        print(f"  {s['name']:<25} {s['count']:>6} {format_size(s['size']):>8}")
    print()

    # Directory breakdown
    print(f"  {'Directory':<40} {'#':>4} {'Size':>8}")
    print(f"  {'-'*40} {'-'*4} {'-'*8}")
    for key in sorted(by_dir, key=lambda k: by_dir[k]["size"], reverse=True):
        p = by_dir[key]
        print(f"  {key:<40} {p['count']:>4} {format_size(p['size']):>8}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd == "stats":
        run_stats()
    elif cmd == "name":
        sessions = []
        for src, project, path in all_sessions():
            info = session_info(path)
            info["src"] = src
            info["directory"] = project
            if info["messages"] > 2:
                sessions.append(info)
        sessions.sort(key=lambda s: s["mtime"], reverse=True)
        run_naming(sessions[:10])
    elif cmd == "correlate":
        sessions = []
        for src, project, path in all_sessions():
            info = session_info(path)
            info["src"] = src
            info["directory"] = project
            if info["messages"] > 2:
                sessions.append(info)
        sessions.sort(key=lambda s: s["mtime"], reverse=True)
        run_correlation(sessions[:15])
    elif cmd == "--help" or cmd == "-h":
        print(__doc__)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
