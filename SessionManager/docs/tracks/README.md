# SessionSkills — Parallel Work Tracks

Three independent tracks, each ownable by a different agent/person in parallel. Each track has its own goals, files to touch, and verification path. Shared infrastructure is called out at the bottom.

| # | Track | File | Primary Domain | Dependencies |
|---|------|------|----------------|--------------|
| 1 | Sessions & Langfuse | [`track-1-sessions-langfuse.md`](track-1-sessions-langfuse.md) | Trace deposit, upsert idempotence, TUI, cache, OTEL | None (self-contained) |
| 2 | Projects ↔ Sessions linking | [`track-2-projects-sessions.md`](track-2-projects-sessions.md) | Canonical project registry; bidirectional links across Claude Code / OpenClaw / work-atoms / Obsidian / Langfuse. Also ships a shared skill `SD.agents/skills/projects-sessions/` usable by both chmo and Claude Code. | Reads from Track 1's schema; writes new columns |
| 3 | Preservator → SessionSkills | [`track-3-preservator-pipeline.md`](track-3-preservator-pipeline.md) | Cross-host data collection (RAR archives on SD.Lake) → SessionSkills ingest | Extends Track 1's `ingest` stage; shares storage paths |

## Where SessionSkills is today (as of 2026-04-21 late afternoon)

- **Code:** `/Users/alex/A/SessionManager/` (canonical); mirrored to `/Users/alex/RAN/AI/SessionManager/` for the active venv. See also `sessionskills-ADR.md` one level up.
- **Store:** `~/.sessionskills/store.sqlite` — 3198 records (3160 live Claude Code / OpenClaw + 31 orphans + 2 analyzed + 1 memorized + 4 freshly ingested).
- **Obsidian project page:** `/Users/alex/_/Projects/SessionSkills.md`.
- **CLI:** `sm` / `sm-app` / `sm-tui` / `sm-local` / `sm-map` / `sm-import` (legacy Langfuse CLI) + `sm-pipeline` / `sm-review` (SessionSkills orchestrator).
- **Completed items:** ingest + merge + name (LLM-slugged for 3160 sessions) + analyze + write_to_memory + cluster + classify + prune + archive + review + launchd plists + symlink-hardening guard + migrate-skills + orphan ingest + gppu cache + TUI (emoji, tint, heatmap, filter, sort, descriptions, right-pane preview).
- **Open:** Task #15 (vault-skills mv), Task #17 (ref sweep), Task #24 (broader config extraction).

## Shared infrastructure (all tracks depend on)

- **Canonical `SessionRecord`** in `sessions/record.py` — `(source, source_id)` PK, state machine with 13 states, JSON flex fields.
- **SQLite store** in `sessions/store.py` — idempotent upsert by `(source, source_id)`.
- **Local LLM** via Ollama at `127.0.0.1:11434` — `qwen3:8b` chat, `nomic-embed-text` embed. Fallback chain: Local → CloudLLM → heuristic.
- **Config** via `sessionskills.yaml` + env-var + (new) `sessions.yaml` `sm_tui:` block. Task #24 unifies.
- **`sm-pipeline` orchestrator** in `sessions/orchestrator.py` — subcommands `doctor`, `stats`, `run <stage>`, `migrate-skills`.

## Running the tracks in parallel

Because each track writes to different files and different record fields, concurrent execution is safe. Contention points:

- **All three** append to `sessions/record.py`'s `classification` dict. Field names prefixed by track (`track2_canonical_project`, `track3_origin_host`) keep them separate.
- **Tracks 1 and 3** both touch `sessions/stages/ingest.py`. Recommend Track 1 to land first (or Track 3 to subclass/wrap the extractor).
- **Tracks 2 and 3** both care about `project` values. Track 2 defines the canonical registry; Track 3 populates it per source.

## Verification of the whole picture (end-to-end)

After all three land, this command shows a session with **complete lineage**:

```bash
sqlite3 ~/.sessionskills/store.sqlite <<'SQL'
SELECT
  source, substr(source_id,1,12),
  json_extract(json,'$.classification.topic_slug')          AS name,
  json_extract(json,'$.classification.work_atom_project')   AS work_atom,
  json_extract(json,'$.classification.canonical_project')   AS canonical_proj,
  json_extract(json,'$.paths.langfuse_trace_id')            AS lf_trace,
  json_extract(json,'$.paths.analyzed_md')                  AS analyzed,
  json_extract(json,'$.origin_host')                        AS host,
  json_extract(json,'$.paths.preservator_rar')              AS archive
FROM records
WHERE state = 'classified'
LIMIT 3;
SQL
```

Every column populated = all three tracks are integrated.
