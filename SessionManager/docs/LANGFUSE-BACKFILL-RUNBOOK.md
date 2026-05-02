# Langfuse Backfill Runbook

Bulk-ingest Claude Code + OpenClaw session JSONLs into Langfuse with full
metadata, tags, per-turn generations, model, usage, and computed cost.

**Run this from the host that hosts Langfuse** (`langfuse.karelin.ai`)
to avoid round-tripping ~8k POSTs across the public network. The script
posts to `https://langfuse.karelin.ai/api/public/ingestion`; running it
locally on that host turns each POST into a localhost call.

The SessionEnd hook handles new sessions live. This runbook is for
historical sessions that predate the hook (or that took the upsert
fast-path with sparse trace fields).

## Prerequisites

1. **Python 3.11+** (uses `from __future__` and `|` union syntax).
2. **Session JSONLs accessible on this host.** They live in:
   - `~/.claude/projects/**/*.jsonl` (Claude Code, including remote agent / sub-agent JSONLs)
   - `~/.openclaw/agents/*/sessions/*.jsonl` (OpenClaw agents)
   If the data lives on another machine, sync it first (rsync,
   syncthing, NFS — your choice). The script does not pull data over
   the network.
3. **Langfuse keys.** The script defaults to the values baked into
   `scripts/session-to-langfuse.py`; override via env vars if you're
   targeting a different workspace:
   ```bash
   export LANGFUSE_HOST=https://langfuse.karelin.ai
   export LANGFUSE_PUBLIC_KEY=pk-lf-...
   export LANGFUSE_SECRET_KEY=sk-lf-...
   ```
4. **Reachability.** From this host:
   ```bash
   curl -sS -o /dev/null -w "%{http_code}\n" "$LANGFUSE_HOST/api/public/health"
   ```
   Expect `200`.

## What the backfill does

For every JSONL it finds, the script:

1. Parses the session (handles both Claude Code and chmo formats).
2. Builds a Langfuse trace with deterministic IDs derived from
   `sessionId` — running this twice deposits the same rows, no
   duplicates.
3. Emits `trace-create + span-create + N generation-create` events
   per session, chunked into POSTs ≤ 3 MB / ≤ 100 events to stay under
   Langfuse's payload limit.

Trace ID = `sha256(session_id)[:32]`.
Observation IDs = `sha256(f"{session_id}:{kind}:{index}")[:32]`.

