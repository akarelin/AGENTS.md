# Track 3 — Preservator → SessionSkills Pipeline

**Owner scope:** turn the raw multi-host data collected by Preservator into a live input source for SessionSkills, so every LLM session on every host — not just the Mac's — flows through ingest/merge/name/analyze/memorize.

## Context

**Preservator** (`~/CRAP/preservator/` — see [README.md](../../../../CRAP/preservator/README.md)) is Alex's cross-host raw-archival tool. It:

1. Runs on a W11 controller (`alex-pc` or `alex-laptop`, native or WSL).
2. Pulls LLM session dirs (`.claude`, `.codex`, `.gemini`, `.openclaw`, etc.) from every configured workstation via SSH / SMB / local.
3. Stages to `/var/tmp/prsvtr-staging`, compresses to RAR with `processors/rar.yaml` config, delivers to SD.Lake + optionally Azure.
4. Output: `{sd.lake}/prsvtr.by_hst/{hostname}/{YYYYMMDD}/prsvtr_{host}_{timestamp}.rar` — one RAR per host per day.

**SessionSkills** (this repo) runs on the Mac and ingests LLM sessions **only from the local filesystem** — `~/.claude/projects/` and `~/.openclaw/agents/`. Sessions from Alex-PC, Alex-Surface, kolme, or any Windows/Linux workstation are **invisible to the pipeline**. They exist only as RARs in SD.Lake.

This is a missed opportunity. If Alex runs Claude Code on Alex-PC, the session JSONL is on Alex-PC's disk → eventually gets RAR'd to SD.Lake → sits there, unread. SessionSkills' rich pipeline (classify, memorize into agent memory, heatmap, project linking) never sees it.

## Goal

Treat each host's preservator output as a **source for SessionSkills ingest**. Sessions from any host get canonical records, deterministic IDs, consistent pipeline processing. After Track 3 lands, `sm-tui` can show sessions from every host Alex works on.

## Current state

- Preservator works and runs (ad-hoc; no scheduled invocation on the Mac — it's controller-driven from W11 side).
- SessionSkills knows nothing about RARs or multi-host. `sessionskills.yaml` sources are local-fs only.
- The canonical storage pattern `prsvtr.by_hst/{hostname}/{date}/prsvtr_{host}_{ts}.rar` is stable and documented.
- Preservator's `llms.yaml` source definition already captures the right patterns (`.claude`, `.openclaw`, `.codex`, etc. — see `/Users/alex/CRAP/_config/sources/llms.yaml`).

## Work items

### 3.1 — SessionSkills can read preservator RARs

- **New file:** `/Users/alex/A/SessionManager/sessions/stages/ingest_preservator.py`
- Input: config block `sources[name='preservator']` pointing at `sd.lake` root.
- Walk `<sd.lake>/prsvtr.by_hst/*/{YYYYMMDD}/*.rar`. For each:
  - Extract hostname from path segment.
  - Peek inside the RAR (use `rar lb` or `unrar l` to list members) and only open members matching known LLM patterns (`.claude/projects/*/*.jsonl`, `.openclaw/agents/*/sessions/*.jsonl`, `.codex/sessions/*/*.jsonl`).
  - For each member, stream-extract into a **content-addressed cache** under `~/.sessionskills/preservator-cache/{hash}/{relative-path}` (one copy per unique sha256, symlinked from per-host-dated dirs).
  - Build a `SessionRecord` exactly as ingest does today, but with extra fields:
    - `origin_host: "alex-pc"` (new top-level field on `SessionRecord`)
    - `paths.preservator_rar: <rar-path>`
    - `paths.raw_jsonl: <path-in-cache>` — downstream stages (name/analyze/memorize) work unchanged.
  - Key by `(source, source_id)` as always — but source_id for a cross-host session needs a host prefix to avoid collision. Proposal: `source_id = f"{hostname}:{uuid}"` for any non-local host; leave local as bare UUID for backward-compat. (Alternative: overload `source` to be `claude-code@alex-pc` — rejected: breaks per-source pipeline config keys.)

### 3.2 — Config additions

Extend `sessionskills.yaml`:

```yaml
sources:
  # ...existing sources...
  - name: preservator
    kind: rar
    root: /Volumes/S1/SD.Lake/prsvtr.by_hst    # or /Users/alex/SD.Lake/... if local
    inner_patterns:
      - ".claude/projects/*/*.jsonl"
      - ".openclaw/agents/*/sessions/*.jsonl"
      - ".codex/sessions/*/*.jsonl"
    include_hosts: []          # empty = all hosts; else whitelist: [alex-pc, alex-surface]
    exclude_hosts: [alex-mac]  # don't re-ingest our own local sessions through the RAR path
    cache_dir: ~/.sessionskills/preservator-cache
    age_limit_days: 365        # ignore RARs older than this
```

### 3.3 — Host-aware dedup

A session may be produced on Alex-PC, RAR'd every day by preservator, and delivered to SD.Lake multiple times (each day's RAR contains the session, growing). We need to ingest it **once** and keep `paths.preservator_rar` pointing at the newest RAR that contains it.

