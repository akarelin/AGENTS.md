"""Canonical session record shared across all pipeline stages.

Primary key for idempotence: (source, source_id). Every stage upserts by this
tuple; re-running a stage on an already-processed record is a no-op.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STATES = (
    "new",
    "ingested",
    "orphan_snapshot",   # v2 merge: reset/deleted JSONL whose live sibling is gone
    "merged",
    "named",
    "analyzed",
    "memorized",
    "clustered",
    "classified",
    "review_pending",
    "pruned",
    "archived",
    "kept",
)

SOURCES = (
    "claude-code",
    "openclaw",
    "codex",
    "langfuse",
    "chatgpt-export",
    "claude-export",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    # Identity
    source: str
    source_id: str
    agent: str | None = None
    project: str | None = None
    cwd: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    model: str | None = None
    provider: str | None = None

    # Stats
    turn_count: int = 0
    message_count: int = 0
    generation_count: int = 0
    error_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    # Grouping (.reset.* / -topic-* / subagent chains)
    session_group: str | None = None
    topic_chain: list[str] = field(default_factory=list)
    merged_into: str | None = None

    # Classification: filled incrementally by name/analyze/cluster/classify
    # Keys: category, topic_slug, importance, theme_id, work_atom_project,
    #       duplicate_of, confidence, tags
    classification: dict[str, Any] = field(default_factory=dict)

    # State machine
    state: str = "new"
    state_history: list[dict[str, Any]] = field(default_factory=list)

    # Paths: raw_jsonl, rendered_md, symlink_name, analyzed_md,
    #        langfuse_trace_id, memory_row_id, archive_tar,
    #        preservator_rar, preservator_rar_history
    paths: dict[str, Any] = field(default_factory=dict)

    # Track 3 — origin host. None on older rows is treated as 'alex-mac' by
    # readers; ingest stages set this explicitly going forward.
    origin_host: str | None = None

    # Bookkeeping
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    first_seen: str = field(default_factory=_now)
    last_updated: str = field(default_factory=_now)
    content_hash: str | None = None

    def key(self) -> tuple[str, str]:
        return (self.source, self.source_id)

    def transition(self, new_state: str, stage: str, notes: str = "") -> None:
        if new_state not in STATES:
            raise ValueError(f"unknown state: {new_state}")
        self.state_history.append(
            {"from": self.state, "to": new_state, "ts": _now(), "stage": stage, "notes": notes}
        )
        self.state = new_state
        self.last_updated = _now()

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SessionRecord":
        data = json.loads(row["json"])
        return cls(**data)


def compute_content_hash(path: str, head_bytes: int = 65536) -> str:
    """Hash first head_bytes of a file — stable enough for mid-write detection."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(head_bytes))
    return h.hexdigest()
