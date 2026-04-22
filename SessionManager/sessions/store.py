"""SQLite-backed canonical record store.

Single table `records` with (source, source_id) unique index and dedicated
indexed columns for common filter/sort fields. Non-indexed fields live in a
single JSON column so schema migrations are cheap.

Stages interact via: upsert(record), get(source, source_id), select(state=...),
claim(source, source_id), transition(source, source_id, new_state, stage).
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

from .record import SessionRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    state         TEXT NOT NULL,
    agent         TEXT,
    project       TEXT,
    started_at    TEXT,
    session_group TEXT,
    content_hash  TEXT,
    first_seen    TEXT NOT NULL,
    last_updated  TEXT NOT NULL,
    json          TEXT NOT NULL,
    PRIMARY KEY (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_records_state         ON records(state);
CREATE INDEX IF NOT EXISTS idx_records_agent         ON records(agent);
CREATE INDEX IF NOT EXISTS idx_records_project       ON records(project);
CREATE INDEX IF NOT EXISTS idx_records_started_at    ON records(started_at);
CREATE INDEX IF NOT EXISTS idx_records_session_group ON records(session_group);

CREATE TABLE IF NOT EXISTS claims (
    source     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    stage      TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    PRIMARY KEY (source, source_id, stage)
);
"""


class SessionStore:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert(self, rec: SessionRecord) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO records (source, source_id, state, agent, project,
                        started_at, session_group, content_hash, first_seen, last_updated, json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, source_id) DO UPDATE SET
                        state=excluded.state,
                        agent=excluded.agent,
                        project=excluded.project,
                        started_at=excluded.started_at,
                        session_group=excluded.session_group,
                        content_hash=excluded.content_hash,
                        last_updated=excluded.last_updated,
                        json=excluded.json""",
                (rec.source, rec.source_id, rec.state, rec.agent, rec.project,
                 rec.started_at, rec.session_group, rec.content_hash,
                 rec.first_seen, rec.last_updated, rec.to_json()),
            )

    def get(self, source: str, source_id: str) -> SessionRecord | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT json FROM records WHERE source=? AND source_id=?",
                (source, source_id),
            ).fetchone()
        if row is None:
            return None
        return SessionRecord(**json.loads(row["json"]))

    def select_by_state(self, states: list[str], limit: int | None = None,
                        source: str | None = None) -> list[SessionRecord]:
        q = f"SELECT json FROM records WHERE state IN ({','.join('?' * len(states))})"
        params: list = list(states)
        if source is not None:
            q += " AND source = ?"
            params.append(source)
        q += " ORDER BY last_updated ASC"
        if limit is not None:
            q += f" LIMIT {int(limit)}"
        with self._conn() as c:
            rows = c.execute(q, params).fetchall()
        return [SessionRecord(**json.loads(r["json"])) for r in rows]

    def count_by_state(self) -> dict[str, int]:
        with self._conn() as c:
            rows = c.execute("SELECT state, COUNT(*) n FROM records GROUP BY state").fetchall()
        return {r["state"]: r["n"] for r in rows}

    def count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM records").fetchone()[0]

    def previous_claude_session_in_project(self, project: str, started_before: str,
                                           within_seconds: int) -> SessionRecord | None:
        """Find the most recent claude-code record in the same project that
        started within `within_seconds` of `started_before` (ISO-8601)."""
        if not project or not started_before:
            return None
        with self._conn() as c:
            row = c.execute(
                "SELECT json FROM records "
                "WHERE source = 'claude-code' AND project = ? "
                "  AND started_at IS NOT NULL AND started_at < ? "
                "  AND strftime('%s', ?) - strftime('%s', started_at) <= ? "
                "ORDER BY started_at DESC LIMIT 1",
                (project, started_before, started_before, int(within_seconds)),
            ).fetchone()
        if row is None:
            return None
        return SessionRecord(**json.loads(row["json"]))

    def known_langfuse_trace_ids(self) -> set[str]:
        """Return trace IDs already attached to any record via
        `paths.langfuse_trace_id`. Used by the langfuse-API ingest for dedupe."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT json_extract(json, '$.paths.langfuse_trace_id') AS t "
                "FROM records WHERE t IS NOT NULL"
            ).fetchall()
        return {r["t"] for r in rows if r["t"]}
