"""
Folder-based session store.

Organizes session data in a shared folder structure that mirrors the DB schema.
No server required — works with any shared filesystem (NAS, Dropbox, Syncthing).

Usage:
    from store import FolderStore
    store = FolderStore("/mnt/nas/sessions", user="alex")
    store.deposit(session_jsonl_path)
    store.rename("5ccbb62b", "My Session Name")
    sessions = store.list()
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import yaml


class FolderStore:
    """File-based session store. A shared folder is the database."""

    def __init__(self, root: str | Path, user: str = "alex"):
        self.root = Path(root)
        self.user = user
        self._ensure_structure()

    def _ensure_structure(self):
        """Create base directory structure."""
        (self.root / ".sm").mkdir(parents=True, exist_ok=True)
        (self.root / "projects").mkdir(exist_ok=True)
        (self.root / "users" / self.user / "sessions").mkdir(parents=True, exist_ok=True)
        (self.root / "archive" / self.user).mkdir(parents=True, exist_ok=True)

    # ── Paths ────────────────────────────────────────────────────────────

    def _session_dir(self, session_id: str) -> Path:
        return self.root / "users" / self.user / "sessions" / session_id[:8]

    def _meta_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "meta.yaml"

    def _jsonl_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.jsonl"

    def _project_dir(self, slug: str) -> Path:
        return self.root / "projects" / slug

    # ── Deposit ──────────────────────────────────────────────────────────

    def deposit(self, jsonl_path: str | Path, meta: dict | None = None) -> str:
        """Import a session JSONL into the store."""
        jsonl_path = Path(jsonl_path)
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

        # Parse session info from JSONL
        info = self._parse_jsonl(jsonl_path)
        session_id = info.get("session_id", jsonl_path.stem)

        # Create session directory
        sess_dir = self._session_dir(session_id)
        sess_dir.mkdir(parents=True, exist_ok=True)

        # Copy JSONL
        dest = sess_dir / "session.jsonl"
        shutil.copy2(str(jsonl_path), str(dest))

        # Write meta
        meta_data = {
            "id": session_id,
            "name": None,
            "name_source": None,
            "source": info.get("source", "unknown"),
            "source_host": os.uname().nodename,
            "source_file": str(jsonl_path),
            "model": info.get("model"),
            "provider": info.get("provider"),
            "project": None,
            "cwd": info.get("cwd"),
            "git_branch": info.get("git_branch"),
            "started": info.get("first_ts"),
            "ended": info.get("last_ts"),
            "messages": info.get("messages", 0),
            "generations": info.get("generations", 0),
            "input_tokens": info.get("input_tokens", 0),
            "output_tokens": info.get("output_tokens", 0),
            "tags": [],
            "status": "completed",
            "merged_into": None,
            "langfuse_trace_id": None,
            "deposited": datetime.now().isoformat(),
        }
        if meta:
            meta_data.update(meta)

        self._write_meta(session_id, meta_data)
        self._update_index()
        return session_id

    def _parse_jsonl(self, path: Path) -> dict:
        """Extract metadata from a JSONL session file."""
        info = {
            "session_id": path.stem,
            "messages": 0,
            "generations": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # Session ID
                if not info.get("session_id_found"):
                    sid = d.get("sessionId") or d.get("id")
                    if sid and len(sid) > 8:
                        info["session_id"] = sid
                        info["session_id_found"] = True

                # Timestamps
                ts = d.get("timestamp")
                if ts:
                    if "first_ts" not in info:
                        info["first_ts"] = ts
                    info["last_ts"] = ts

                # Source detection
                if d.get("type") == "session" and d.get("version"):
                    info["source"] = "openclaw"
                elif d.get("entrypoint") == "sdk-cli" or d.get("type") == "queue-operation":
                    info["source"] = "claude-code"

                # Model
                msg = d.get("message", {})
                if isinstance(msg, dict) and msg.get("model") and not info.get("model"):
                    info["model"] = msg["model"]

                # CWD / git
                if d.get("cwd") and not info.get("cwd"):
                    info["cwd"] = d["cwd"]
                if d.get("gitBranch") and not info.get("git_branch"):
                    info["git_branch"] = d["gitBranch"]

                # Message counting
                role = msg.get("role", d.get("type", ""))
                if role in ("user", "user_message"):
                    info["messages"] += 1
                elif role == "assistant":
                    info["messages"] += 1
                    info["generations"] += 1
                    usage = msg.get("usage", {})
                    info["input_tokens"] += usage.get("input_tokens", 0)
                    info["output_tokens"] += usage.get("output_tokens", 0)

        info.pop("session_id_found", None)
        return info

    # ── Read / List ──────────────────────────────────────────────────────

    def list(self, user: str | None = None, project: str | None = None,
             status: str | None = None) -> list[dict]:
        """List sessions, optionally filtered."""
        # Try index first
        index = self._read_index()
        if index:
            sessions = index.get("sessions", [])
        else:
            sessions = self._scan_all_meta()

        if user:
            sessions = [s for s in sessions if s.get("user") == user]
        if project:
            sessions = [s for s in sessions if s.get("project") == project]
        if status:
            sessions = [s for s in sessions if s.get("status") == status]

        return sessions

    def get(self, session_id: str) -> dict | None:
        """Get session metadata by ID (partial match)."""
        for s in self.list():
            if s["id"].startswith(session_id):
                return s
        return None

    def get_jsonl(self, session_id: str) -> str | None:
        """Get raw JSONL content."""
        path = self._jsonl_path(session_id)
        if path.exists():
            return path.read_text()
        # Try partial match
        for s in self.list():
            if s["id"].startswith(session_id):
                p = self._jsonl_path(s["id"])
                return p.read_text() if p.exists() else None
        return None

    # ── Modify ───────────────────────────────────────────────────────────

    def rename(self, session_id: str, name: str, name_source: str = "manual"):
        """Rename a session."""
        meta = self._read_meta(session_id)
        if not meta:
            raise ValueError(f"Session not found: {session_id}")
        meta["name"] = name
        meta["name_source"] = name_source
        self._write_meta(session_id, meta)
        self._update_index()

    def tag(self, session_id: str, tags: list[str]):
        """Add tags to a session."""
        meta = self._read_meta(session_id)
        if not meta:
            raise ValueError(f"Session not found: {session_id}")
        existing = set(meta.get("tags", []))
        existing.update(tags)
        meta["tags"] = sorted(existing)
        self._write_meta(session_id, meta)
        self._update_index()

    def archive(self, session_id: str):
        """Move session to archive."""
        sess_dir = self._session_dir(session_id)
        if not sess_dir.exists():
            raise ValueError(f"Session not found: {session_id}")
        archive_dir = self.root / "archive" / self.user / session_id[:8]
        shutil.move(str(sess_dir), str(archive_dir))

        # Update meta
        meta_path = archive_dir / "meta.yaml"
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text()) or {}
            meta["status"] = "archived"
            meta["archived_at"] = datetime.now().isoformat()
            meta_path.write_text(yaml.dump(meta, default_flow_style=False))

        self._update_index()

    def merge(self, session_ids: list[str], name: str | None = None) -> str:
        """Merge multiple sessions into one."""
        metas = []
        jsonl_paths = []
        for sid in session_ids:
            meta = self._read_meta(sid)
            if meta:
                metas.append(meta)
                jp = self._jsonl_path(meta["id"])
                if jp.exists():
                    jsonl_paths.append(jp)

        if len(jsonl_paths) < 2:
            raise ValueError("Need at least 2 sessions to merge")

        # Create merged session
        merged_id = f"merged-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        merged_dir = self._session_dir(merged_id)
        merged_dir.mkdir(parents=True, exist_ok=True)

        # Merge JSONLs (sorted by timestamp)
        all_lines = []
        for jp in jsonl_paths:
            with open(jp) as f:
                for line in f:
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

        merged_jsonl = merged_dir / "session.jsonl"
        with open(merged_jsonl, "w") as f:
            for _, line in all_lines:
                f.write(line + "\n")

        # Write merged meta
        merged_meta = {
            "id": merged_id,
            "name": name or f"Merged: {', '.join(m.get('name') or m['id'][:8] for m in metas[:3])}",
            "name_source": "merge",
            "source": metas[0].get("source", "unknown"),
            "source_host": os.uname().nodename,
            "messages": sum(m.get("messages", 0) for m in metas),
            "generations": sum(m.get("generations", 0) for m in metas),
            "input_tokens": sum(m.get("input_tokens", 0) for m in metas),
            "output_tokens": sum(m.get("output_tokens", 0) for m in metas),
            "tags": sorted(set(t for m in metas for t in m.get("tags", []))),
            "status": "completed",
            "merged_from": [m["id"] for m in metas],
            "deposited": datetime.now().isoformat(),
        }
        self._write_meta(merged_id, merged_meta)

        # Archive originals
        for meta in metas:
            try:
                self.archive(meta["id"])
            except Exception:
                pass

        self._update_index()
        return merged_id

    def associate_project(self, session_id: str, project_slug: str):
        """Associate a session with a project."""
        # Ensure project exists
        proj_dir = self._project_dir(project_slug)
        proj_dir.mkdir(parents=True, exist_ok=True)
        proj_yaml = proj_dir / "project.yaml"
        if not proj_yaml.exists():
            proj_yaml.write_text(yaml.dump({
                "name": project_slug,
                "slug": project_slug,
                "created": datetime.now().isoformat(),
            }, default_flow_style=False))

        # Create session reference
        sess_ref = proj_dir / "sessions"
        sess_ref.mkdir(exist_ok=True)
        meta = self._read_meta(session_id)
        if meta:
            ref_file = sess_ref / f"{session_id[:8]}.yaml"
            ref_file.write_text(yaml.dump({
                "session_id": meta["id"],
                "user": self.user,
                "associated": datetime.now().isoformat(),
            }, default_flow_style=False))

            # Update session meta
            meta["project"] = project_slug
            self._write_meta(session_id, meta)
            self._update_index()

    # ── Projects ─────────────────────────────────────────────────────────

    def list_projects(self) -> list[dict]:
        """List all projects."""
        projects = []
        proj_root = self.root / "projects"
        if not proj_root.exists():
            return projects
        for d in sorted(proj_root.iterdir()):
            if not d.is_dir():
                continue
            proj_yaml = d / "project.yaml"
            if proj_yaml.exists():
                proj = yaml.safe_load(proj_yaml.read_text()) or {}
                # Count sessions
                sess_dir = d / "sessions"
                count = len(list(sess_dir.glob("*.yaml"))) if sess_dir.exists() else 0
                proj["session_count"] = count
                projects.append(proj)
        return projects

    # ── Internal ─────────────────────────────────────────────────────────

    def _read_meta(self, session_id: str) -> dict | None:
        path = self._meta_path(session_id)
        if path.exists():
            return yaml.safe_load(path.read_text()) or {}
        # Partial match
        sessions_dir = self.root / "users" / self.user / "sessions"
        for d in sessions_dir.iterdir():
            if d.is_dir() and session_id.startswith(d.name):
                mp = d / "meta.yaml"
                if mp.exists():
                    return yaml.safe_load(mp.read_text()) or {}
        return None

    def _write_meta(self, session_id: str, meta: dict):
        path = self._meta_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))

    def _scan_all_meta(self) -> list[dict]:
        """Scan all meta.yaml files across all users."""
        sessions = []
        users_dir = self.root / "users"
        if not users_dir.exists():
            return sessions
        for user_dir in users_dir.iterdir():
            if not user_dir.is_dir():
                continue
            sessions_dir = user_dir / "sessions"
            if not sessions_dir.exists():
                continue
            for sess_dir in sessions_dir.iterdir():
                if not sess_dir.is_dir():
                    continue
                meta_path = sess_dir / "meta.yaml"
                if meta_path.exists():
                    meta = yaml.safe_load(meta_path.read_text()) or {}
                    meta["user"] = user_dir.name
                    sessions.append(meta)
        return sessions

    def _read_index(self) -> dict | None:
        path = self.root / ".sm" / "index.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return None
        return None

    def _update_index(self):
        """Rebuild the index cache."""
        sessions = self._scan_all_meta()
        index = {
            "updated": datetime.now().isoformat(),
            "sessions": sessions,
        }
        path = self.root / ".sm" / "index.json"
        path.write_text(json.dumps(index, indent=2, default=str))
