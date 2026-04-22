"""Ingest stage — discover new JSONLs across configured sources and create
canonical SessionRecord rows in state='ingested'.

Sources (from sessionskills.yaml `sources`):
  - claude-code: ~/.claude/projects/<slug>/*.jsonl
  - openclaw:    ~/.openclaw/agents/<agent>/sessions/*.jsonl
  - langfuse:    pull traces via API (only when --backfill or enabled)

Per file:
  - Extract sessionId (filename stem; honor Claude Code inline `custom-title`)
  - Extract agent (openclaw: path-derived) or project (claude-code: path-derived)
  - Parse first + last timestamps, message count, model
  - Compute content_hash (first 64KB). If existing record has same hash and
    state > 'ingested', skip. If hash differs, re-upsert as 'ingested' so
    downstream stages re-process.

Idempotent: re-running produces processed=0 on unchanged files.
"""
from __future__ import annotations

import base64
import fnmatch
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .. import config as cfgmod
from ..orchestrator import StageResult
from ..record import SessionRecord, compute_content_hash
from ..store import SessionStore


# ────────────────────────────────────────────────────────────────── helpers ──

def _iter_files(root: Path, patterns: list[str], excludes: list[str]) -> Iterable[Path]:
    """Walk root matching any of `patterns` but not `excludes` (glob)."""
    for pat in patterns:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            name = p.name
            if any(fnmatch.fnmatch(name, ex) for ex in excludes):
                continue
            yield p


def _parse_ts(s: str | None) -> str | None:
    if not s:
        return None
    # Most sources produce ISO8601 already; just normalize
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return s


def _parse_jsonl_head_tail(path: Path, head_lines: int = 200,
                           tail_lines: int = 50) -> tuple[list[dict], list[dict]]:
    """Read first N and last M JSONL entries — enough to extract stats without
    loading GB files."""
    head: list[dict] = []
    tail: list[dict] = []
    try:
        with open(path, "rb") as f:
            for i, line in enumerate(f):
                if i >= head_lines:
                    break
                try:
                    head.append(json.loads(line))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        # Tail via seek from end — conservative: only last 256KB
        size = path.stat().st_size
        with open(path, "rb") as f:
            if size > 262144:
                f.seek(size - 262144)
                f.readline()  # discard partial
            data = f.read()
        for line in data.splitlines()[-tail_lines:]:
            try:
                tail.append(json.loads(line))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    except OSError:
        pass
    return head, tail


# ────────────────────────────────────────────────────────────── claude-code ──

def _extract_claude_code(path: Path, source_cfg: dict) -> SessionRecord:
    """Claude Code: ~/.claude/projects/<slug>/<session-uuid>.jsonl.

    Format per line:
      {"type":"user"|"assistant"|"tool_result", "message":{...}, "cwd":"...",
       "gitBranch":"...", "sessionId":"..."}
    May contain inline {"type":"custom-title","customTitle":"..."} entries.
    """
    head, tail = _parse_jsonl_head_tail(path)
    session_id = path.stem
    project = None
    # project slug = parent dir name under ~/.claude/projects/
    try:
        project = path.parent.name
    except Exception:
        pass

    cwd = None
    git_branch = None
    model = None
    provider = None
    started_at = None
    ended_at = None
    custom_title = None
    user_turns = 0
    message_count = 0

    for entry in head:
        t = entry.get("type")
        if t == "custom-title":
            custom_title = entry.get("customTitle")
        if cwd is None:
            cwd = entry.get("cwd")
        if git_branch is None:
            git_branch = entry.get("gitBranch")
        ts = entry.get("timestamp")
        if ts and started_at is None:
            started_at = _parse_ts(ts)
        if t == "user":
            user_turns += 1
            message_count += 1
        elif t == "assistant":
            message_count += 1
            if model is None:
                msg = entry.get("message") or {}
                model = msg.get("model") or entry.get("model")

    for entry in tail:
        if entry.get("timestamp"):
            ended_at = _parse_ts(entry["timestamp"])
            break

    rec = SessionRecord(
        source="claude-code",
        source_id=session_id,
        agent=None,
        project=project,
        cwd=cwd,
        started_at=started_at,
        ended_at=ended_at,
        model=model,
        provider=provider,
        turn_count=user_turns,
        message_count=message_count,
        paths={"raw_jsonl": str(path)},
        state="ingested",
    )
    if custom_title:
        rec.classification["custom_title"] = custom_title
    return rec


