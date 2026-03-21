"""Session persistence — based on session continuity pattern (70 instances).

Stores conversation history so agents can resume across sessions.
Uses SQLite for DA sessions, gppu.Cache for Claude session cache.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from gppu.data import Cache as GppuCache


class SessionStore:
    """SQLite-backed session storage."""

    def __init__(self, db_path: str = "~/.da/sessions.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at REAL,
                updated_at REAL,
                project TEXT,
                agent TEXT DEFAULT 'orchestrator'
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT REFERENCES sessions(id),
                role TEXT,
                content TEXT,
                timestamp REAL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        self.conn.commit()
        # gppu Cache for Claude sessions (thread-safe, TTL-based)
        cache_dir = str(self.db_path.parent / "claude_cache")
        self._claude_cache = GppuCache(cache_dir, ttl=3600, backend="sqlite")

    def create_session(self, session_id: str, name: str = "", project: str = "") -> None:
        now = time.time()
        self.conn.execute(
            "INSERT OR REPLACE INTO sessions (id, name, created_at, updated_at, project) VALUES (?, ?, ?, ?, ?)",
            (session_id, name, now, now, project),
        )
        self.conn.commit()

    def add_message(self, session_id: str, role: str, content: Any) -> None:
        self.conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, json.dumps(content) if not isinstance(content, str) else content, time.time()),
        )
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (time.time(), session_id),
        )
        self.conn.commit()

    def get_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        messages = []
        for role, content, ts in reversed(rows):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass
            messages.append({"role": role, "content": content})
        return messages

    def list_sessions(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, name, project, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"id": r[0], "name": r[1], "project": r[2], "updated_at": r[3]}
            for r in rows
        ]

    def get_latest_session(self, project: str | None = None) -> dict | None:
        if project:
            row = self.conn.execute(
                "SELECT id, name, project, updated_at FROM sessions WHERE project = ? ORDER BY updated_at DESC LIMIT 1",
                (project,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT id, name, project, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 1",
            ).fetchone()
        if row:
            return {"id": row[0], "name": row[1], "project": row[2], "updated_at": row[3]}
        return None

    def delete_session(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def get_session_stats(self, session_id: str) -> dict:
        row = self.conn.execute(
            "SELECT id, name, project, created_at, updated_at, agent FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return {}
        msg_counts = self.conn.execute(
            "SELECT role, COUNT(*) FROM messages WHERE session_id = ? GROUP BY role",
            (session_id,),
        ).fetchall()
        total = self.conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        return {
            "id": row[0], "name": row[1], "project": row[2],
            "created_at": row[3], "updated_at": row[4], "agent": row[5],
            "message_counts": dict(msg_counts), "total_messages": total,
        }

    def list_sessions_detailed(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("""
            SELECT s.id, s.name, s.project, s.created_at, s.updated_at,
                   COUNT(m.id) as msg_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [
            {"id": r[0], "name": r[1], "project": r[2],
             "created_at": r[3], "updated_at": r[4], "msg_count": r[5]}
            for r in rows
        ]

    def rename_session(self, session_id: str, new_name: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET name = ? WHERE id = ?", (new_name, session_id)
        )
        self.conn.commit()

    def get_global_stats(self) -> dict:
        total_sessions = self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        total_messages = self.conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        roles = dict(self.conn.execute(
            "SELECT role, COUNT(*) FROM messages GROUP BY role"
        ).fetchall())
        projects = dict(self.conn.execute(
            "SELECT project, COUNT(*) FROM sessions WHERE project != '' GROUP BY project ORDER BY COUNT(*) DESC LIMIT 10"
        ).fetchall())
        oldest = self.conn.execute("SELECT MIN(created_at) FROM sessions").fetchone()[0]
        newest = self.conn.execute("SELECT MAX(updated_at) FROM sessions").fetchone()[0]
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "roles": roles,
            "projects": projects,
            "oldest": oldest,
            "newest": newest,
        }

    # --- Claude session cache (via gppu.Cache — thread-safe) ---

    def cache_claude_sessions_bulk(self, sessions: list[dict]) -> None:
        """Store all Claude sessions in gppu cache as a single key."""
        self._claude_cache.set("all_sessions", sessions)

    def get_cached_claude_sessions(self, max_age: float = 3600) -> list[dict]:
        """Get cached sessions. Returns empty if cache expired (TTL-based)."""
        return self._claude_cache.get("all_sessions", default=[])

    def clear_claude_cache(self) -> None:
        self._claude_cache.delete("all_sessions")

    def delete_cached_claude_session(self, session_id: str) -> None:
        sessions = self._claude_cache.get("all_sessions", default=[])
        sessions = [s for s in sessions if s.get("id") != session_id]
        self._claude_cache.set("all_sessions", sessions)

    def close(self):
        self.conn.close()