- Use `content_hash` (already on every record) as the primary dedup. Two RAR members with the same sha256 = same session; upsert the one record, append the newer RAR path to `paths.preservator_rar_history[]`.

### 3.4 — Claude-Code-slug translation across hosts

A Claude Code session on Alex-PC has slug like `-C--Users-Alex-RAN-AI` (Windows-ish encoding of `C:\Users\Alex\RAN\AI`). Track 2's canonical project registry needs entries recognizing these cross-host slugs as the same project.

- Track 3 contributes: when ingesting a cross-host Claude Code session, emit a hint to Track 2's unlinked-project review queue:
  ```json
  {
    "kind": "host_slug_alias",
    "host": "alex-pc",
    "slug": "-C--Users-Alex-RAN-AI",
    "suggested_project": "sessionskills",
    "evidence": "matching slug pattern on alex-mac"
  }
  ```
  Reviewer accepts → adds the alex-pc slug to the project's `claude_code_slugs` in the registry.

### 3.5 — Scheduling / automation

Preservator runs from W11 controller; SessionSkills runs on Mac. The handshake:

- W11 controller runs preservator (manual or scheduled); new RAR lands in SD.Lake.
- SD.Lake is a Synology share — already auto-mounts on the Mac.
- **New launchd plist** `/Users/alex/A/SessionManager/launchd/ai.sessionskills.preservator-ingest.plist`:
  - Runs `sm-pipeline run ingest --source preservator` every 6 hours.
  - StandardOutPath `~/Library/Logs/sessionskills-preservator.log`.

### 3.6 — Reverse path: push Mac's live sessions back to preservator's archive

A nice-to-have symmetry. Mac sessions are live in `~/.claude/` / `~/.openclaw/` but **not archived** (they live on the Mac only, with Synology SD sync as the only cross-machine safety). Preservator's `llms.yaml` source matches these patterns, but preservator never runs on the Mac (it's W11-controller-driven).