# ──────────────────────────────────────────────────────────────── openclaw ──

def _extract_openclaw(path: Path, source_cfg: dict) -> SessionRecord:
    """OpenClaw: ~/.openclaw/agents/<agent>/sessions/<uuid>(-topic-<ts>)?.jsonl.

    Format per line (version 3):
      {"type":"session", "id":"...", "timestamp":"...", "cwd":"..."}
      {"type":"model_change", "provider":"...", "modelId":"..."}
      {"type":"message", "message":{"role":"user"|"assistant"|"toolResult",...}}
    """
    head, tail = _parse_jsonl_head_tail(path)
    session_id = path.stem
    # agent derived from path: ~/.openclaw/agents/<agent>/sessions/...
    agent = None
    try:
        # .../agents/<agent>/sessions/file.jsonl
        parts = path.parts
        if "agents" in parts:
            agent = parts[parts.index("agents") + 1]
    except (IndexError, ValueError):
        pass

    # detect -topic-<ts> suffix (same session_group as base)
    session_group = None
    if "-topic-" in path.stem:
        base = path.stem.split("-topic-", 1)[0]
        session_group = f"openclaw:{base}"

    cwd = None
    model = None
    provider = None
    started_at = None
    ended_at = None
    user_turns = 0
    message_count = 0

    for entry in head:
        t = entry.get("type")
        if t == "session":
            started_at = _parse_ts(entry.get("timestamp"))
            cwd = cwd or entry.get("cwd")
        elif t == "model_change":
            provider = provider or entry.get("provider")
            model = model or entry.get("modelId")
        elif t == "message":
            message_count += 1
            msg = entry.get("message") or {}
            if msg.get("role") == "user":
                user_turns += 1

    for entry in tail:
        ts = entry.get("timestamp")
        if ts:
            ended_at = _parse_ts(ts)
            break

    return SessionRecord(
        source="openclaw",
        source_id=session_id,
        agent=agent,
        project=None,
        cwd=cwd,
        started_at=started_at,
        ended_at=ended_at,
        model=model,
        provider=provider,
        turn_count=user_turns,
        message_count=message_count,
        session_group=session_group,
        paths={"raw_jsonl": str(path)},
        state="ingested",
    )


EXTRACTORS = {
    "claude-code": _extract_claude_code,
    "openclaw": _extract_openclaw,
}


# ──────────────────────────────────────────────────────────────── langfuse ──

_SINCE_RE = re.compile(r"^(\d+)([dhm])$")


def _parse_since(spec: str | None) -> str | None:
    """Turn '7d' / '12h' / '90m' → ISO8601 `fromTimestamp` arg with a
    trailing `Z` (Langfuse's datetime validator rejects the `+00:00`
    offset form)."""
    if not spec:
        return None
    m = _SINCE_RE.match(spec.strip())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    delta = {"d": timedelta(days=n), "h": timedelta(hours=n),
             "m": timedelta(minutes=n)}[unit]
    return (datetime.now(timezone.utc) - delta).isoformat().replace("+00:00", "Z")


def _langfuse_auth(src: dict) -> str | None:
    """Return 'Basic <b64>' header or None if credentials missing."""
    env_keys = src.get("auth_env") or ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
    pk = os.environ.get(env_keys[0]) if len(env_keys) >= 1 else None
    sk = os.environ.get(env_keys[1]) if len(env_keys) >= 2 else None
    if not pk or not sk:
        return None
    return "Basic " + base64.b64encode(f"{pk}:{sk}".encode()).decode()


