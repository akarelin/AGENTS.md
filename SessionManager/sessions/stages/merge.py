"""Merge stage — detect session groups across `.reset.*` / `.deleted.*`
snapshots, topic-suffix variants (`<uuid>-topic-<ts>.jsonl`), and (v2)
subagent trees.

v1 scope:
  - OpenClaw: find sibling `<uuid>.jsonl.reset.<iso>` / `.deleted.<iso>` files
    for each live record and record them under `paths.snapshots`.
  - Topic-suffix grouping: ingest already sets `session_group` for
    `-topic-<ts>` files; merge verifies and ensures the base record also
    carries the same `session_group`.
  - Subagent detection: scan first few lines for `[Subagent Task]` wrapper;
    if present, mark classification.is_subagent=True. Linking subagent
    children to their parent is v2 (requires walking OpenClaw's subagents
    runs.json).

Transitions: state ingested → merged (even if no group found).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .. import config as cfgmod
from ..orchestrator import StageResult
from ..record import SessionRecord
from ..store import SessionStore


RESET_SUFFIX_RE = re.compile(r"\.jsonl\.(reset|deleted)\.(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}(?:\.\d+)?Z?)(?:\.md)?$")
SUBAGENT_MARKER_RE = re.compile(r"\[Subagent Task\]", re.IGNORECASE)

# Claude Code resume-chain detection. Slack's ~8-hour "session continuation"
# window is too loose; start with 30 min. User-overridable via config.
RESUME_PREFIX_RE = re.compile(r"^\s*(Continue|Resume|This session is being continued)",
                              re.IGNORECASE)
DEFAULT_RESUME_WINDOW_S = 30 * 60


def _find_snapshots(base_jsonl: Path) -> list[str]:
    """Return paths to `.jsonl.reset.<ts>` / `.jsonl.deleted.<ts>` siblings."""
    if not base_jsonl.exists():
        return []
    parent = base_jsonl.parent
    stem = base_jsonl.stem  # e.g., 'f873a988-...' (no .jsonl extension)
    snapshots = []
    for sibling in parent.iterdir():
        if not sibling.is_file():
            continue
        name = sibling.name
        if not name.startswith(stem + ".jsonl."):
            continue
        m = RESET_SUFFIX_RE.search(name)
        if m:
            snapshots.append(str(sibling))
    return sorted(snapshots)


def _first_user_text(jsonl_path: Path, max_lines: int = 30) -> str | None:
    """Return the first non-empty user-role message text from a JSONL session.
    Handles Claude Code (`type: 'user', message.content`) and OpenClaw
    (`type: 'message', message.role == 'user'`) formats."""
    try:
        with open(jsonl_path, "rb") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                # Claude Code
                if entry.get("type") == "user":
                    msg = entry.get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, list):
                        content = " ".join(
                            p.get("text", "") for p in content
                            if isinstance(p, dict)
                        )
                    if isinstance(content, str) and content.strip():
                        return content
                # OpenClaw
                if entry.get("type") == "message":
                    msg = entry.get("message") or {}
                    if msg.get("role") == "user":
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            return content
    except OSError:
        pass
    return None


def _is_subagent(jsonl_path: Path) -> bool:
    """Sniff first few user-message lines for `[Subagent Task]` wrapper."""
    try:
        with open(jsonl_path, "rb") as f:
            for i, line in enumerate(f):
                if i > 30:
                    return False
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                msg = entry.get("message") or {}
                content = msg.get("content") or ""
                if isinstance(content, list):
                    content = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                if isinstance(content, str) and SUBAGENT_MARKER_RE.search(content):
                    return True
    except OSError:
        pass
    return False


def run(store: SessionStore, cfg: dict, *,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        source: str | None = None,
        source_id: str | None = None,
        **_: object) -> StageResult:
    result = StageResult(stage="merge")

    eligible_states = ["ingested", "orphan_snapshot"] if not force \
        else ["ingested", "orphan_snapshot", "merged"]
    records = store.select_by_state(eligible_states, limit=limit, source=source)

    for rec in records:
        if source_id is not None and rec.source_id != source_id:
            continue

        # Orphans use snapshot_jsonl; live records use raw_jsonl.
        raw = rec.paths.get("raw_jsonl") or rec.paths.get("snapshot_jsonl")
        if not raw:
            result.skipped += 1
            continue

        jsonl_path = Path(raw)
        changed = False

        # Snapshots (reset / deleted)
        snapshots = _find_snapshots(jsonl_path) if rec.source == "openclaw" else []
        if snapshots:
            rec.paths["snapshots"] = snapshots
            changed = True

        # Subagent detection
        if rec.source == "openclaw" and jsonl_path.exists() and jsonl_path.stat().st_size > 0:
            if _is_subagent(jsonl_path):
                rec.classification["is_subagent"] = True
                # Group all subagents under a meta group if not already grouped
                if rec.session_group is None:
                    rec.session_group = f"openclaw:subagent:{rec.agent}"
                changed = True

        # Cross-session resume-chain detection (Claude Code only).
        # Extends the v1 merge vocabulary to cover "Continue/Resume" sessions
        # the user starts in the same project dir shortly after a prior one.
        if rec.source == "claude-code" and rec.project and rec.started_at \
                and rec.session_group is None \
                and jsonl_path.exists() and jsonl_path.stat().st_size > 0:
            first = _first_user_text(jsonl_path)
            if first and RESUME_PREFIX_RE.match(first):
                window = int(((cfg.get("thresholds") or {})
                              .get("resume_chain_window_s")) or DEFAULT_RESUME_WINDOW_S)
                prev = store.previous_claude_session_in_project(
                    rec.project, rec.started_at, window)
                if prev and prev.source_id != rec.source_id:
                    group = prev.session_group or f"cc:resume-chain:{prev.source_id}"
                    rec.session_group = group
                    rec.classification["resume_chain_parent"] = prev.source_id
                    # Backfill parent's session_group so both sides join the same
                    # chain on first detection.
                    if prev.session_group != group:
                        prev.session_group = group
                        if not dry_run:
                            store.upsert(prev)
                    changed = True

        if dry_run:
            if changed:
                print(f"[merge] would update {rec.source}:{rec.source_id[:8]} "
                      f"snapshots={len(snapshots)} subagent={rec.classification.get('is_subagent', False)}")
            rec.transition("merged", stage="merge", notes="dry-run")
            result.processed += 1
            continue

        rec.transition("merged", stage="merge",
                       notes=f"snapshots={len(snapshots)}")
        store.upsert(rec)
        result.processed += 1

    return result
