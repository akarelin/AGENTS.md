#!/usr/bin/env python3
"""
sm-map — Session map navigator.

Uses user-provided sm-map.yaml to discover, navigate, transform, and sync sessions.

Usage:
    sm-map                        # Interactive: scan all sources, show everything
    sm-map scan                   # Scan all sources and show summary
    sm-map sync                   # Sync all sessions to configured targets
    sm-map project <slug>         # Show sessions for a project
    sm-map associate              # Auto-associate sessions to projects by cwd
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

SM_DIR = Path(__file__).resolve().parent.parent

MAP_SEARCH_PATHS = [
    Path.home() / ".config" / "sm" / "map.yaml",
    Path.home() / "sm-map.yaml",
    Path.cwd() / "sm-map.yaml",
    SM_DIR / "sm-map.yaml",
]


def load_map() -> dict:
    """Load user's session map."""
    for p in MAP_SEARCH_PATHS:
        if p.exists():
            return yaml.safe_load(p.read_text()) or {}
    print("  No sm-map.yaml found. Create one from sm-map.yaml.example")
    print(f"  Copy to: {MAP_SEARCH_PATHS[0]}")
    sys.exit(1)


def format_size(size):
    if size < 1024: return f"{size}B"
    elif size < 1048576: return f"{size // 1024}K"
    else: return f"{size / 1048576:.1f}M"


# ── Source scanning ──────────────────────────────────────────────────────────

def scan_source(source: dict) -> list[dict]:
    """Scan a single source for session files."""
    src_type = source.get("type", "")
    src_path = Path(os.path.expanduser(source.get("path", "")))
    host = source.get("host", "local")
    name = source.get("name", src_type)

    sessions = []

    if host != "local":
        # Remote source via SSH
        sessions = _scan_remote(host, str(src_path), src_type, name)
    elif src_type in ("chatgpt-export", "claude-export"):
        # Export archive — needs import first
        if src_path.exists():
            sessions.append({
                "source": name,
                "type": src_type,
                "path": str(src_path),
                "size": src_path.stat().st_size,
                "is_archive": True,
                "imported": False,
            })
    elif src_path.exists():
        # Local source
        sessions = _scan_local(src_path, src_type, name)

    return sessions