def _langfuse_get(host: str, path: str, params: dict, auth: str) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
    url = f"{host.rstrip('/')}{path}?{qs}"
    req = urllib.request.Request(
        url, headers={"Authorization": auth, "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _trace_to_record(trace: dict) -> SessionRecord:
    meta = trace.get("metadata") or {}
    trace_id = trace.get("id")
    tags = trace.get("tags") or []
    rec = SessionRecord(
        source="langfuse",
        source_id=trace_id,
        project=meta.get("project"),
        cwd=meta.get("cwd"),
        started_at=_parse_ts(trace.get("timestamp")),
        model=meta.get("model"),
        provider=meta.get("provider"),
        input_tokens=int(meta.get("total_input_tokens") or 0),
        output_tokens=int(meta.get("total_output_tokens") or 0),
        paths={"langfuse_trace_id": trace_id},
        state="ingested",
    )
    if tags:
        rec.classification["langfuse_tags"] = tags
    if trace.get("name"):
        rec.classification["langfuse_name"] = trace["name"]
    return rec


def _pull_langfuse(store: "SessionStore", src: dict, *,
                   limit: int | None, dry_run: bool,
                   force: bool, result: "StageResult") -> None:
    host = src.get("host")
    if not host:
        print("[ingest:langfuse] no host configured; skipping")
        return
    auth = _langfuse_auth(src)
    if not auth:
        print("[ingest:langfuse] missing LANGFUSE_PUBLIC_KEY/SECRET_KEY; skipping")
        return

    known = store.known_langfuse_trace_ids() if not force else set()
    since = _parse_since(src.get("pull_since"))
    page_size = int(src.get("page_size") or 100)
    max_pages = int(src.get("max_pages") or 200)

    for page in range(1, max_pages + 1):
        if limit is not None and result.processed >= limit:
            break
        params = {"page": page, "limit": page_size}
        if since:
            params["fromTimestamp"] = since
        try:
            data = _langfuse_get(host, "/api/public/traces", params, auth)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f"[ingest:langfuse] page {page} failed: {e}")
            result.errors += 1
            break
        rows = data.get("data") or []
        if not rows:
            break
        for trace in rows:
            if limit is not None and result.processed >= limit:
                break
            tid = trace.get("id")
            if not tid:
                continue
            if tid in known and not force:
                result.skipped += 1
                continue
            existing = store.get("langfuse", tid)
            if existing and not force:
                result.skipped += 1
                continue
            if dry_run:
                print(f"[ingest:langfuse] would ingest: langfuse:{tid}")
                result.processed += 1
                continue
            try:
                rec = _trace_to_record(trace)
                rec.transition("ingested", stage="ingest",
                               notes=f"langfuse pull page={page}")
                store.upsert(rec)
                known.add(tid)
                result.processed += 1
            except Exception as e:
                print(f"[ingest:langfuse] error on trace {tid[:8]}: {e}")
                result.errors += 1
        total = ((data.get("meta") or {}).get("totalItems")) or 0
        if total and page * page_size >= total:
            break


# ─────────────────────────────────────────────────────────── orphan snapshots ──

# Matches: <uuid>.jsonl.reset.<iso>  or  <uuid>.jsonl.deleted.<iso>
ORPHAN_SUFFIX_RE = re.compile(
    r"^(?P<base>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"(?:-topic-\d+)?)"
    r"\.jsonl\.(?P<kind>reset|deleted)\."
    r"(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}(?:\.\d+)?Z?)"
    r"(?:\.md)?$",
    re.IGNORECASE,
)


