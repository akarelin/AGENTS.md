# Tasks

Markdown-tracked work for SessionManager + SessionSkills. Flat list with
nested checkboxes — parent task first, subtasks indented below. Closed
items keep their completion date so the history is auditable.

## SessionManager (meta project)

- [ ] **Phase 3 — Parallel tracks** (in_progress; blocked_by Phase 2)
  - [ ] Track 1 — Sessions & Langfuse · spec [`docs/tracks/track-1-sessions-langfuse.md`](docs/tracks/track-1-sessions-langfuse.md)
    - Spawned session: `<tbd>` · title target: `track-1-sessions-langfuse`
    - 7 work items — backfill, Langfuse API pull, server-side filter, sort UX, deposit progress, token telemetry, resume-chain detection
  - [ ] Track 2 — Projects ↔ Sessions linking · spec [`docs/tracks/track-2-projects-sessions.md`](docs/tracks/track-2-projects-sessions.md)
    - Spawned session: `<tbd>` · title target: `track-2-projects-sessions`
    - 9 work items — canonical project registry, resolver, link_project stage, shared skill at SD.agents/skills/projects-sessions/, Obsidian bidirectional views, work-atoms integration, TUI upgrade, unlinked review, task-hierarchy schema (§2.8)
  - [ ] Track 3 — Preservator → SessionSkills pipeline · spec [`docs/tracks/track-3-preservator-pipeline.md`](docs/tracks/track-3-preservator-pipeline.md)
    - Spawned session: `<tbd>` · title target: `track-3-preservator-pipeline`
    - 6 work items — RAR reader, host-aware dedup, config, slug-alias hints to Track 2, launchd schedule, reverse archival (optional)
  - Spawn script: [`bin/spawn-tracks.sh`](bin/spawn-tracks.sh); prompts under [`docs/tracks/spawn/`](docs/tracks/spawn)
- [x] **Phase 2 — SessionSkills orchestrator build** (completed 2026-04-21)
    session: `f56a50a4-3dd9-49d9-a907-8ec1ee14859b` · title: `session-skills` · host: alex-mac
  - [x] `sessions/` package — record, store, llm, config, orchestrator, skill_paths, migrate_skills, review_tui
  - [x] 10 pipeline stages — ingest, merge, name, analyze, write_to_memory, cluster, classify, prune, archive, review
  - [x] Ollama local LLM integration (Qwen3-8B chat + nomic-embed-text embed), with Cloud + heuristic fallback
  - [x] `sm-pipeline` CLI + `sm-review` TUI + 5 launchd plists
  - [x] `sm-pipeline migrate-skills` one-button vault-skill migration
  - [x] v2 merge orphan ingest — `.jsonl.reset.*` / `.jsonl.deleted.*` (31 snapshot records recovered)
  - [x] Symlink guard — Synology Drive hardening for `~/.claude/projects` (launchd + SessionStart hook + `sm-pipeline doctor` check)
  - [x] Deterministic Langfuse trace + observation IDs → `sm deposit-all` fully idempotent
  - [x] Cross-host SSH path — `bin/_bootstrap.sh` + `.zshenv` PATH extension; sm commands work bare over `ssh alex@Alex-Mac.local`
  - [x] `sm-tui` enhancements — 🤖🦀 emoji badges, age/size tint, 90-day activity heatmap, substring filter (`/`), column sort (`s`), description column via LLM-slugged symlinks, right-pane preview (first-prompt + analyzed summary), gppu.data.Cache-backed API (~1700× speedup), `R` force-refresh
  - [x] wiki-raw-sources RAR archival (702 files, 6.8 MB compressed) out of git into vault cold storage
  - [x] Alex-PC/Surface skill-consolidation completed remotely via Obsidian-tracked task
- [x] **Phase 1 — Legacy SessionManager CLI + Langfuse SessionEnd hook** (pre-existing baseline)

## Documentation

- [ ] **Session Manager — documentation**
  - [x] Preservator README integrations section — current + desired SM handoff (2026-04-21) [session](~/.claude/projects/-home-alex-CRAP-preservator/a733ad67-781f-4a91-9ff0-829457eb1d3a.jsonl)
  - [x] SessionSkills Phase 3 track specifications under `docs/tracks/` (2026-04-21) [session](~/.claude/projects/-Users-alex-RAN-AI/f56a50a4-3dd9-49d9-a907-8ec1ee14859b.jsonl)

## Pending actions (user-initiated, Phase-3 side)

