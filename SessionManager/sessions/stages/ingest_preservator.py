"""Track 3 — multi-host ingest from preservator RAR archives on SD.Lake.

Walks `<sources.preservator.root>/<host>/YYYYMMDD/*.rar`, lists inner members
with `unrar lb`, filters by `inner_patterns`, stream-extracts each matching
member into a content-addressed cache, and upserts a SessionRecord.

Invoked by the same stage-runner as ingest.py when the preservator source is
selected:

    sm-pipeline run ingest_preservator
    sm-pipeline run ingest_preservator --source preservator --dry-run

Idempotence:
  - Cache key is sha256 of the extracted member → one copy per unique content
    across all hosts/dates.
  - SessionRecord primary key stays (source, source_id) where source_id for
    non-local hosts is "{hostname}:{uuid}". Re-ingest of the same member is a
    no-op; a newer RAR containing the same content appends to
    `paths.preservator_rar_history` and rewrites `paths.preservator_rar`.

Does not modify anything under ~/CRAP/preservator; this is a reader only.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .. import config as cfgmod
from ..orchestrator import StageResult
from ..record import SessionRecord, compute_content_hash
from ..store import SessionStore
from .ingest import _extract_claude_code, _extract_openclaw


# ───────────────────────────────────────────────────────────── path helpers ──

# Preservator writes one RAR per host per day. Example path under `root`:
#   alex-pc/20260421/prsvtr_alex-pc_20260421_120843.rar
RAR_PATH_RE = re.compile(
    r"^(?P<host>[^/]+)/(?P<date>\d{8})/prsvtr_(?P=host)_\d{8}_\d{6}\.rar$"
)

# Claude Code session UUID filename (ignore any -topic-<ts>- suffix).
_UUID_STEM_RE = re.compile(
    r"^(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?:-topic-\d+)?(?:-[A-Za-z0-9_-]+)?$",
    re.IGNORECASE,
)


def _iter_rars(root: Path) -> Iterable[tuple[str, str, Path]]:
    """Yield (host, date_str, rar_path) for each RAR under root."""
    if not root.is_dir():
        return
    for host_dir in sorted(root.iterdir()):
        if not host_dir.is_dir():
            continue
        for date_dir in sorted(host_dir.iterdir()):
            if not date_dir.is_dir() or not re.fullmatch(r"\d{8}", date_dir.name):
                continue
            for rar in sorted(date_dir.glob("*.rar")):
                rel = rar.relative_to(root).as_posix()
                if RAR_PATH_RE.match(rel):
                    yield host_dir.name, date_dir.name, rar


def _match_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def _source_from_member(member: str) -> str | None:
    """Decide which canonical source a matched member belongs to."""
    if "/.claude/projects/" in member:
        return "claude-code"
    if "/.openclaw/agents/" in member and "/sessions/" in member:
        return "openclaw"
    if "/.codex/sessions/" in member:
        return "codex"
    return None


# ─────────────────────────────────────────────────────────────── unrar glue ──

def _rar_binary() -> str:
    """Prefer `rar` (full binary, behaves well over pipes); fall back to
    `unrar`. The Homebrew `rar` cask's `unrar` deadlocks on stdin in some
    environments, so `rar` is the reliable default."""
    for cand in ("rar", "unrar"):
        path = shutil.which(cand)
        if path:
            return path
    raise RuntimeError("neither `rar` nor `unrar` is on PATH")


def _unrar_list(rar: Path, timeout_s: int = 180) -> list[str]:
    """Return the member list via `rar lb` (bare names, one per line)."""
    try:
        cp = subprocess.run(
            [_rar_binary(), "lb", "-p-", str(rar)],
            stdin=subprocess.DEVNULL,
            capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
        print(f"[ingest_preservator] rar lb failed for {rar.name}: {e}")
        return []
    if cp.returncode != 0:
        print(f"[ingest_preservator] rar lb rc={cp.returncode} on {rar.name}: "
              f"{cp.stderr.strip()[:200]}")
        return []
    return [ln for ln in cp.stdout.splitlines() if ln.strip()]


def _unrar_extract(rar: Path, member: str, dest: Path,
                   timeout_s: int = 300) -> bool:
    """Stream a single member to dest via `rar p -inul`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with open(tmp, "wb") as out:
            cp = subprocess.run(
                [_rar_binary(), "p", "-inul", "-p-", str(rar), member],
                stdin=subprocess.DEVNULL,
                stdout=out, stderr=subprocess.PIPE,
                timeout=timeout_s, check=False,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as e:
        tmp.unlink(missing_ok=True)
        print(f"[ingest_preservator] rar p failed {rar.name}:{member}: {e}")
        return False
    if cp.returncode != 0:
        tmp.unlink(missing_ok=True)
        print(f"[ingest_preservator] rar p rc={cp.returncode} on "
              f"{rar.name}:{member}: {cp.stderr.decode(errors='replace')[:200]}")
        return False
    os.replace(tmp, dest)
    return True


# ──────────────────────────────────────────────────────── content-addr cache ──

def _sha256_file(path: Path, bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(bufsize), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_layout(cache_root: Path, digest: str, member: str) -> Path:
    """Fan out cache by the first 2 hex chars to keep directory sizes sane.
    Path: <cache_root>/<aa>/<digest>/<basename>"""
    base = Path(member).name
    return cache_root / digest[:2] / digest / base


# ─────────────────────────────────────────────────── cross-host slug aliases ──

def _emit_host_slug_alias(cfg: dict, host: str, slug: str,
                          suggested: str | None) -> None:
    """Write a `host_slug_alias` hint to the review queue for Track 2."""
    queue_path = Path(cfgmod.expand(cfg["store"]["review_queue"]))
    try:
        data = json.loads(queue_path.read_text()) if queue_path.exists() else \
            {"version": 1, "items": []}
    except (OSError, json.JSONDecodeError):
        data = {"version": 1, "items": []}

    key = ("host_slug_alias", host, slug)
    for it in data.get("items", []):
        if (it.get("kind"), it.get("host"), it.get("slug")) == key and \
                it.get("status") == "pending":
            return

    data.setdefault("items", []).append({
        "kind": "host_slug_alias",
        "host": host,
        "slug": slug,
        "suggested_project": suggested,
        "evidence": "matching slug pattern on alex-mac"
             if suggested else "no local slug match — needs human mapping",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(data, indent=2))


def _local_claude_slugs() -> set[str]:
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return set()
    return {p.name for p in root.iterdir() if p.is_dir()}


def _suggest_project_from_slug(slug: str, local: set[str]) -> str | None:
    """Naive match: same slug, or a slug that collapses to the same suffix
    after dropping the drive-letter prefix (Windows `-C--Users-Alex-...`)."""
    if slug in local:
        # Same slug on multiple hosts = same project — project name is the slug
        # (Track 2 will resolve to canonical).
        return slug
    # Strip leading `-[A-Z]-` drive prefix common on Windows slugs.
    stripped = re.sub(r"^-[A-Z]--", "-", slug)
    if stripped != slug and stripped in local:
        return stripped
    # Tail match — last two path segments shared.
    tail = "-".join(slug.split("-")[-3:])
    for s in local:
        if s.endswith(tail) and len(tail) >= 6:
            return s
    return None


# ─────────────────────────────────────────────────────────── member → record ──

@dataclass
class _Member:
    host: str
    rar: Path
    member: str        # exact path as listed inside the rar
    source: str        # claude-code | openclaw | codex


def _make_source_id(host: str, stem: str) -> str:
    """Non-local sessions get a host-prefixed source_id to avoid UUID
    collisions across hosts. alex-mac ingest path does not flow through here."""
    return f"{host}:{stem}"


def _extract_record(m: _Member, cached: Path) -> SessionRecord | None:
    """Build a SessionRecord from a cached member file. Delegates to the
    existing per-source extractors for parsing."""
    if m.source == "claude-code":
        rec = _extract_claude_code(cached, {})
        slug = Path(m.member).parent.name  # <...>/projects/<slug>/<uuid>.jsonl
        rec.project = slug
    elif m.source == "openclaw":
        rec = _extract_openclaw(cached, {})
        # path-derived agent lookup in _extract_openclaw uses `path.parts`;
        # the cached filename loses that context, so recover agent from the
        # member path.
        parts = m.member.split("/")
        if "agents" in parts:
            try:
                rec.agent = parts[parts.index("agents") + 1]
            except IndexError:
                pass
    elif m.source == "codex":
        # codex v1: reuse claude-code-style parser — jsonl with timestamps;
        # there is no dedicated extractor yet. Produce a minimal record.
        rec = SessionRecord(
            source="codex",
            source_id=cached.stem,
            paths={"raw_jsonl": str(cached)},
            state="ingested",
        )
    else:
        return None

    # Override source_id with host-prefixed form (post-extract so path-derived
    # fields are still correct).
    stem = cached.stem
    mu = _UUID_STEM_RE.match(stem)
    if mu:
        stem = mu.group("uuid")
    rec.source_id = _make_source_id(m.host, stem)
    rec.paths["raw_jsonl"] = str(cached)
    rec.paths["preservator_rar"] = str(m.rar)
    rec.origin_host = m.host
    return rec


# ──────────────────────────────────────────────────────────────────── main ──

def _load_source_cfg(cfg: dict) -> dict | None:
    for src in cfg.get("sources", []):
        if src.get("name") == "preservator":
            return src
    return None


def run(store: SessionStore, cfg: dict, *,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        source: str | None = None,
        source_id: str | None = None,
        **_: object) -> StageResult:
    """Entry point wired into the same orchestrator as ingest."""
    result = StageResult(stage="ingest_preservator")

    # Respect --source filter: if the caller pinned a non-preservator source,
    # nothing to do.
    if source is not None and source != "preservator":
        return result

    src = _load_source_cfg(cfg)
    if src is None:
        return result

    root = Path(cfgmod.expand(src["root"]))
    if not root.is_dir():
        print(f"[ingest_preservator] root missing: {root}")
        return result

    patterns = list(src.get("inner_patterns") or [])
    if not patterns:
        print("[ingest_preservator] no inner_patterns configured; skipping")
        return result

    include = set(src.get("include_hosts") or [])
    exclude = set(src.get("exclude_hosts") or [])
    cache_root = Path(cfgmod.expand(src.get("cache_dir")
                                    or "~/.sessionskills/preservator-cache"))
    age_days = int(src.get("age_limit_days") or 0)
    cutoff = time.time() - age_days * 86400 if age_days > 0 else 0.0

    local_slugs = _local_claude_slugs()

    for host, date, rar in _iter_rars(root):
        if include and host not in include:
            continue
        if host in exclude:
            continue
        try:
            if cutoff and rar.stat().st_mtime < cutoff:
                result.skipped += 1
                continue
        except OSError:
            continue

        members = _unrar_list(rar)
        if not members:
            continue

        matching = [m for m in members if _match_any(m, patterns)]
        if not matching:
            continue

        print(f"[ingest_preservator] {host}/{date} {rar.name}: "
              f"{len(matching)}/{len(members)} members match")

        for member in matching:
            if limit is not None and result.processed >= limit:
                break

            sub = _source_from_member(member)
            if sub is None:
                continue

            # Extract into a throwaway path; rehome to cache after hashing.
            stage_path = cache_root / ".staging" / rar.stem / Path(member).name
            if dry_run:
                print(f"[ingest_preservator] would extract: "
                      f"{host}:{rar.name}:{member}")
                result.processed += 1
                continue

            if not _unrar_extract(rar, member, stage_path):
                result.errors += 1
                continue

            try:
                digest = _sha256_file(stage_path)
            except OSError:
                stage_path.unlink(missing_ok=True)
                result.errors += 1
                continue

            cached = _cache_layout(cache_root, digest, member)
            if not cached.exists():
                cached.parent.mkdir(parents=True, exist_ok=True)
                os.replace(stage_path, cached)
            else:
                stage_path.unlink(missing_ok=True)

            # Build record.
            m = _Member(host=host, rar=rar, member=member, source=sub)
            try:
                rec = _extract_record(m, cached)
            except Exception as e:
                print(f"[ingest_preservator] parse error {member}: {e}")
                result.errors += 1
                continue
            if rec is None:
                continue

            if source_id is not None and rec.source_id != source_id:
                continue

            # Content-hash dedup via the live records table.
            rec.content_hash = compute_content_hash(str(cached))

            existing = store.get(rec.source, rec.source_id)

            # Collision check: another host's record with the same content_hash
            # is the same conversation preserved in another RAR.
            if existing and existing.content_hash == rec.content_hash and not force:
                # §3.3: append the newer RAR path, refresh the primary pointer.
                hist = list(existing.paths.get("preservator_rar_history") or [])
                for p in (existing.paths.get("preservator_rar"), str(rar)):
                    if p and p not in hist:
                        hist.append(p)
                existing.paths["preservator_rar_history"] = hist
                existing.paths["preservator_rar"] = str(rar)
                existing.last_updated = datetime.now(timezone.utc).isoformat()
                store.upsert(existing)
                result.skipped += 1
                continue

            # Preserve prior classification / paths across re-ingest.
            if existing:
                rec.id = existing.id
                rec.first_seen = existing.first_seen
                merged = dict(existing.paths)
                hist = list(merged.get("preservator_rar_history") or [])
                if (merged.get("preservator_rar")
                        and merged["preservator_rar"] not in hist):
                    hist.append(merged["preservator_rar"])
                merged.update(rec.paths)
                merged["preservator_rar_history"] = hist
                rec.paths = merged
                if existing.classification:
                    rec.classification = {**existing.classification,
                                          **rec.classification}

            rec.transition("ingested", stage="ingest_preservator",
                           notes=f"{host} {rar.name} {Path(member).name}")
            store.upsert(rec)
            result.processed += 1

            # §3.4 — Track 2 slug-alias hint (Claude Code only; Windows-ish
            # slugs are the common cross-host case).
            if sub == "claude-code" and rec.project:
                suggested = _suggest_project_from_slug(rec.project, local_slugs)
                if suggested != rec.project:  # always emit for cross-host slugs
                    _emit_host_slug_alias(cfg, host, rec.project, suggested)
                    result.to_review += 1

        if limit is not None and result.processed >= limit:
            break

    return result