def _iter_orphan_files(root: Path):
    """Walk ~/.openclaw/agents/<agent>/sessions/ for *.jsonl.reset.* / *.deleted.*"""
    if not root.exists():
        return
    for agent_dir in root.iterdir():
        if not agent_dir.is_dir():
            continue
        sessions_dir = agent_dir / "sessions"
        if not sessions_dir.is_dir():
            continue
        for f in sessions_dir.iterdir():
            if not f.is_file():
                continue
            m = ORPHAN_SUFFIX_RE.match(f.name)
            if m:
                yield f, m.group("base"), m.group("kind"), m.group("ts"), agent_dir.name


def _extract_orphan(path: Path, base_uuid: str, kind: str, ts: str,
                   agent: str) -> SessionRecord:
    """Parse a .reset.*/.deleted.* snapshot as a regular OpenClaw JSONL
    but tag it as an orphan_snapshot record with its own source_id."""
    head, tail = _parse_jsonl_head_tail(path)

    # Canonical orphan source_id: base-orphan-<kind>-<ts>
    # Stays stable so re-ingestion is idempotent.
    source_id = f"{base_uuid}-orphan-{kind}-{ts}"

    cwd = None
    model = None
    provider = None
    started_at = None
    ended_at = None
    user_turns = 0
    message_count = 0

    for entry in head:
        t = entry.get("type")
        if t == "session":
            started_at = _parse_ts(entry.get("timestamp"))
            cwd = cwd or entry.get("cwd")
        elif t == "model_change":
            provider = provider or entry.get("provider")
            model = model or entry.get("modelId")
        elif t == "message":
            message_count += 1
            msg = entry.get("message") or {}
            if msg.get("role") == "user":
                user_turns += 1

    for entry in tail:
        ts_v = entry.get("timestamp")
        if ts_v:
            ended_at = _parse_ts(ts_v)
            break

    rec = SessionRecord(
        source="openclaw",
        source_id=source_id,
        agent=agent,
        project=None,
        cwd=cwd,
        started_at=started_at,
        ended_at=ended_at,
        model=model,
        provider=provider,
        turn_count=user_turns,
        message_count=message_count,
        # All orphans for the same base_uuid share a session_group so merge
        # stage can navigate reset chains.
        session_group=f"openclaw:orphan-chain:{base_uuid}",
        paths={"snapshot_jsonl": str(path)},
        state="orphan_snapshot",
    )
    rec.classification["orphan_kind"] = kind
    rec.classification["base_uuid"] = base_uuid
    rec.classification["orphan_ts"] = ts
    return rec


# ──────────────────────────────────────────────────────────────────── main ──

