"""
Thread — core abstraction for SessionManager.

A Thread is an ordered chain of chats linked as previous/next.
Everything is a Thread:
  - A single session is a Thread with one chat
  - A project is a Thread containing session Threads
  - A merged result is a Thread linking its source Threads

Threads can be merged (combine into one) and pruned (remove chats).
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Chat:
    """A single conversation unit within a Thread."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = ""               # user | assistant | system | tool
    content: str = ""
    timestamp: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    metadata: dict = field(default_factory=dict)

    # Linked list
    prev: str | None = None      # previous Chat ID
    next: str | None = None      # next Chat ID


@dataclass
class Thread:
    """Ordered chain of Chats with prev/next links.

    A Thread is the universal container:
      - Session: Thread with chats from one LLM conversation
      - Project: Thread whose chats are references to session Threads
      - Merged:  Thread combining multiple source Threads
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None
    kind: str = "session"        # session | project | merged | import
    source: str = ""             # claude-code | openclaw | chatgpt-export | ...
    source_file: str = ""
    source_host: str = ""

    # Chain
    chats: list[Chat] = field(default_factory=list)
    head: str | None = None      # first Chat ID
    tail: str | None = None      # last Chat ID

    # Thread links (Threads within Threads)
    parent: str | None = None    # parent Thread ID (project → session)
    children: list[str] = field(default_factory=list)
    prev_thread: str | None = None   # previous Thread in sequence
    next_thread: str | None = None   # next Thread in sequence

    # Merge tracking
    merged_from: list[str] = field(default_factory=list)
    merged_into: str | None = None

    # Metadata
    model: str = ""
    cwd: str = ""
    git_branch: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "active"       # active | completed | archived | merged | pruned
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    updated: str = field(default_factory=lambda: datetime.now().isoformat())

    # Stats (computed)
    @property
    def message_count(self) -> int:
        return len(self.chats)

    @property
    def total_tokens_in(self) -> int:
        return sum(c.tokens_in for c in self.chats)

    @property
    def total_tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.chats)

    @property
    def first_timestamp(self) -> str | None:
        return self.chats[0].timestamp if self.chats else None

    @property
    def last_timestamp(self) -> str | None:
        return self.chats[-1].timestamp if self.chats else None

    # ── Chain operations ─────────────────────────────────────────────

    def append(self, chat: Chat) -> None:
        """Append a Chat to the end of the chain."""
        if self.chats:
            last = self.chats[-1]
            last.next = chat.id
            chat.prev = last.id
        else:
            self.head = chat.id
        self.tail = chat.id
        self.chats.append(chat)
        self.updated = datetime.now().isoformat()

    def prepend(self, chat: Chat) -> None:
        """Prepend a Chat to the start of the chain."""
        if self.chats:
            first = self.chats[0]
            first.prev = chat.id
            chat.next = first.id
        else:
            self.tail = chat.id
        self.head = chat.id
        self.chats.insert(0, chat)
        self.updated = datetime.now().isoformat()

    def get_chat(self, chat_id: str) -> Chat | None:
        """Get a Chat by ID."""
        for c in self.chats:
            if c.id == chat_id:
                return c
        return None

    def walk(self) -> list[Chat]:
        """Walk the chain from head to tail following next links."""
        if not self.head:
            return list(self.chats)  # fallback to list order

        chat_map = {c.id: c for c in self.chats}
        result = []
        current = self.head
        visited = set()
        while current and current not in visited:
            visited.add(current)
            chat = chat_map.get(current)
            if not chat:
                break
            result.append(chat)
            current = chat.next
        return result

    # ── Merge ────────────────────────────────────────────────────────

    @staticmethod
    def merge(threads: list[Thread], name: str | None = None) -> Thread:
        """Merge multiple Threads into one new Thread.

        Chats are interleaved by timestamp. Source Threads are linked via merged_from.
        """
        merged = Thread(
            name=name or f"Merged: {', '.join(t.name or t.id[:8] for t in threads[:3])}",
            kind="merged",
            merged_from=[t.id for t in threads],
            tags=sorted(set(tag for t in threads for tag in t.tags)),
            source=threads[0].source if threads else "",
        )

        # Collect all chats with timestamps
        all_chats = []
        for t in threads:
            for c in t.walk():
                all_chats.append(c)

        # Sort by timestamp
        all_chats.sort(key=lambda c: c.timestamp or "")

        # Re-link as a new chain
        for chat in all_chats:
            new_chat = Chat(
                id=chat.id,
                role=chat.role,
                content=chat.content,
                timestamp=chat.timestamp,
                model=chat.model,
                tokens_in=chat.tokens_in,
                tokens_out=chat.tokens_out,
                metadata={**chat.metadata, "original_thread": next(
                    (t.id for t in threads if any(c.id == chat.id for c in t.chats)), None
                )},
            )
            merged.append(new_chat)

        # Mark sources as merged
        for t in threads:
            t.merged_into = merged.id
            t.status = "merged"

        return merged

    # ── Prune ────────────────────────────────────────────────────────

    def prune(self, keep_roles: set[str] | None = None,
              keep_last: int | None = None,
              remove_ids: set[str] | None = None) -> int:
        """Prune chats from the Thread.

        Args:
            keep_roles: Only keep chats with these roles (e.g. {"user", "assistant"})
            keep_last: Only keep the last N chats
            remove_ids: Remove specific chat IDs

        Returns:
            Number of chats removed
        """
        original_count = len(self.chats)

        if remove_ids:
            self.chats = [c for c in self.chats if c.id not in remove_ids]

        if keep_roles:
            self.chats = [c for c in self.chats if c.role in keep_roles]

        if keep_last and len(self.chats) > keep_last:
            self.chats = self.chats[-keep_last:]

        # Re-link chain
        self._relink()
        self.updated = datetime.now().isoformat()
        return original_count - len(self.chats)

    def _relink(self):
        """Rebuild prev/next links after modification."""
        for i, chat in enumerate(self.chats):
            chat.prev = self.chats[i - 1].id if i > 0 else None
            chat.next = self.chats[i + 1].id if i < len(self.chats) - 1 else None
        self.head = self.chats[0].id if self.chats else None
        self.tail = self.chats[-1].id if self.chats else None

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "source_file": self.source_file,
            "source_host": self.source_host,
            "head": self.head,
            "tail": self.tail,
            "parent": self.parent,
            "children": self.children,
            "prev_thread": self.prev_thread,
            "next_thread": self.next_thread,
            "merged_from": self.merged_from,
            "merged_into": self.merged_into,
            "model": self.model,
            "cwd": self.cwd,
            "git_branch": self.git_branch,
            "tags": self.tags,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
            "message_count": self.message_count,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "chats": [asdict(c) for c in self.chats],
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Thread:
        chats = [Chat(**c) for c in d.pop("chats", [])]
        # Remove computed properties
        d.pop("message_count", None)
        d.pop("total_tokens_in", None)
        d.pop("total_tokens_out", None)
        t = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        t.chats = chats
        return t

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_json(cls, s: str) -> Thread:
        return cls.from_dict(json.loads(s))

    # ── JSONL conversion ─────────────────────────────────────────────

    @classmethod
    def from_jsonl(cls, path: str | Path, source: str = "unknown") -> Thread:
        """Create a Thread from a local JSONL session file."""
        path = Path(path)
        thread = cls(
            source=source,
            source_file=str(path),
            source_host=os.uname().nodename,
        )

        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                entry_type = d.get("type", "")
                ts = d.get("timestamp", "")

                # Session metadata
                if entry_type == "session":
                    thread.id = d.get("id", thread.id)
                    if not thread.source or thread.source == "unknown":
                        thread.source = "openclaw" if d.get("version") else "unknown"
                    thread.cwd = d.get("cwd", thread.cwd)

                # Model info
                if entry_type == "model_change":
                    thread.model = d.get("modelId", thread.model)

                # Messages
                msg = d.get("message", d)
                role = msg.get("role", "")
                if role not in ("user", "assistant", "tool", "toolResult", "system"):
                    continue

                # Normalize role
                if role == "toolResult":
                    role = "tool"

                # Extract content
                content = msg.get("content", "")
                if isinstance(content, list):
                    texts = [b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text"]
                    content = "\n".join(texts)

                # Extract model/tokens from assistant messages
                model = msg.get("model", "")
                usage = msg.get("usage", {})
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)

                if not thread.source or thread.source == "unknown":
                    if d.get("entrypoint") == "sdk-cli":
                        thread.source = "claude-code"

                if d.get("cwd") and not thread.cwd:
                    thread.cwd = d["cwd"]
                if d.get("gitBranch") and not thread.git_branch:
                    thread.git_branch = d["gitBranch"]
                if model and not thread.model:
                    thread.model = model

                # Session ID
                sid = d.get("sessionId")
                if sid and thread.id == thread.id:  # only if still default
                    thread.id = sid

                chat = Chat(
                    role=role,
                    content=content[:5000],  # truncate very long content
                    timestamp=ts,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                )
                thread.append(chat)

        return thread

    def to_jsonl(self, path: str | Path) -> None:
        """Export Thread back to JSONL format."""
        path = Path(path)
        with open(path, "w") as f:
            # Session header
            f.write(json.dumps({
                "type": "session",
                "id": self.id,
                "timestamp": self.created,
                "cwd": self.cwd,
                "source": self.source,
            }) + "\n")

            for chat in self.walk():
                f.write(json.dumps({
                    "type": "message",
                    "timestamp": chat.timestamp,
                    "message": {
                        "role": chat.role,
                        "content": [{"type": "text", "text": chat.content}],
                        "model": chat.model,
                        "usage": {
                            "input_tokens": chat.tokens_in,
                            "output_tokens": chat.tokens_out,
                        },
                    },
                }) + "\n")


# ── Project as Thread ────────────────────────────────────────────────────────

def create_project_thread(slug: str, name: str, session_threads: list[Thread]) -> Thread:
    """Create a project Thread that links session Threads as children."""
    project = Thread(
        name=name,
        kind="project",
        tags=[slug],
        children=[t.id for t in session_threads],
    )

    # Link sessions in sequence
    for i, t in enumerate(session_threads):
        t.parent = project.id
        if i > 0:
            t.prev_thread = session_threads[i - 1].id
            session_threads[i - 1].next_thread = t.id

        # Add a reference chat to the project thread
        project.append(Chat(
            role="system",
            content=f"Session: {t.name or t.id[:12]} ({t.source}, {t.message_count} messages)",
            timestamp=t.first_timestamp or "",
            metadata={"ref_thread": t.id},
        ))

    return project
