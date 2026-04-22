# Track 1 — Sessions & Langfuse

**Owner scope:** everything that concerns a session's own lifecycle + its mirror in Langfuse. No cross-track knowledge required.

## Context

Every LLM client on every host produces a session JSONL. Claude Code writes to `~/.claude/projects/<slug>/*.jsonl`. OpenClaw writes to `~/.openclaw/agents/<agent>/sessions/*.jsonl`. A self-hosted Langfuse at `https://langfuse.karelin.ai` receives:

- **OTEL push** live from both Claude Code and OpenClaw (already wired; produces minimal traces with token/span telemetry).
- **Deposit push** via the `SessionEnd` hook `~/.claude/hooks/session-to-langfuse.py` which parses the final JSONL, enriches the OTEL trace with input/output/tags, or creates a new trace if no OTEL trace exists.

SessionSkills treats Langfuse as a canonical remote mirror. The pipeline reads sessions from local disk, orchestrates ingest/merge/name/analyze/etc., and the `sm` / `sm-tui` CLI exposes Langfuse (remote) + local state in one UI.

## Current state

- 3198 records in `~/.sessionskills/store.sqlite`.
- 3017 Langfuse traces already (from the SessionEnd hook running historically).
- `session-to-langfuse.py` has **deterministic trace + observation IDs** → `sm deposit-all` is now fully idempotent (re-deposits upsert; no duplicate per-turn observations).
- `sm-tui` has: emoji src badges, age/size tint, 90-day activity heatmap, substring filter, column sort, description column (via sessions-named symlink slug), right-pane preview with first-prompt + analyzed summary, `R` key for cache-bypass refresh, gppu.data.Cache-backed API calls (~1700× speedup on warm hits).

## Work items (not yet done)

### 1.1 — Bulk backfill the last ~155 undeposited local sessions

- 3172 local sessions exist; 3017 remote; ≈155 deposit gap.
- Idempotent now (the generation-ID patch). Run `sm deposit-all` (or `D` in sm-tui). ~20-40 min wall time.
- Verify: `curl -u $LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY https://langfuse.karelin.ai/api/public/traces?limit=1 | jq '.meta.totalItems'` ≥ 3172 after.
- **Touch:** no code — just run. Post-run verification optional.

### 1.2 — Langfuse API pull (read path)

Currently we only push to Langfuse. The `ingest` stage has a `langfuse` source kind with `enabled: false` in `sessionskills.yaml`. Implement:
- A tiny pull that reads `GET /api/public/traces?fromTimestamp=<since>&page=<n>` paginated.
- Map each trace to a `SessionRecord` with `source='langfuse'`, `source_id=<trace-id>`.
- Dedupe against existing records that already have `paths.langfuse_trace_id` set.
- **Touch:** `sessions/stages/ingest.py` (new ~40 lines for the `api` kind).

### 1.3 — Server-side filter for the TUI remote view

Currently `/` filter applies client-side over the loaded 1000 traces (of 3017). Pass the filter as `&name=<needle>` to the Langfuse list endpoint so filtering searches the full corpus.

- **Touch:** `scripts/sm-tui.py` — in the filter-set path, when `self._view == 'remote'`, re-invoke `_load_all` with the filter as an API param.

### 1.4 — Better sort UX

`s` currently only toggles direction. Upgrade to cycle columns: `s` advances sort column left-to-right; `S` (capital) reverses direction. Show `▲`/`▼` glyph next to the active column header.

- **Touch:** `scripts/sm-tui.py` — `action_cycle_sort`, rewrite column render to inject the arrow glyph.

### 1.5 — Deposit progress in TUI

`D` (Deposit All) currently writes per-session lines to the right pane. Improve with a visual progress bar (Textual ProgressBar widget) + a rolling ETA.

- **Touch:** `scripts/sm-tui.py` — `_do_deposit_all()`.

### 1.6 — Token-budget telemetry for the pipeline's Ollama calls

Qwen3 token usage isn't surfaced anywhere today. Useful for cost attribution and sizing. Ollama's `/api/generate` returns `prompt_eval_count` + `eval_count`. Capture per-stage, roll up to `sm-pipeline stats`.

- **Touch:** `sessions/llm.py` + each stage wrapper to persist counts on the record.

### 1.7 — Cross-session resume chain detection

A user may "continue" a conversation in a new Claude Code session. Today these are separate records. Langfuse already groups via `sessionId`. Extend SessionSkills' merge to detect resume-chains:
- Two consecutive Claude Code sessions in the same project dir, started within N minutes of each other, where one starts with "Continue" or "Resume" → attach a `session_group = f"cc:resume-chain:{first_uuid}"`.
- v1 merge handles `-topic-<ts>` and `.reset.*` already; this extends the same vocabulary.

- **Touch:** `sessions/stages/merge.py` — add resume-chain detection after the existing checks.

## Files in scope

**Primary:**
- `/Users/alex/A/SessionManager/scripts/sm-tui.py`
- `/Users/alex/A/SessionManager/scripts/session-to-langfuse.py` (idempotent; patched 2026-04-21)
- `/Users/alex/A/SessionManager/scripts/sm.py` (legacy `lf`-style CLI; touch only for bugfix)
- `/Users/alex/A/SessionManager/sessions/stages/ingest.py`
- `/Users/alex/A/SessionManager/sessions/stages/merge.py`
- `/Users/alex/A/SessionManager/sessions/llm.py`

**Reference:**
- `/Users/alex/A/SessionManager/docs/sessionskills-ADR.md` — architecture decisions.
- Langfuse API docs — use `/api/public/traces` endpoints throughout.

## Verification

- `sm-pipeline doctor` — all green.
- After 1.1: `sm-tui` → `4` (Stats) → remote total matches local total ±5.
- After 1.2: `sqlite3 ~/.sessionskills/store.sqlite "SELECT COUNT(*) FROM records WHERE source='langfuse'"` > 0.
- After 1.3: `/` filter in remote view returns results from traces not on page 1.
- After 1.4: `sm-tui` → press `s` several times → column header glyph moves.
- After 1.7: orphan + live `.reset` chains AND cross-session resumes both have `session_group` populated.

## Out of scope for this track

- Project semantics → Track 2.
- Cross-host data collection → Track 3.
- LLM model changes (Qwen3 → something else) — defer; the pipeline is model-agnostic.
