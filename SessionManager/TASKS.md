# Tasks

Markdown-tracked work for SessionManager + SessionSkills. Flat list with
nested checkboxes — parent task first, subtasks indented below. Closed
items keep their completion date so the history is auditable.

## SessionManager (meta project)

- [ ] **Phase 3 — Parallel tracks** (in_progress; blocked_by Phase 2)
  - [x] Track 1 — Sessions & Langfuse · spec [`docs/tracks/track-1-sessions-langfuse.md`](docs/tracks/track-1-sessions-langfuse.md) (completed 2026-04-22)
    - Spawned session: `b1c418ff-5954-4d35-b0b9-196225cc8f2f` · title: `track1-langfuse` · host: alex-mac
    - 7 work items — backfill, Langfuse API pull, server-side filter, sort UX, deposit progress, token telemetry, resume-chain detection
    - [x] 1.1 Bulk backfill (72 min, 2026-04-21): `sm deposit-all` 6,348 deposited / 0 failed; Langfuse `meta.totalItems` = 5,925 post-run (≥ 3,172 local target ✓). Log: `/tmp/track1/deposit-all.log`
    - [x] 1.2 Langfuse API pull ingest (`sessions/stages/ingest.py` + `SessionStore.known_langfuse_trace_ids`)
    - [x] 1.3 Server-side `name=` filter in TUI remote view
    - [x] 1.4 Cycle-column sort UX + ▲/▼ header glyph (`s` advances col, `S` reverses)
    - [x] 1.5 Deposit ProgressBar + rolling ETA in `_do_deposit_all()`
    - [x] 1.6 Ollama token telemetry — `LocalLLM.generate(return_meta=True)` + `record_tokens()` helper; analyze stage reads `ollama-tokens.jsonl` sidecar emitted by `llm-analyze.py`; `sm-pipeline stats` rolls up per-stage prompt/eval counts
    - [x] 1.7 Cross-session resume-chain detection in merge (`RESUME_PREFIX_RE`, `store.previous_claude_session_in_project()`, 30-min default window configurable via `thresholds.resume_chain_window_s`)
  - [ ] Track 2 — Projects ↔ Sessions linking · spec [`docs/tracks/track-2-projects-sessions.md`](docs/tracks/track-2-projects-sessions.md)
    - Sessions (chain): `66afd881-8b89-4e24-bd00-64bdb7704dae` (initial build, handoff) → `a2e8beb5-d2e9-426c-9c0c-eeb279bbae0f` (resume, finished 2026-04-21)
    - 9 work items — canonical project registry, resolver, link_project stage, shared skill at SD.agents/skills/projects-sessions/, Obsidian bidirectional views, work-atoms integration, TUI upgrade, unlinked review, task-hierarchy schema (§2.8)
    - [x] 2.1 Canonical project registry — 39 entries at `~/_/KG/Project/_registry.yaml` (session `66afd881`, 2026-04-21)
    - [x] 2.2 Resolver library — `sessions/projects.py`, priority-ordered, mtime-cached (session `66afd881`, 2026-04-21)
    - [x] 2.3 link_project pipeline stage — `sessions/stages/link_project.py`, wired to default+nightly, idempotent (session `66afd881`, 2026-04-21)
    - [x] 2.4 Obsidian emitter — `sessions/stages/_obsidian_emit.py`; `## Sessions` + `## Task tree` blocks on project pages, splice sentinels, idempotent (session `a2e8beb5`, 2026-04-21)
    - [x] 2.5 Unlinked-project review flow — kind-dispatch in `sessions/review_tui.py`; `[p]ick/[n]ew/[i]gnore/[s]kip/[q]uit` against the 39-entry registry; text-append for new entries preserves YAML comments (session `a2e8beb5`, 2026-04-21)
    - [x] 2.7 work-atoms prefer canonical — `/Users/alex/_/{internals}/Skills/work-atoms/classify.py` new `lookup_canonical()` short-circuits the LLM call when SessionSkills already resolved the project (cost + consistency win per spec) (session `a2e8beb5`, 2026-04-21)
    - [x] 2.9 Shared skill — instruction-style `~/SD.agents/skills/projects-sessions/SKILL.md` (session `66afd881`, 2026-04-21)
    - [ ] 2.6 TUI Projects view — plan in handoff (source registry rows from `~/_/KG/Project/_registry.yaml`, additive to Langfuse-tag aggregation; sync `/A` ↔ `/RAN`)
    - [ ] 2.8 Finalization — reduce this TASKS.md to a pointer to the registry's `tasks:` block once 2.6 lands
    - Incidental fixes this chain: registry `sessionmanager.tasks` now carries `name:`/`status:` + `session_ids:` list on Track 2. (Note: the earlier "Track 1/3 UUIDs swapped" fix over-corrected — actual spawns are b1c418ff=Track1, c5ef017d=Track3, restored 2026-04-22.)
    - **Session title note:** this resume session (`a2e8beb5`) got auto-classified to project `backstop` (via `/rename` or client-side tagger) — the canonical project is `sessionmanager`. Registry + store linkage for this session will need to be re-stamped manually (or by running `link_project` once the session's JSONL is ingested)
  - [x] Track 3 — Preservator → SessionSkills pipeline · spec [`docs/tracks/track-3-preservator-pipeline.md`](docs/tracks/track-3-preservator-pipeline.md) (completed 2026-04-21)
    - Spawned session: `c5ef017d-f79c-4b7b-89af-a03d699147be` · title target: `track-3-preservator-pipeline`
    - [x] 3.1 RAR reader — `sessions/stages/ingest_preservator.py` walks `prsvtr.by_hst/<host>/YYYYMMDD/*.rar`, filters members by `inner_patterns`, stream-extracts via `rar p -inul` into sha256 content-addressed cache under `~/.sessionskills/preservator-cache/<aa>/<digest>/`. Delegated into the existing `ingest` stage via the new `kind: rar` case, so `sm-pipeline run ingest --source preservator` works end-to-end. Harnessed against live RARs on `/Volumes/S1/SD.Lake/prsvtr.by_hst` — 109/2720 matches on alex-xsolla 2026-04-20 RAR, 20 records materialized (2026-04-21)
    - [x] 3.2 `sessionskills.yaml` `preservator` source block + `SessionRecord.origin_host` field; local-fs ingest tags `origin_host='alex-mac'` (2026-04-21)
    - [x] 3.3 Host-aware dedup via `content_hash`; duplicate-content upsert merges `paths.preservator_rar_history[]` and rewrites `paths.preservator_rar` to the newer RAR (2026-04-21)
    - [x] 3.4 Cross-host Claude Code `host_slug_alias` hints written to `~/.sessionskills/review_queue.json` for Track 2's unlinked-project reviewer. Dedup key `(kind, host, slug)` (2026-04-21)
    - [x] 3.5 `launchd/ai.sessionskills.preservator-ingest.plist` — every 6 h `sm-pipeline run ingest --source preservator`, logs to `~/Library/Logs/sessionskills-preservator.log`. Auto-picked up by the existing `launchd/install.sh` glob (2026-04-21)
    - [x] 3.6 Reverse archival — decision (option a) stays: preservator-side adds alex-mac to `workstations.yaml` over SSH; SessionSkills is read-only against the archive tree, no code needed here (2026-04-21)
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

## Quick-start — run this on alex-mac to resume Phase 3

```bash
ssh alex@Alex-Mac.local
cd /Users/alex/A/SessionManager
./bin/spawn-tracks.sh          # fires Track 1 + 2 + 3 in detached tmux
./launchd/install.sh           # installs hourly/nightly/weekly schedules + symlink guard
tmux attach -t track1          # supervise any of {track1,track2,track3}; Ctrl-b d to detach

# Optional, large-scope:
sm deposit-all                 # backfill ~155 undeposited Langfuse traces (idempotent)
sm-pipeline run analyze write_to_memory   # multi-hour Ollama run; 3000+ sessions → agent memory
sm-pipeline migrate-skills --apply --rewrite-refs    # 16 vault skills → SD.agents/skills/
```

## Pending actions (user-initiated, Phase-3 side)

- [x] **Spawn Phase-3 tracks** (2026-04-21) — three parallel tmux sessions fired via `bin/spawn-tracks.sh`; all three landed (Track 1 completed 2026-04-22, Tracks 2/3 completed 2026-04-21).
- [x] **Bulk Langfuse backfill** (2026-04-21, closed by Track 1 session `b1c418ff`) — `sm deposit-all` 6,348 deposits / 0 failed / 72 min; Langfuse `meta.totalItems` = 5,925 post-run.
- [ ] **Install launchd schedules** — `/Users/alex/A/SessionManager/launchd/install.sh` → hourly analyze, nightly cluster+classify, weekly prune+archive, symlink guard every hour. Now also includes `ai.sessionskills.preservator-ingest.plist` (6 h) courtesy of Track 3 §3.5.
- [ ] **Full analyze cascade** over the 3160 named records — `sm-pipeline run analyze write_to_memory`. Multi-hour Ollama run; produces structured summaries + writes them into OpenClaw per-agent memory SQLite. Token telemetry (Track 1 §1.6) will surface in `sm-pipeline stats` after.
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

**Track 1 session closed 2026-04-22** (session `b1c418ff`). All 7 work items landed + verified. Canonical commits: `082de40` (main Track 1 land), `694fcb5` (sm-tui self-review nits), `c895b95` (TASKS.md backfill close). Mirror at `akarelin/SessionManager`: `090d71d`, `572d3a5` (sm-tui sync). Post-run Langfuse state: 5,925 traces / 10-day-span median ~500 sessions/day; daily breakdown captured in this session's transcript. Phase 3 tracks 1 + 3 are fully complete; Track 2 has 2.6 (TUI Projects view) + 2.8 (TASKS.md → registry migration) remaining.
