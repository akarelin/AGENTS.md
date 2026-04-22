"""link_project — stamp every record with its canonical project (Track 2 §2.3).

Runs after classify but doesn't advance state (it's a metadata-enrichment
pass that can re-run idempotently). For each eligible record:

  • call projects.resolve(rec) → (canonical_project_id, task_id | None)
  • set classification.canonical_project, canonical_project_name,
    task_id, task_parent_path
  • if unresolved → enqueue review item kind='unlinked_project'

Optional `--emit-obsidian` flag delegates to the obsidian_emit module
(sessions-on-project-pages renderer for §2.4).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .. import config as cfgmod
from .. import projects as projmod
from ..orchestrator import StageResult
from ..store import SessionStore


ELIGIBLE_STATES = ("analyzed", "memorized", "clustered", "classified")


def _load_queue(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "items": []}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "items": []}


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".review-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _task_parent_path(project: projmod.Project, task_id: str) -> str | None:
    """Build 'projectid/parent/.../task_id' path. Returns None if not found."""
    def walk(nodes: Iterable[dict[str, Any]], crumbs: list[str]) -> list[str] | None:
        for t in nodes:
            tid = t.get("id")
            new_crumbs = crumbs + [tid] if tid else crumbs
            if tid == task_id:
                return new_crumbs
            children = t.get("children") or []
            if children:
                hit = walk(children, new_crumbs)
                if hit:
                    return hit
        return None

    crumbs = walk(project.tasks, [project.id])
    return "/".join(crumbs) if crumbs else None


def run(store: SessionStore, cfg: dict, *,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        source: str | None = None,
        source_id: str | None = None,
        emit_obsidian: bool = False,
        **_: object) -> StageResult:
    result = StageResult(stage="link_project")

    # Force a fresh registry read on every run — picks up curator edits.
    projmod.load_registry(force=True)

    queue_path = Path(cfgmod.expand(cfg["store"]["review_queue"]))
    queue = _load_queue(queue_path)
    pending_unlinked = {
        tuple(it.get("record_ids", []))
        for it in queue["items"]
        if it.get("kind") == "unlinked_project" and it.get("status") == "pending"
    }

    eligible = list(ELIGIBLE_STATES)
    for rec in store.select_by_state(eligible, limit=limit, source=source):
        if source_id is not None and rec.source_id != source_id:
            continue

        existing = rec.classification.get("canonical_project")
        if existing and not force:
            result.skipped += 1
            continue

        canonical, task_id = projmod.resolve(rec)

        if canonical is None:
            key = (f"{rec.source}:{rec.source_id}",)
            if key in pending_unlinked:
                result.skipped += 1
                continue
            queue["items"].append({
                "kind": "unlinked_project",
                "record_ids": [f"{rec.source}:{rec.source_id}"],
                "proposal": {"canonical_project": None},
                "reason": (
                    f"no slug/agent/tag/alias match "
                    f"(topic_slug={rec.classification.get('topic_slug')!r}, "
                    f"agent={rec.agent!r})"
                ),
                "confidence": 0,
                "status": "pending",
                "created_at": rec.last_updated,
            })
            result.to_review += 1
            continue

        proj = projmod.find_by_id(canonical)
        rec.classification["canonical_project"] = canonical
        if proj:
            rec.classification["canonical_project_name"] = proj.name
        if task_id:
            rec.classification["task_id"] = task_id
            if proj:
                tpath = _task_parent_path(proj, task_id)
                if tpath:
                    rec.classification["task_parent_path"] = tpath
        if not dry_run:
            store.upsert(rec)
        result.processed += 1

    if not dry_run:
        _atomic_write(queue_path, queue)

    if emit_obsidian and not dry_run:
        from . import _obsidian_emit  # local import — avoids cost when unused
        wrote = _obsidian_emit.emit_all(store, cfg)
        print(f"[link_project] obsidian: wrote {wrote} project pages")

    return result
