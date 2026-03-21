"""Claude Session Manager — UI-independent session operations.

Handles: listing, caching, deleting, moving, copying Claude Code sessions.
Used by TUI, CLI, session_manager, and agent tools.
"""

import json
import shutil
from pathlib import Path
from typing import Any


# --- Path decoding ---

_WIN_MACHINES = {"ALEX-LAPTOP", "Alex-PC"}


def decode_project_dir(dirname: str) -> str:
    """Convert encoded project dir back to path. '-home-alex-CRAP' -> '/home/alex/CRAP'"""
    if dirname.startswith("D--"):
        rest = dirname[3:]
        parts = rest.split("-") if rest else []
        return "D:\\" + "\\".join(parts) if parts else "D:\\"
    return dirname.replace("-", "/")


def machine_icon(name: str) -> str:
    """Return icon for machine type."""
    if name.endswith(".WSL"):
        return "\U0001f427"  # 🐧 WSL
    if name in _WIN_MACHINES:
        return "\u229e"      # ⊞ Windows
    return "\U0001f5a5"      # 🖥 Linux


def machine_label(name: str) -> str:
    """Pretty machine name with icon."""
    return f"{machine_icon(name)} {name.replace('.WSL', '')}"


# --- Session parsing ---

def first_user_message(path: Path) -> str:
    """Extract first non-meta user message from a session JSONL."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "user" and not d.get("isMeta"):
                    c = d.get("message", {}).get("content", "")
                    if isinstance(c, str) and len(c) > 3 and not c.startswith("<"):
                        return c[:60]
    except Exception:
        pass
    return path.stem[:12]


def session_timestamp(path: Path) -> str:
    """Get date from first entry."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    ts = d.get("timestamp", "")
                    if isinstance(ts, str) and "T" in ts:
                        return ts[:10]
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def fast_msg_count(filepath: str) -> int:
    """Fast message count — string scan, no JSON parse."""
    try:
        count = 0
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"type":"user"' in line or '"type": "user"' in line:
                    count += 1
                elif '"type":"assistant"' in line or '"type": "assistant"' in line:
                    count += 1
        return count
    except Exception:
        return 0