Two options:
- **(a)** Ask preservator to add an SSH transport reaching back from W11 to Alex-Mac. Requires sshd on Mac (already enabled — we ssh'd earlier). Adds alex-mac to `workstations.yaml`.
- **(b)** SessionSkills' `archive` stage already writes tar.gz to `~/Archives/sessions/`. Extend it to also deliver to the same `{sd.lake}/prsvtr.by_hst/alex-mac/...` path preservator uses. Then one tool doesn't have to reach across machines.

Pick (a): single source of truth for collection; preservator already understands the schema. SessionSkills just reads; doesn't write to the archive tree.

## Files in scope

**New:**
- `/Users/alex/A/SessionManager/sessions/stages/ingest_preservator.py`
- `/Users/alex/A/SessionManager/launchd/ai.sessionskills.preservator-ingest.plist`
- (Track 2 coordination) A small hook in Track 2's `unlinked_project` review handler for `host_slug_alias` items.

**Modified:**
- `/Users/alex/A/SessionManager/sessionskills.yaml` (preservator source block)
- `/Users/alex/A/SessionManager/sessions/record.py` (new field `origin_host: str | None = None`, defaults to `'alex-mac'` for local records via a helper on load)
- `/Users/alex/A/SessionManager/sessions/stages/ingest.py` (when ingesting from local fs, set `origin_host='alex-mac'`)
- `/Users/alex/A/SessionManager/scripts/sm-tui.py` — add `origin_host` column (with a small flag emoji: 🍎 mac, 🪟 windows, 🐧 linux)

**Reference / external (do not modify from this track):**
- `/Users/alex/CRAP/preservator/README.md`
- `/Users/alex/CRAP/preservator/REQUIREMENTS.md`
- `/Users/alex/CRAP/_config/sources/llms.yaml`
- `/Users/alex/CRAP/_config/workstations.yaml`

## Verification

```bash
# 1. List RARs visible from the Mac
find /Volumes/S1/SD.Lake/prsvtr.by_hst -name "*.rar" 2>/dev/null | head
# (or wherever sd.lake resolves on this Mac)

# 2. Ingest one host's worth of RARs
sm-pipeline run ingest --source preservator --dry-run
sm-pipeline run ingest --source preservator

# 3. Cross-host records in the store
sqlite3 ~/.sessionskills/store.sqlite \
  "SELECT json_extract(json,'$.origin_host') AS host, COUNT(*)
   FROM records GROUP BY host"
# Expect rows for alex-mac (preexisting), alex-pc, alex-surface, kolme — whatever hosts are archived.

# 4. Fresh Alex-PC Claude Code session reaches ingest within a day
# - On alex-pc: open claude, do something, exit.
# - Preservator runs on W11 controller (daily).
# - Next day: `sm-pipeline run ingest --source preservator` picks it up.
# - `sm-tui` → Local view shows the Alex-PC session with 🪟 flag + full metadata.

# 5. Cross-host dedup
# - The same session appears in two consecutive daily RARs (growing content).
# - After two ingests, `SELECT COUNT(*) FROM records WHERE source_id LIKE 'alex-pc:<uuid>'` = 1.
# - `paths.preservator_rar_history` has both RAR paths.
```

## Dependencies

- **Track 1** defines the `SessionRecord` schema — Track 3 adds a field (`origin_host`) but doesn't change the state machine.
- **Track 2** canonical project registry benefits when Track 3 adds cross-host slug entries — the `host_slug_alias` review item closes the loop.
- **Preservator itself** needs no changes for Track 3 to work — we're adding a *reader*, not altering archival. If Track 3.6 (reverse: archive Mac sessions) is pursued, preservator's `workstations.yaml` adds alex-mac; no code changes required.

## Out of scope

- Decompressing full RARs to disk permanently. We extract selected members on demand into a content-addressed cache that can be garbage-collected.
- Supporting every preservator source (browsers, shell, TickTick). Track 3 is specifically the **LLM-session subset** — `.claude`, `.openclaw`, `.codex`.
- Cross-host _real-time_ session sync. Preservator is daily-ish. For faster sync, use Synology Drive on each host (already the case for `SD.agents/` and partially for `.claude/`).
- Rewriting preservator. It works; it's not our code; don't touch its engine/.

## Cross-references

- The preservator RAR output pattern and `sd.lake` resolution rules: [preservator/README.md](../../../../CRAP/preservator/README.md) §Output + §Transport selection.
- Work-atom classification flow (same data, different consumer): Track 2.7.
- For the reverse — SessionSkills' own `archive` stage writing tar.gz to `~/Archives/sessions/`: see `sessions/stages/archive.py` (local-only today; Track 3.6 would extend).