def run(store: SessionStore, cfg: dict, *,
        limit: int | None = None,
        dry_run: bool = False,
        force: bool = False,
        source: str | None = None,
        source_id: str | None = None,
        backfill: bool = False,
        **_: object) -> StageResult:
    result = StageResult(stage="ingest")

    for src in cfg.get("sources", []):
        if source is not None and src["name"] != source:
            continue
        kind = src.get("kind")
        if kind == "api":
            # Langfuse pull gated by backfill flag OR source.enabled.
            if not backfill and not src.get("enabled", False):
                continue
            if src.get("name") == "langfuse":
                _pull_langfuse(store, src, limit=limit, dry_run=dry_run,
                               force=force, result=result)
            else:
                print(f"[ingest] unsupported api source={src['name']}; skipping")
            continue
        if kind == "rar":
            # Track 3 — delegate to the preservator RAR reader. Mutates the
            # same StageResult so the caller sees aggregate counts.
            from . import ingest_preservator
            sub_src = src["name"]
            sub = ingest_preservator.run(
                store, cfg, limit=limit, dry_run=dry_run, force=force,
                source=sub_src, source_id=source_id,
            )
            result.processed += sub.processed
            result.skipped += sub.skipped
            result.errors += sub.errors
            result.to_review += sub.to_review
            continue
        if kind != "jsonl":
            continue

        root = Path(cfgmod.expand(src["root"]))
        if not root.exists():
            continue
        patterns = src.get("patterns", [])
        excludes = src.get("exclude_patterns", []) + src.get("exclude", [])
        extractor = EXTRACTORS.get(src["name"])
        if extractor is None:
            print(f"[ingest] no extractor for source={src['name']}; skipping")
            continue

        for path in _iter_files(root, patterns, excludes):
            if limit is not None and result.processed >= limit:
                break
            # Idempotence: skip if hash matches existing record's content_hash
            # AND record state is already past 'ingested' AND not force.
            try:
                h = compute_content_hash(str(path))
            except OSError:
                result.errors += 1
                continue

            if source_id is not None and path.stem != source_id:
                continue

            existing = store.get(src["name"], path.stem)
            if existing and existing.content_hash == h and not force:
                if existing.state != "new":
                    result.skipped += 1
                    continue

            if dry_run:
                print(f"[ingest] would ingest: {src['name']}:{path.stem} ({path})")
                result.processed += 1
                continue

            try:
                rec = extractor(path, src)
                rec.content_hash = h
                # Track 3 — local-fs ingest is always this host; cross-host
                # ingest lives in ingest_preservator.
                rec.origin_host = "alex-mac"
                # Preserve existing classification / paths on re-ingest
                if existing:
                    rec.id = existing.id
                    rec.first_seen = existing.first_seen
                    merged_paths = dict(existing.paths)
                    merged_paths.update(rec.paths)
                    rec.paths = merged_paths
                    if existing.classification:
                        merged_cls = dict(existing.classification)
                        merged_cls.update(rec.classification)
                        rec.classification = merged_cls
                rec.transition("ingested", stage="ingest",
                               notes=f"file={path.name}")
                store.upsert(rec)
                result.processed += 1
            except Exception as e:
                print(f"[ingest] error on {path}: {e}")
                result.errors += 1

        if limit is not None and result.processed >= limit:
            break

    # v2 merge: orphan .reset.*/.deleted.* snapshots (OpenClaw only for now).
    # Runs once after normal jsonl ingest. Gated by sources[name='openclaw']
    # orphan_snapshots.enabled (defaults to true if the key block is present).
    if source is None or source == "openclaw":
        for src in cfg.get("sources", []):
            if src.get("name") != "openclaw":
                continue
            cfg_orphan = src.get("orphan_snapshots") or {}
            if cfg_orphan.get("enabled") is False:
                continue
            root = Path(cfgmod.expand(src["root"]))
            if not root.exists():
                continue
            for path, base, kind, ts, agent in _iter_orphan_files(root):
                if limit is not None and result.processed >= limit:
                    break
                if source_id is not None and base != source_id and \
                        f"{base}-orphan-{kind}-{ts}" != source_id:
                    continue
                try:
                    h = compute_content_hash(str(path))
                except OSError:
                    result.errors += 1
                    continue
                ssid = f"{base}-orphan-{kind}-{ts}"
                existing = store.get("openclaw", ssid)
                if existing and existing.content_hash == h and not force:
                    result.skipped += 1
                    continue
                if dry_run:
                    print(f"[ingest:orphan] would ingest: openclaw:{ssid} ({path.name})")
                    result.processed += 1
                    continue
                try:
                    rec = _extract_orphan(path, base, kind, ts, agent)
                    rec.content_hash = h
                    rec.origin_host = "alex-mac"
                    if existing:
                        rec.id = existing.id
                        rec.first_seen = existing.first_seen
                        rec.paths = {**existing.paths, **rec.paths}
                        rec.classification = {**existing.classification, **rec.classification}
                    rec.transition("orphan_snapshot", stage="ingest",
                                   notes=f"{kind} snapshot of {base[:8]}")
                    store.upsert(rec)
                    result.processed += 1
                except Exception as e:
                    print(f"[ingest:orphan] error on {path}: {e}")
                    result.errors += 1

    return result