def _scan_local(base: Path, src_type: str, name: str) -> list[dict]:
    """Scan local directory for JSONL sessions."""
    sessions = []
    exclude = {".reset.", "audit.jsonl"}

    for f in base.rglob("*.jsonl"):
        if any(exc in f.name for exc in exclude):
            continue
        if not f.is_file():
            continue

        stat = f.stat()
        # Derive directory label
        try:
            rel = f.relative_to(base)
            if src_type == "claude-code":
                directory = f.parent.name.replace("-Users-alex-", "").replace("-home-alex-", "").replace("-", "/")
            elif src_type == "openclaw":
                directory = rel.parts[0] if len(rel.parts) > 2 else f.parent.name
            else:
                directory = str(rel.parent) if len(rel.parts) > 1 else ""
        except ValueError:
            directory = f.parent.name

        sessions.append({
            "source": name,
            "type": src_type,
            "directory": directory,
            "session_id": f.stem,
            "path": str(f),
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return sessions


def _scan_remote(host: str, path: str, src_type: str, name: str) -> list[dict]:
    """Scan remote host via SSH for JSONL sessions."""
    try:
        result = subprocess.run(
            ["ssh", host, f"find {path} -name '*.jsonl' -not -name '*.reset.*' -exec stat --format='%n|%s|%Y' {{}} \\; 2>/dev/null || "
             f"find {path} -name '*.jsonl' -not -name '*.reset.*' -exec stat -f '%N|%z|%m' {{}} \\; 2>/dev/null"],
            capture_output=True, text=True, timeout=15,
        )
        sessions = []
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            fpath, size, mtime = parts[0], int(parts[1]), int(parts[2])
            fname = Path(fpath).stem
            directory = Path(fpath).parent.name

            sessions.append({
                "source": name,
                "type": src_type,
                "directory": directory,
                "session_id": fname,
                "path": fpath,
                "size": size,
                "mtime": datetime.fromtimestamp(mtime).isoformat(),
                "host": host,
            })
        return sessions
    except Exception as e:
        print(f"  ⚠️  Failed to scan {host}: {e}")
        return []


# ── Project association ──────────────────────────────────────────────────────

def auto_associate(sessions: list[dict], projects: list[dict]) -> list[dict]:
    """Auto-associate sessions to projects by matching cwd/path to project paths."""
    # Build lookup: expanded path → project slug
    path_to_project = {}
    for proj in projects:
        for p in proj.get("paths", []):
            expanded = os.path.expanduser(p)
            path_to_project[expanded] = proj["slug"]

    for session in sessions:
        if session.get("project"):
            continue
        spath = session.get("path", "")
        # Check if session path is under any project path
        for proj_path, slug in path_to_project.items():
            if proj_path in spath:
                session["project"] = slug
                break

    return sessions


# ── Sync ─────────────────────────────────────────────────────────────────────

def sync_to_langfuse(sessions: list[dict], config: dict):
    """Sync sessions to Langfuse."""
    venv_python = SM_DIR / ".venv" / "bin" / "python3"
    depositor = SM_DIR / "scripts" / "session-to-langfuse.py"

    total = len(sessions)
    ok = 0
    for i, s in enumerate(sessions, 1):
        if s.get("is_archive"):
            continue
        path = s.get("path", "")
        if not path or not Path(path).exists():
            continue
        print(f"  [{i}/{total}] {s.get('source', '?')}: {s.get('directory', '')}/{s.get('session_id', '')[:12]}...")
        result = subprocess.run(
            [str(venv_python), str(depositor)],
            input=json.dumps({"session_file": path}),
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            ok += 1
    print(f"\n  ✅ Synced {ok}/{total} sessions to Langfuse")


def sync_to_folder(sessions: list[dict], config: dict):
    """Sync sessions to folder store."""
    from store import FolderStore
    store_path = os.path.expanduser(config.get("path", ""))
    if not store_path:
        print("  No folder store path configured")
        return
    store = FolderStore(store_path)
    total = len(sessions)
    ok = 0
    for i, s in enumerate(sessions, 1):
        if s.get("is_archive"):
            continue
        path = s.get("path", "")
        if not path or not Path(path).exists():
            continue
        try:
            meta = {"project": s.get("project")} if s.get("project") else {}
            store.deposit(path, meta=meta)
            ok += 1
        except Exception as e:
            print(f"  ⚠️  {s.get('session_id', '?')[:12]}: {e}")
    print(f"\n  ✅ Synced {ok}/{total} sessions to folder store")


# ── Interactive UI ───────────────────────────────────────────────────────────

def run_interactive(user_map: dict):
    """Main interactive flow."""
    user = user_map.get("user", {})
    sources = user_map.get("sources", [])
    projects = user_map.get("projects", [])
    sync_config = user_map.get("sync", {})
    options = user_map.get("options", {})

    print(f"\n  📋 Session Map — {user.get('name', 'unknown')}\n")

    # Scan all sources
    all_sessions = []
    print(f"  Scanning {len(sources)} sources...\n")
    for src in sources:
        host = src.get("host", "local")
        host_tag = f" ({host})" if host != "local" else ""
        sessions = scan_source(src)

        if sessions:
            total_size = sum(s.get("size", 0) for s in sessions)
            archives = [s for s in sessions if s.get("is_archive")]
            if archives:
                print(f"  📦 {src['name']}{host_tag}: archive ({format_size(total_size)})")
            else:
                print(f"  ✅ {src['name']}{host_tag}: {len(sessions)} sessions ({format_size(total_size)})")
        else:
            print(f"  ⏭  {src['name']}{host_tag}: no sessions found")
        all_sessions.extend(sessions)

    print(f"\n  Total: {len(all_sessions)} sessions\n")

    # Auto-associate
    if options.get("auto_associate", True) and projects:
        all_sessions = auto_associate(all_sessions, projects)
        associated = sum(1 for s in all_sessions if s.get("project"))
        if associated:
            print(f"  🔗 Auto-associated {associated} sessions to projects\n")

    # Project summary
    if projects:
        print(f"  📁 Projects:\n")
        for proj in projects:
            slug = proj["slug"]
            proj_sessions = [s for s in all_sessions if s.get("project") == slug]
            count = len(proj_sessions)
            size = sum(s.get("size", 0) for s in proj_sessions)
            tags = ", ".join(proj.get("tags", [])[:3])
            status = f"{count} sessions ({format_size(size)})" if count else "no sessions"
            print(f"  📂 {proj.get('name', slug):<30} {status:<25} {tags}")
        print()

    # Unassociated sessions
    unassociated = [s for s in all_sessions if not s.get("project") and not s.get("is_archive")]
    if unassociated:
        print(f"  ❓ {len(unassociated)} sessions not associated with any project\n")

    # Archives to import
    archives = [s for s in all_sessions if s.get("is_archive")]
    if archives:
        print(f"  📦 {len(archives)} export archive(s) to import:\n")
        for a in archives:
            print(f"    {a['source']}: {a['path']} ({format_size(a['size'])})")
        print()
        choice = input("  Import archives? [y/N] ").strip().lower()
        if choice == "y":
            for a in archives:
                src_type = a["type"]
                cmd = ["sm-import"]
                if src_type == "chatgpt-export":
                    cmd += ["chatgpt", a["path"]]
                elif src_type == "claude-export":
                    cmd += ["claude", a["path"]]
                subprocess.run(cmd)

    # Sync options
    print("  Actions:")
    print("  [1] Sync all to Langfuse")
    print("  [2] Sync all to folder store")
    print("  [3] Show unassociated sessions")
    print("  [4] Show project detail")
    print("  [q] Quit")
    print()

    while True:
        choice = input("  > ").strip().lower()
        if choice == "q" or not choice:
            break
        elif choice == "1":
            lf = sync_config.get("langfuse", {})
            if lf:
                non_archives = [s for s in all_sessions if not s.get("is_archive")]
                sync_to_langfuse(non_archives, lf)
            else:
                print("  No Langfuse config in sm-map.yaml")
        elif choice == "2":
            fs = sync_config.get("folder_store", {})
            if fs:
                non_archives = [s for s in all_sessions if not s.get("is_archive")]
                sync_to_folder(non_archives, fs)
            else:
                print("  No folder store config in sm-map.yaml")
        elif choice == "3":
            for s in unassociated[:20]:
                print(f"    [{s.get('type','')}] {s.get('directory','')}/{s.get('session_id','')[:12]}...")
            if len(unassociated) > 20:
                print(f"    ... and {len(unassociated) - 20} more")
        elif choice == "4":
            slug = input("  Project slug: ").strip()
            proj_sessions = [s for s in all_sessions if s.get("project") == slug]
            if proj_sessions:
                for s in proj_sessions:
                    print(f"    [{s.get('source','')}] {s.get('session_id','')[:16]}... {format_size(s.get('size',0))}")
            else:
                print(f"  No sessions for '{slug}'")
        print()


def run_scan(user_map: dict):
    """Just scan and print summary."""
    sources = user_map.get("sources", [])
    total = 0
    total_size = 0
    for src in sources:
        sessions = scan_source(src)
        size = sum(s.get("size", 0) for s in sessions)
        host = src.get("host", "local")
        host_tag = f" ({host})" if host != "local" else ""
        print(f"  {src['name']:<30}{host_tag:<25} {len(sessions):>4} sessions  {format_size(size):>8}")
        total += len(sessions)
        total_size += size
    print(f"\n  Total: {total} sessions, {format_size(total_size)}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    user_map = load_map()

    if cmd == "scan":
        run_scan(user_map)
    elif cmd == "sync":
        all_sessions = []
        for src in user_map.get("sources", []):
            all_sessions.extend(scan_source(src))
        non_archives = [s for s in all_sessions if not s.get("is_archive")]
        lf = user_map.get("sync", {}).get("langfuse", {})
        if lf:
            sync_to_langfuse(non_archives, lf)
    elif cmd == "associate":
        all_sessions = []
        for src in user_map.get("sources", []):
            all_sessions.extend(scan_source(src))
        all_sessions = auto_associate(all_sessions, user_map.get("projects", []))
        associated = [s for s in all_sessions if s.get("project")]
        for s in associated:
            print(f"  {s.get('session_id','')[:12]}... → {s['project']}")
        print(f"\n  {len(associated)} sessions associated")
    elif cmd == "project" and len(sys.argv) > 2:
        slug = sys.argv[2]
        all_sessions = []
        for src in user_map.get("sources", []):
            all_sessions.extend(scan_source(src))
        all_sessions = auto_associate(all_sessions, user_map.get("projects", []))
        proj_sessions = [s for s in all_sessions if s.get("project") == slug]
        print(f"\n  Project '{slug}': {len(proj_sessions)} sessions\n")
        for s in proj_sessions:
            print(f"  [{s.get('source','')}] {s.get('session_id','')[:16]}... {format_size(s.get('size',0)):>6}  {s.get('directory','')}")
    elif cmd in ("--help", "-h"):
        print(__doc__)
    else:
        run_interactive(user_map)


if __name__ == "__main__":
    main()