def load_session_messages(session_file: str) -> list[dict]:
    """Parse a Claude Code JSONL into [{role, content}]."""
    messages = []
    try:
        with open(session_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                mtype = d.get("type")
                msg = d.get("message", {})
                if mtype == "user" and not d.get("isMeta"):
                    c = msg.get("content", "")
                    if isinstance(c, str) and len(c) > 1 and not c.startswith("<"):
                        messages.append({"role": "user", "content": c[:500]})
                elif mtype == "assistant":
                    c = msg.get("content", "")
                    if isinstance(c, list):
                        parts = []
                        for b in c:
                            if isinstance(b, dict):
                                if b.get("type") == "text":
                                    parts.append(b.get("text", ""))
                                elif b.get("type") == "tool_use":
                                    messages.append({"role": "tool", "content": b.get("name", "")})
                        if parts:
                            messages.append({"role": "assistant", "content": "\n".join(parts)[:2000]})
                    elif isinstance(c, str) and c:
                        messages.append({"role": "assistant", "content": c[:2000]})
    except Exception:
        pass
    return messages


# --- Session Manager ---

class ClaudeSessionManager:
    """UI-independent Claude session operations."""

    def __init__(self, claude_dir: str = "/mnt/d/SD/.claude", store=None):
        self.claude_dir = claude_dir
        self.store = store  # SessionStore for cache access

    def scan_all(self) -> dict[str, dict[str, list[dict]]]:
        """Scan .claude directory. Returns machine -> project -> [session_info]."""
        cpath = Path(self.claude_dir)
        if not cpath.exists():
            return {}

        result: dict[str, dict[str, list[dict]]] = {}
        for mdir in sorted(cpath.iterdir()):
            if not mdir.is_dir():
                continue
            pdir = mdir / "projects"
            if not pdir.is_dir():
                continue

            msessions: dict[str, list[dict]] = {}
            for projd in sorted(pdir.iterdir()):
                if not projd.is_dir():
                    continue
                proj_path = decode_project_dir(projd.name)
                sessions = []
                for sf in sorted(projd.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                    if sf.name.startswith("."):
                        continue
                    sessions.append({
                        "id": sf.stem,
                        "name": first_user_message(sf),
                        "date": session_timestamp(sf),
                        "file": str(sf),
                        "project_dir": projd.name,
                        "project_path": proj_path,
                        "machine_dir": mdir.name,
                    })
                    if len(sessions) >= 15:
                        break
                if sessions:
                    msessions[proj_path] = sessions
            if msessions:
                result[mdir.name] = msessions
        return result

    def scan_flat(self, with_stats: bool = False) -> list[dict]:
        """Scan and return flat list of all sessions with optional stats."""
        data = self.scan_all()
        all_sessions = []
        for machine, projects in data.items():
            for proj, sessions in projects.items():
                for s in sessions:
                    if with_stats:
                        s["msg_count"] = fast_msg_count(s.get("file", ""))
                        fpath = Path(s["file"])
                        s["file_size"] = fpath.stat().st_size if fpath.exists() else 0
                        subdir = fpath.parent / fpath.stem / "subagents"
                        s["subagent_count"] = len(list(subdir.glob("*.jsonl"))) if subdir.is_dir() else 0
                    all_sessions.append(s)
        return all_sessions

    def get_cached(self) -> list[dict]:
        """Get sessions from cache. Returns [] if no cache or expired."""
        if self.store:
            return self.store.get_cached_claude_sessions()
        return []

    def refresh_cache(self) -> list[dict]:
        """Scan disk, update cache, return sessions."""
        sessions = self.scan_flat(with_stats=True)
        if self.store:
            self.store.clear_claude_cache()
            self.store.cache_claude_sessions_bulk(sessions)
        return sessions

    def find_session(self, session_id: str) -> Path | None:
        """Find session JSONL by ID."""
        cpath = Path(self.claude_dir)
        for f in cpath.glob(f"*/projects/*/{session_id}.jsonl"):
            return f
        return None

    def delete_session(self, session_id: str) -> str:
        """Delete session files. Returns status message."""
        fpath = self.find_session(session_id)
        if not fpath:
            return f"Session not found: {session_id}"
        session_dir = fpath.parent / fpath.stem
        name = first_user_message(fpath)
        fpath.unlink(missing_ok=True)
        if session_dir.is_dir():
            shutil.rmtree(session_dir)
        if self.store:
            self.store.delete_cached_claude_session(session_id)
        return f"Deleted: {name}"

    def copy_session(self, session_id: str, dest: str) -> str:
        """Copy session to destination directory."""
        fpath = self.find_session(session_id)
        if not fpath:
            return f"Session not found: {session_id}"
        dest_path = Path(dest).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fpath, dest_path / fpath.name)
        session_dir = fpath.parent / fpath.stem
        if session_dir.is_dir():
            dest_session = dest_path / fpath.stem
            if not dest_session.exists():
                shutil.copytree(session_dir, dest_session)
        return f"Copied to {dest_path}"

    def move_session(self, session_id: str, dest: str) -> str:
        """Move session to destination directory."""
        fpath = self.find_session(session_id)
        if not fpath:
            return f"Session not found: {session_id}"
        dest_path = Path(dest).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)
        shutil.move(str(fpath), str(dest_path / fpath.name))
        session_dir = fpath.parent / fpath.stem
        if session_dir.is_dir():
            shutil.move(str(session_dir), str(dest_path / fpath.stem))
        if self.store:
            self.store.delete_cached_claude_session(session_id)
        return f"Moved to {dest_path}"

    def copy_to_local(self, session_info: dict) -> str:
        """Copy session to local .claude for 'claude --resume'."""
        src = Path(session_info["file"])
        local_proj = Path.home() / ".claude" / "projects" / session_info.get("project_dir", "")
        local_proj.mkdir(parents=True, exist_ok=True)
        dest = local_proj / src.name
        if not dest.exists():
            shutil.copy2(src, dest)
        subagents_src = src.parent / src.stem / "subagents"
        if subagents_src.is_dir():
            subagents_dest = local_proj / src.stem / "subagents"
            if not subagents_dest.exists():
                shutil.copytree(subagents_src, subagents_dest)
        return f"Copied to {local_proj}"

    def get_session_detail(self, session_info: dict) -> dict:
        """Get detailed stats for a session."""
        fpath = Path(session_info["file"])
        fsize = fpath.stat().st_size if fpath.exists() else 0
        subagent_dir = fpath.parent / fpath.stem / "subagents"
        subagent_count = len(list(subagent_dir.glob("*.jsonl"))) if subagent_dir.is_dir() else 0
        tool_results_dir = fpath.parent / fpath.stem / "tool-results"
        tool_result_count = len(list(tool_results_dir.iterdir())) if tool_results_dir.is_dir() else 0
        local_path = Path.home() / ".claude" / "projects" / session_info.get("project_dir", "") / fpath.name
        return {
            **session_info,
            "file_size": fsize,
            "subagent_count": subagent_count,
            "tool_result_count": tool_result_count,
            "has_local_copy": local_path.exists(),
            "local_path": str(local_path),
            "msg_count": session_info.get("msg_count") or fast_msg_count(session_info.get("file", "")),
        }

    def rename_session(self, session_id: str, new_name: str) -> str:
        """Rename a Claude session. TODO: implement."""
        # Possible approach: update the first user message or add metadata file
        raise NotImplementedError("Claude session rename not yet implemented")

    def merge_sessions(self, session_ids: list[str]) -> str:
        """Merge multiple sessions into one. TODO: implement."""
        # Possible approach: concatenate JSONLs, deduplicate, fix parent UUIDs
        raise NotImplementedError("Session merge not yet implemented")

    def list_hosts(self) -> list[dict]:
        """List all hosts with session counts."""
        cpath = Path(self.claude_dir)
        if not cpath.exists():
            return []
        hosts = []
        for d in sorted(cpath.iterdir()):
            if d.is_dir() and (d / "projects").is_dir():
                projects = [p for p in (d / "projects").iterdir() if p.is_dir()]
                sessions = sum(1 for p in projects for _ in p.glob("*.jsonl"))
                hosts.append({
                    "name": d.name,
                    "label": machine_label(d.name),
                    "projects": len(projects),
                    "sessions": sessions,
                })
        return hosts