- [ ] **Spawn Phase-3 tracks** — on Mac: `/Users/alex/A/SessionManager/bin/spawn-tracks.sh` → three tmux sessions (`track1`/`track2`/`track3`) running in parallel. Replaces the `<tbd>` spawned-session markers above on first run.
- [ ] **Install launchd schedules** — `/Users/alex/A/SessionManager/launchd/install.sh` → hourly analyze, nightly cluster+classify, weekly prune+archive, symlink guard every hour.
- [ ] **Bulk Langfuse backfill** — `sm deposit-all` → closes the 3172-local vs 3017-remote gap. Safe since Phase 2 landed deterministic observation IDs (full idempotence).
- [ ] **Full analyze cascade** over the 3160 named records — `sm-pipeline run analyze write_to_memory`. Multi-hour Ollama run; produces structured summaries + writes them into OpenClaw per-agent memory SQLite.
- [ ] **Vault-skill migration** — `sm-pipeline migrate-skills --apply --rewrite-refs` → moves the 16 skills still in `~/_/{internals}/Skills/` into `SD.agents/skills/` and sweeps hardcoded references.

## Preservator-backfill

Plan at `~/.claude/plans/peppy-exploring-bee.md`. One-shot cleanup: every
session log on every host with mtime < 2026-04-20 → classify → dedup →
Langfuse → markdown-queue → RAR → archive originals. Overlaps Track 3
scope (cross-host session ingest) — reconcile when Track 3 lands §3.1.

- [ ] **Preservator-backfill — end-to-end** [session](~/.claude/projects/-home-alex-CRAP-preservator/2211216d-340c-4649-94ec-0ea52024e254.jsonl)
  - [x] Phase 1a — max_mtime filter in matchers + find helpers (content_pattern, file_extension, folders; local + SSH fast-paths with sentinel-touch) (2026-04-21)
  - [x] Phase 1b — `max_mtime: '2026-04-20'` set on llms.yaml content_pattern + folders entries (2026-04-21)
  - [ ] Phase 2 — config scoped + backfill run
    - [x] `_config/config.yaml` edited (staging.*.backfill; `aggregate_archive_name: prsvtr_backfill_*`; `dest_dirs.by_host: prsvtr.backfill`) — commit `671786db`, (2026-04-21)
    - [ ] Dress rehearsal on alex-mac: `preservator_v2.py --target alex-mac --preserve --no-tui`; confirm RAR at `SD.Lake/prsvtr.backfill/<date>/prsvtr_backfill_*_alex-mac.rar` + `_MANIFEST/inventory.csv` has no `mtime >= 2026-04-20`
    - [ ] Full run: `preservator_v2.py --all --preserve --merge --parallel 8`
    - [ ] After Phase 7 completes: `git revert 671786db` to restore nightly staging/output paths
  - [ ] Phase 3 — SessionManager/SessionSkills classify + Thread merge/dedup against staged tree. Re-scope to hook into `sm-pipeline` (ingest/merge/name steps) rather than a parallel sm-backfill.py, since the SessionSkills pipeline already owns the lifecycle
  - [ ] Phase 4 — `sm session deposit <staged/host>/llms.merged/` → Langfuse traces
  - [ ] Phase 5 — drop `.render-md.pending` markers next to merged sessions (renderer is a separate later one-shot — out of scope here)
  - [ ] Phase 6 — RAR the backfill tree to `SD.Lake/prsvtr.backfill/<date>/` (existing preserve step, new staging location)
  - [ ] Phase 7 — `preservator_v2.py --target <host> --archive --no-tui` per host, human-verified, after counts match
  - [ ] Verification checklist (single-host dress rehearsal on alex-mac before running `--all`): manifest mtime column all < 2026-04-20; Langfuse count == merged jsonl count; on-disk delta post-archive == inventory row count

## How to maintain this file

- Flat markdown checkboxes. Parent-first, children indented.
- When a track spawns, replace `<tbd>` with the session UUID (`ls -lt ~/.claude/projects/-Users-alex-A-SessionManager/*.jsonl | head -1`).
- When a task completes: check the box, add completion date, link the session(s) that did the work via `[session](~/.claude/projects/<slug>/<uuid>.jsonl)`.
- When Track 2's §2.1 lands the canonical registry at `~/_/KG/Project/_registry.yaml`, migrate this file's hierarchy there and reduce this to a one-line pointer.

---

**Phase 2 build session closed 2026-04-21.** All code committed and pushed: `akarelin/AGENTS.md` at `5c593d3`+ (contains the tracks/spec + TASKS.md + spawn script) and `akarelin/SessionManager` at `969547e`+ (contains all scripts + bin/_bootstrap.sh + sm-tui enhancements + deterministic deposit IDs). Next work picks up from the **Pending actions** list above — any session can resume.
