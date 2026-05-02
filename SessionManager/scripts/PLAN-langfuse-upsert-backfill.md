# Plan: OTEL Trace Enrichment + Backfill

**Status:** Closed — completed 2026-04-21, verified 2026-04-22.

**Outcome:** Implemented in `session-to-langfuse.py`. Bulk run via `sm deposit-all`: 6,348 events deposited, 0 failed, 72 min wall time. Langfuse `meta.totalItems` = 5,925 post-run (≥ 3,172 local target ✓). Idempotency proven by re-runs: deterministic `_make_trace_id()` / `_make_obs_id()` (SHA-256 of session ID) cause Langfuse `trace-create` and observation events to upsert instead of duplicate. Tracked in `../TASKS.md` Phase 3 Track 1 §1.1; Track 1 closed 2026-04-22 (session `b1c418ff`).

## Context

OTEL traces flow in real-time from Claude Code and chmo through the OTEL collector to Langfuse (`langfuse.karelin.ai`). They have token usage and structural spans but lack tags, project names, input/output content, and `userId`. The existing `SessionEnd` hook (`session-to-langfuse.py`) has all this data but currently creates a **separate** trace with a different trace ID, causing duplicates.

**Goal**: Modify the hook to upsert the OTEL trace (enrich it with tags/metadata) instead of creating a new one. Add a backfill command to process historical JSONL files.

## Key Discovery

The Langfuse ingestion API `trace-create` acts as an **upsert** when given an existing trace ID — it merges fields including tags. This is already used in `sm.py` via `ingest_trace_update()` (line 83). So the hook can find the OTEL trace by session ID and enrich it without creating duplicates.

## Files to Modify

- `SessionManager/scripts/session-to-langfuse.py` — main changes

## Langfuse Config

- **Host**: `https://langfuse.karelin.ai`
- **Public key**: `pk-lf-xsolla-main-2026`
- **Secret key**: `sk-lf-xsolla-main-2026-secret-changeme`
- **OTEL collector**: `http://langfuse.karelin.ai:4318` (transforms attributes before forwarding to Langfuse)
- **Ingestion API**: `POST /api/public/ingestion` with Basic auth
- **Traces API**: `GET /api/public/traces?sessionId={id}` to find existing traces

## Approach

### 1. Add `find_otel_trace()` helper

```python
def find_otel_trace(session_id: str) -> dict | None:
    """Find an existing OTEL trace by sessionId."""
    url = f"{LANGFUSE_HOST}/api/public/traces?sessionId={session_id}&limit=5"
    # Auth: Basic base64(LANGFUSE_PUBLIC_KEY:LANGFUSE_SECRET_KEY)
    # Return first trace that was NOT created by this script
    # (OTEL traces have no "source": "claude-code" in metadata)
```

### 2. Modify `ship_to_langfuse()` to upsert OTEL traces

Instead of always creating a new trace with `_make_trace_id(session_id)`:

1. **Search** for an existing trace by `sessionId` via `find_otel_trace()`
2. **If found** (OTEL trace exists): send `trace-create` upsert with the OTEL trace's `id` — this merges tags, sets userId, input/output, metadata. **Skip** creating the root span and generation observations (OTEL already has those with better timing data).
3. **If not found** (OTEL didn't fire): fall back to current behavior — create full trace + span + generations using the deterministic `_make_trace_id()`.

The upsert batch for an existing OTEL trace is minimal:
```python
batch = [{
    "id": str(uuid.uuid4()),
    "type": "trace-create",
    "timestamp": start_ts,
    "body": {
        "id": otel_trace_id,  # existing OTEL trace ID
        "name": f"claude-code: {project}",
        "userId": "alex",
        "tags": ["claude-code", project, f"branch:{git_branch}"],
        "input": first_message[:3000],
        "output": last_message[:3000],
        "metadata": {
            "source": "claude-code",
            "project": project,
            "cwd": session["cwd"],
            "model": session["model"],
            "git_branch": session["git_branch"],
            "file": session["file"],
            "total_generations": len(session["generations"]),
            "total_messages": len(session["messages"]),
            "total_input_tokens": session["total_input_tokens"],
            "total_output_tokens": session["total_output_tokens"],
        },
    },
}]
```

### 3. Add `--backfill` CLI mode

The script already supports being called with `session_file` on stdin (hook mode). Add a CLI mode:

```bash
python session-to-langfuse.py --backfill           # all JSONL files
python session-to-langfuse.py --backfill <file>     # specific file
```

This reuses `parse_session()` + the updated `ship_to_langfuse()` with upsert logic. For each file:
- Parse session
- Search for OTEL trace → upsert if found, create if not
- Log result

The `sm.py` `session deposit` / `session deposit-all` commands already call this script via subprocess, so they get the new behavior for free.

### 4. No changes to the collector or OTEL config

The collector stays as-is. Tags and environment come from the hook enrichment, not OTEL attributes.

## Existing Code to Reuse

- `parse_session()` — already handles both Claude Code and OpenClaw JSONL formats
- `_make_trace_id()` — deterministic trace ID for fallback (no OTEL trace exists)
- `find_session_file()` — finds JSONL by session ID across `~/.claude/projects/`
- Auth pattern: `base64(LANGFUSE_PUBLIC_KEY:LANGFUSE_SECRET_KEY)` in headers
- `sm.py:ingest_trace_update()` (line 83) — reference implementation of trace upsert

## Verification

1. Run a Claude Code session → check Langfuse for a single enriched trace (not duplicates)
2. Trace should have: tags, userId, input/output, AND token usage from OTEL
3. Run `python session-to-langfuse.py --backfill` on a few old JSONLs → verify traces created or upserted
4. Kill a session without clean exit → verify OTEL trace exists (bare) without hook enrichment