Sessions with zero assistant turns are skipped (logged as "no
generations found").

## Run

```bash
cd ~/A/SessionManager      # adjust if the repo lives elsewhere
PYTHONUNBUFFERED=1 nohup python3 scripts/session-to-langfuse.py \
  --backfill --force-full \
  > /tmp/langfuse-backfill.log 2>&1 &
echo "pid: $!"
```

Flags:

- `--backfill` — scan both session dirs and process every JSONL.
- `--force-full` — required. Bypasses the OTEL-trace upsert path
  (which silently drops trace-level fields on Langfuse OTEL-ingested
  traces) and writes fresh traces with the deterministic ID. Without
  this flag, backfill enriches OTEL traces' metadata only and
  generation rows are left empty.
- `--since YYYY-MM-DD` (optional) — process only sessions starting on
  or after this date. Useful for incremental top-ups.
- `--project <substring>` (optional) — filter by path substring,
  e.g. `--project alex` to limit to the chmo "alex" agent.
- `<file.jsonl>` (positional, optional) — process a single file
  instead of scanning. Same idempotency rules apply.

`PYTHONUNBUFFERED=1` matters: without it the log buffers and you can't
tell if the run is making progress vs. stuck.

## Monitor

```bash
tail -f /tmp/langfuse-backfill.log
```

Quick counters:

```bash
echo "deposited: $(grep -c 'deposited:' /tmp/langfuse-backfill.log)"
echo "skipped:   $(grep -c 'skipped'    /tmp/langfuse-backfill.log)"
echo "failed:    $(grep -c 'FAILED:'    /tmp/langfuse-backfill.log)"
```

Throughput on a healthy run with co-located Langfuse: ~1.5–3 sessions
per second. ~8,000 sessions ≈ 50–90 minutes.

If the rate is much slower (< 0.3/s) the most likely cause is a stuck
HTTPS request — see [Stalls](#stalls-ssl-read) below.

## Stop / Resume

Stop:

```bash
kill <pid>
```

Resume: re-run the same command. Because trace and observation IDs are
deterministic, every session that already landed will simply upsert
(no duplicates). Sessions that hadn't started yet are processed
fresh. There is no checkpoint file — the deterministic IDs make one
unnecessary.

## Verify

Query Langfuse for a known sessionId and confirm trace + observations
are populated:

```bash
SID="<some-session-id>"
TID=$(python3 -c "import hashlib; print(hashlib.sha256('$SID'.encode()).hexdigest()[:32])")

curl -sS -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/traces/$TID" \
  | python3 -c "
import json, sys
t = json.load(sys.stdin)
print('name:        ', t.get('name'))
print('userId:      ', t.get('userId'))
print('sessionId:   ', t.get('sessionId'))
print('totalCost:   ', t.get('totalCost'))
print('latency:     ', t.get('latency'))
obs = t.get('observations') or []
gens = [o for o in obs if o.get('type') == 'GENERATION']
print(f'observations: {len(obs)} total, {len(gens)} generations')
if gens:
    g = gens[0]
    print(f'  sample: model={g[\"model\"]} usage={g[\"usage\"]} cost={g.get(\"calculatedTotalCost\")}')
"
```

Expected output for a populated trace:

- `name`: `"claude-code: <project>"` or `"chmo: <agent>"`
- `userId`: `"alex"`
- `totalCost`: > 0 (provided pricing exists for the model — see
  [Cost notes](#cost-notes))
- `observations`: > 0 with a non-zero generation count

## Troubleshooting

### Stalls (SSL read)

If progress freezes for a few minutes with no log output, the script
is stuck waiting on a Langfuse response. Confirm with:

```bash
sample <pid> 1 2>/dev/null | grep -A1 SSLSocket_read
```

If you see `_ssl__SSLSocket_read` in the stack: kill and restart. The
script's POST timeout is 60s, but a slow-streaming response from
Langfuse can hold the connection past that. On retry, deterministic
IDs make this safe — the partially-shipped session just upserts.

### HTTP 413 (Request Entity Too Large)

Should not happen — `_send_batch` chunks payloads under 3 MB and 100
events. If it does, your Langfuse instance has a stricter limit.
Lower `_INGEST_MAX_BYTES` in the script (top of the function) and
re-run.

### `No generations found in session. Skipping.`

The JSONL has no assistant turns (e.g., user typed and immediately
quit). The skip is correct. The session contributes nothing to ingest.

### `Falling back to most recent JSONL`

Only seen in hook mode (live SessionEnd), not backfill. Indicates the
hook couldn't resolve the session_id from stdin to a JSONL path; it
takes the most recently modified file as a guess. In backfill mode
the script iterates files directly, so this branch never fires.

## Cost notes

Langfuse computes per-generation cost from a model→price registry
keyed on `modelName`. Verified entries already in
`langfuse.karelin.ai`:

| Model                    | Input $/Mtok | Output $/Mtok |
|--------------------------|--------------|---------------|
| `claude-opus-4-7`        | 5            | 25            |
| `claude-sonnet-4-6`      | 3            | 15            |
| `claude-haiku-4-5`       | 0.80         | 4             |

These are flat prices. Cache tokens (`cache_read_input_tokens`,
`cache_creation_input_tokens`) are sent on each generation as
auxiliary fields, but Langfuse does not multiply them — pricing
covers only base input/output.

Anthropic's actual cache pricing:

- `cache_read_input_tokens` — 0.1× input price
- `cache_creation` 5m TTL — 1.25× input price
- `cache_creation` 1h TTL — 2× input price

For sessions that lean heavily on cache (long-running agents),
Langfuse's reported cost will undercount real billed cost. The error
is bounded — typically 5–15% of total session cost. To close the gap
you'd need to add cache pricing to the Langfuse model entries and
patch the hook to send `usageDetails` with separate categories.
Out of scope for this runbook.

## Re-running for new dates only

After the initial backfill, top up with:

```bash
PYTHONUNBUFFERED=1 python3 scripts/session-to-langfuse.py \
  --backfill --force-full --since 2026-05-01
```

The live SessionEnd hook also continues to fire on session exits, so
re-running is only needed if the hook didn't run (e.g., crashes,
remote sessions on a host without the hook installed).

## File layout reference

```
SessionManager/
├── scripts/
│   ├── session-to-langfuse.py    # the script invoked here
│   └── PLAN-langfuse-upsert-backfill.md  # original design doc
└── docs/
    └── LANGFUSE-BACKFILL-RUNBOOK.md  # this file
```
