"""Canonical project registry + resolver (Track 2 §2.2).

Loads ~/_/KG/Project/_registry.yaml once and resolves SessionRecord →
canonical project id by priority:

  1. record.classification['canonical_project'] already set → return it
  2. claude-code source: raw_jsonl path's parent dir matches a project's
     `claude_code_slugs`
  3. openclaw source: record.agent matches a project's `openclaw_agents`
  4. langfuse source: trace tag matches a project's `langfuse_tag`
  5. fuzzy alias match against record.classification.topic_slug, name,
     project, or cwd basename (token overlap > 0.7)
  6. None — caller should enqueue an `unlinked_project` review item

The resolver returns a (canonical_project_id, task_id) tuple — task_id
is non-None only when the record's title or session_id is registered
under a task's `target_session_title` / `session_id` / `session_ids`
field of the project's `tasks:` block (§2.8).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


REGISTRY_PATH = Path(os.path.expanduser("~/_/KG/Project/_registry.yaml"))


@dataclass
class Project:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    claude_code_slugs: list[str] = field(default_factory=list)
    openclaw_agents: list[str] = field(default_factory=list)
    work_atom_slug: str | None = None
    langfuse_tag: str | None = None
    obsidian_page: str | None = None
    tasks: list[dict[str, Any]] = field(default_factory=list)

    def all_alias_tokens(self) -> set[str]:
        toks: set[str] = set()
        for s in [self.id, self.name, *self.aliases]:
            for t in _tokenize(s):
                toks.add(t)
        return toks


_REGISTRY_CACHE: list[Project] | None = None
_REGISTRY_MTIME: float | None = None


def load_registry(path: Path | str | None = None, *, force: bool = False) -> list[Project]:
    """Return the in-memory registry. Re-reads if the file mtime changed."""
    global _REGISTRY_CACHE, _REGISTRY_MTIME
    p = Path(path).expanduser() if path else REGISTRY_PATH
    if not p.exists():
        return []
    mtime = p.stat().st_mtime
    if not force and _REGISTRY_CACHE is not None and _REGISTRY_MTIME == mtime:
        return _REGISTRY_CACHE
    with open(p) as fh:
        data = yaml.safe_load(fh) or {}
    raw = data.get("projects", []) if isinstance(data, dict) else []
    projects: list[Project] = []
    for entry in raw:
        if not isinstance(entry, dict) or "id" not in entry:
            continue
        projects.append(Project(
            id=str(entry["id"]),
            name=str(entry.get("name") or entry["id"]),
            aliases=list(entry.get("aliases") or []),
            claude_code_slugs=list(entry.get("claude_code_slugs") or []),
            openclaw_agents=list(entry.get("openclaw_agents") or []),
            work_atom_slug=entry.get("work_atom_slug"),
            langfuse_tag=entry.get("langfuse_tag"),
            obsidian_page=entry.get("obsidian_page"),
            tasks=list(entry.get("tasks") or []),
        ))
    _REGISTRY_CACHE = projects
    _REGISTRY_MTIME = mtime
    return projects


def find_by_id(pid: str) -> Project | None:
    for p in load_registry():
        if p.id == pid:
            return p
    return None


def find_by_obsidian_page(page: str) -> Project | None:
    for p in load_registry():
        if p.obsidian_page and p.obsidian_page == page:
            return p
    return None


# ─── resolution ──────────────────────────────────────────────────────

def _tokenize(s: str) -> list[str]:
    if not s:
        return []
    out: list[str] = []
    cur = []
    for ch in s.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return [t for t in out if len(t) >= 2]


def _slug_from_jsonl(raw_jsonl: str | None) -> str | None:
    if not raw_jsonl:
        return None
    try:
        return Path(raw_jsonl).parent.name
    except Exception:
        return None


def _alias_overlap(record_tokens: set[str], project: Project) -> float:
    pt = project.all_alias_tokens()
    if not pt or not record_tokens:
        return 0.0
    inter = record_tokens & pt
    if not inter:
        return 0.0
    return len(inter) / max(1, min(len(pt), len(record_tokens)))


def resolve(record: Any) -> tuple[str | None, str | None]:
    """Return (canonical_project_id, task_id). Either may be None.

    `record` is duck-typed: a SessionRecord-like with .source, .agent,
    .classification (dict), .paths (dict), .source_id, .id (uuid).
    """
    cls = getattr(record, "classification", None) or {}
    paths = getattr(record, "paths", None) or {}
    source = getattr(record, "source", None)

    # 1. already resolved — trust it
    pid = cls.get("canonical_project")
    if pid:
        return pid, cls.get("task_id")

    projects = load_registry()
    if not projects:
        return None, None

    # 1.5. session_id explicitly registered under some project's tasks.
    # Strongest possible signal — overrides slug-based defaults.
    sid = getattr(record, "source_id", None)
    if sid:
        for p in projects:
            tid = _find_session_in_tasks(p.tasks, sid)
            if tid:
                return p.id, tid

    # 2. claude-code slug
    if source == "claude-code":
        slug = _slug_from_jsonl(paths.get("raw_jsonl"))
        if slug:
            for p in projects:
                if slug in p.claude_code_slugs:
                    return p.id, _resolve_task(p, record)

    # 3. openclaw agent
    if source == "openclaw":
        agent = getattr(record, "agent", None)
        if agent:
            for p in projects:
                if agent in p.openclaw_agents:
                    return p.id, _resolve_task(p, record)

    # 4. langfuse tag
    if source == "langfuse":
        tag = (cls.get("langfuse_project_tag")
               or paths.get("langfuse_project_tag"))
        if tag:
            for p in projects:
                if p.langfuse_tag and p.langfuse_tag == tag:
                    return p.id, _resolve_task(p, record)

    # 5. fuzzy alias overlap on best signal we have
    candidates: list[str] = []
    for key in ("topic_slug", "name", "category"):
        v = cls.get(key)
        if v:
            candidates.append(str(v))
    proj_field = getattr(record, "project", None)
    if proj_field:
        candidates.append(str(proj_field))
    cwd = getattr(record, "cwd", None)
    if cwd:
        candidates.append(Path(str(cwd)).name)
    if not candidates:
        return None, None
    record_tokens: set[str] = set()
    for c in candidates:
        record_tokens.update(_tokenize(c))
    if not record_tokens:
        return None, None
    best_p, best_score = None, 0.0
    for p in projects:
        score = _alias_overlap(record_tokens, p)
        if score > best_score:
            best_p, best_score = p, score
    if best_p and best_score >= 0.7:
        return best_p.id, _resolve_task(best_p, record)
    return None, None


def _find_session_in_tasks(nodes: Iterable[dict[str, Any]], sid: str) -> str | None:
    for t in nodes:
        if sid in (t.get("session_ids") or []) or t.get("session_id") == sid:
            return t.get("id")
        children = t.get("children") or []
        if children:
            hit = _find_session_in_tasks(children, sid)
            if hit:
                return hit
    return None


def _resolve_task(project: Project, record: Any) -> str | None:
    """Walk project.tasks to find a task referencing this session."""
    sid = getattr(record, "source_id", None)
    title = (getattr(record, "classification", {}) or {}).get("topic_slug")

    def walk(nodes: Iterable[dict[str, Any]]) -> str | None:
        for t in nodes:
            tid = t.get("id")
            if sid and (sid in (t.get("session_ids") or []) or t.get("session_id") == sid):
                return tid
            if title and t.get("target_session_title") == title:
                return tid
            children = t.get("children") or []
            if children:
                hit = walk(children)
                if hit:
                    return hit
        return None

    return walk(project.tasks)


def resolve_by_source_id(source: str, source_id: str) -> dict[str, Any]:
    """CLI helper: load record from store, resolve, return JSON-friendly dict."""
    from . import config as cfgmod
    from .store import SessionStore
    cfg = cfgmod.load()
    store = SessionStore(cfgmod.expand(cfg["store"]["path"]))
    rec = store.get(source, source_id)
    if rec is None:
        return {"error": f"no record for {source}:{source_id}"}
    canonical, task = resolve(rec)
    return {
        "source": source,
        "source_id": source_id,
        "canonical_project": canonical,
        "task_id": task,
        "project_name": find_by_id(canonical).name if canonical and find_by_id(canonical) else None,
    }


def all_aliases_index() -> dict[str, str]:
    """Flat alias-token → project-id map (debug helper)."""
    out: dict[str, str] = {}
    for p in load_registry():
        for a in [p.id, p.name, *p.aliases]:
            out[a] = p.id
    return out
