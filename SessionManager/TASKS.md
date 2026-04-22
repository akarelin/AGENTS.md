---
title: SessionManager / SessionSkills Task Tree
kind: project-hierarchy
interim_location: true
target_location: ~/_/KG/Project/_registry.yaml
updated: 2026-04-21
---

# SessionManager — Task Tree

Interim home for the project hierarchy until Track 2 lands the canonical registry at `~/_/KG/Project/_registry.yaml` (see `docs/tracks/track-2-projects-sessions.md` §2.1 + §2.8).

Same schema; just parked here for now so it's alongside the code it describes.

## `SessionManager` (umbrella project)

### Phase 1 — Legacy SessionManager CLI + Langfuse hook

- **Status:** done (pre-existing; baseline we started from)
- **Delivered:** `sm`, `sm-app`, `sm-tui`, `sm-import`, `sm-local`, `sm-map`; `session-to-langfuse.py` SessionEnd hook; Langfuse self-hosted at langfuse.karelin.ai; discovery_rules.yaml.
- **Sessions:** not specifically attributed (historical work before this project hierarchy existed).

### Phase 2 — SessionSkills orchestrator build ✅

- **Status:** **COMPLETED 2026-04-21**
- **Session:** `f56a50a4-3dd9-49d9-a907-8ec1ee14859b` · title: `session-skills`
- **Session file:** `/Users/alex/SD/.claude/projects/-Users-alex-RAN-AI/f56a50a4-3dd9-49d9-a907-8ec1ee14859b.jsonl`
- **Host:** alex-mac
- **Delivered:**
  - `sessions/` package — `record.py`, `store.py`, `llm.py`, `config.py`, `orchestrator.py`, `skill_paths.py`, `migrate_skills.py`, `review_tui.py`
  - 10 pipeline stages — ingest, merge, name, analyze, write_to_memory, cluster, classify, prune, archive, review
  - Ollama local LLM integration (Qwen3-8B + nomic-embed-text), with Cloud + heuristic fallback
  - `sm-pipeline` CLI + `sm-review` TUI + 5 launchd plists
  - `sm-pipeline migrate-skills` one-button vault-skill migration
  - v2 merge orphan ingest (`.jsonl.reset.*` / `.jsonl.deleted.*` snapshots — 31 records recovered)
  - Symlink guard (`~/.claude/projects` Synology Drive hardening) with SessionStart hook
  - Deterministic Langfuse trace + observation IDs → `sm deposit-all` fully idempotent
  - Cross-host SSH path (`/Users/alex/RAN/AI/SessionManager/bin/_bootstrap.sh` + `.zshenv` PATH extension)
  - `sm-tui` rich enhancements — 🤖🦀 emoji badges, age/size tint, 90-day activity heatmap, substring filter (`/`), column sort (`s`), description column via LLM-slugged symlinks, right-pane preview (first-prompt + analyzed summary), gppu.data.Cache-backed API (~1700× speedup), `R` force-refresh
  - wiki-raw-sources RAR archival (702 files, 6.8 MB compressed) out of git into vault cold storage
  - Alex-PC/Surface skill-consolidation completed remotely via Obsidian-tracked task
- **Task-tracker ref:** #26 (completed)

### Phase 3 — Parallel tracks 🚧

- **Status:** in_progress · parallel = true
- **Blocked by:** Phase 2 (done)
- **Specs:** `/Users/alex/A/SessionManager/docs/tracks/`
- **Task-tracker ref:** #27 (parent)
- **Spawn script:** `/Users/alex/A/SessionManager/bin/spawn-tracks.sh` — ready (prompts under `docs/tracks/spawn/`). Not yet executed; run on the Mac to fire all three.

#### Track 1 — Sessions & Langfuse

- **Doc:** [`docs/tracks/track-1-sessions-langfuse.md`](docs/tracks/track-1-sessions-langfuse.md)
- **Scope:** 7 work items — bulk backfill, Langfuse API pull, server-side filter, sort UX, deposit progress, token telemetry, resume-chain detection
- **Spawned session:** `<tbd>` (will be populated when spawn one-liner runs; title target: `track-1-sessions-langfuse`)
- **Task-tracker ref:** #28 (blocked by #27)

#### Track 2 — Projects ↔ Sessions linking

- **Doc:** [`docs/tracks/track-2-projects-sessions.md`](docs/tracks/track-2-projects-sessions.md)
- **Scope:** 9 work items — canonical project registry, resolver lib, `link_project` stage, bidirectional Obsidian views, unlinked review flow, TUI Projects upgrade, work-atoms integration, **project task hierarchy (§2.8)**, **shared skill at `SD.agents/skills/projects-sessions/` usable by chmo + Claude Code (§2.9)**
- **Spawned session:** `<tbd>` (title target: `track-2-projects-sessions`)
- **Task-tracker ref:** #29 (blocked by #27)

#### Track 3 — Preservator → SessionSkills pipeline

- **Doc:** [`docs/tracks/track-3-preservator-pipeline.md`](docs/tracks/track-3-preservator-pipeline.md)
- **Refs:** `/Users/alex/CRAP/preservator/README.md`, `/Users/alex/CRAP/_config/sources/llms.yaml`
- **Scope:** 6 work items — RAR reader, host-aware dedup, config additions, slug-alias hints for Track 2, launchd schedule, reverse-archival path (optional)
- **Spawned session:** `<tbd>` (title target: `track-3-preservator-pipeline`)
- **Task-tracker ref:** #30 (blocked by #27)

---

## How to maintain this file

- When a track's spawn one-liner is run, update that track's `spawned session` line with the session UUID (find via `ls -lt ~/.claude/projects/-Users-alex-A-SessionManager/*.jsonl | head -1` after the session is active for a minute).
- When a track completes, change its **Status** line and add a `completed_at:` date.
- When Track 2's §2.1 lands the canonical registry, migrate this content to `~/_/KG/Project/_registry.yaml` and reduce this file to a one-line pointer.
- Prefer editing here over the external task-tracker for day-to-day project state — external tasks are in-session only; this file persists across sessions.
