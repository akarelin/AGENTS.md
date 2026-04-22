# Track 2 — Handoff

Rolling handoff doc. Latest checkpoint at top, prior checkpoint below.

## Checkpoint 2026-04-21 (session `a2e8beb5-d2e9-426c-9c0c-eeb279bbae0f`, resumed from `66afd881…`)

Stopped after 2.7 per user ask. 2.6 + 2.8 finalization still pending.

| Subtask | Status | Notes |
|---|---|---|
| 2.1 Canonical project registry | ✅ | unchanged — 39 entries. Added `name`/`status` and switched Track 2 child to `session_ids:` list (now carries both the initial-build and resume UUIDs) so the task-tree renderer shows both. |
| 2.2 Resolver library | ✅ | unchanged. |
| 2.3 link_project pipeline stage | ✅ | unchanged. |
| 2.9 Shared skill | ✅ | unchanged. |
| 2.4 Obsidian emitter | ✅ | `sessions/stages/_obsidian_emit.py` (new). Splices `## Sessions` and (when `tasks:` present) `## Task tree` blocks into each project's `obsidian_page`, wrapped in `<!-- SessionSkills:auto BEGIN/END <name> -->` sentinels so hand-authored content is preserved. Uses `os.path.relpath` for vault-internal analyzed_md links. Idempotent: second run writes 0 pages. Added `SessionStore.iter_with_canonical_project()` as the data-access seam (store.py). Guard: `obsidian_page` that resolves to a directory (e.g. etls' `Projects/ETL and CRM/`) is skipped via `page.is_file()`. Registered projects emitted to so far: SessionSkills + Chmo (the 3 canonically-linked records). |
| 2.5 Unlinked-project review flow | ✅ | `sessions/review_tui.py`. Kind-dispatcher at top of the per-item loop. For `kind='unlinked_project'`: lists all 39 project ids; commands are `[p]ick existing / [n]ew project / [i]gnore / [s]kip / [q]uit`. Pick stamps `canonical_project` on the record(s) and marks the queue item `accepted`. New appends a minimal entry to `_registry.yaml` via text append (preserves comments/structure — no YAML round-trip). Also swapped `os.popen("date -u …")` for an internal `_now_iso()` helper. Smoke-tested end-to-end with piped stdin against a fake queue; 39 projects printed and dispatch ran clean. |
| 2.7 work-atoms prefer canonical | ✅ | `/Users/alex/_/{internals}/Skills/work-atoms/classify.py`. New `lookup_canonical(session_id)` queries the SessionSkills store across `(claude-code, openclaw, langfuse, codex)` sources and returns `(registry.name, registry.work_atom_slug)` with a per-process cache. `classify_session()` calls it first; on hit, skips the LLM call entirely and synthesizes a result dict with `atoms=[]` + a minimal timeline entry (matches spec: cost + consistency win; atoms aren't extracted in the canonical path). Registers `canonical_name → work_atom_slug` into `PROJECTS` so the downstream `project_slug()` routing still works. Smoke-tested: `lookup_canonical('f56a50a4…') → ('SessionManager', 'agents')`; `'88b89bcc…' → ('Chmo', 'chmo')`. |
| 2.6 TUI Projects view | ⏳ | not started. `_render_projects` at `scripts/sm-tui.py:732` currently groups `_remote_traces` by `metadata.project` (raw Langfuse tag). Narrow additive plan: add module-level helper that parses `~/_/KG/Project/_registry.yaml` with PyYAML (no `sessions.projects` import — sm-tui runs from `/RAN`), emit registry rows first (with tag-aggregated counts) then any unregistered tags below. Remember to sync the edited file to `/Users/alex/RAN/AI/SessionManager/scripts/sm-tui.py`. |
| 2.8 Task-hierarchy schema | 🟡 partial | Renderer is in (see 2.4). Still pending: reduce `TASKS.md` to a one-line pointer once everything else is clean. Leave this for the session that ships 2.6. |

### Incidental fixes this session

- **TASKS.md Track 1/3 UUIDs were swapped.** `c5ef017d` is Track 1 (sessions-langfuse), `b1c418ff` is Track 3 (preservator-pipeline) — confirmed by reading the first prompt of each jsonl. TASKS.md corrected.
- **Track 2 spawned-session line** updated with this session's UUID.

### Files touched this session

NEW:
  - `/Users/alex/A/SessionManager/sessions/stages/_obsidian_emit.py`

MODIFIED:
  - `/Users/alex/A/SessionManager/sessions/store.py` — added `iter_with_canonical_project()`.
  - `/Users/alex/A/SessionManager/sessions/review_tui.py` — unlinked_project dispatcher.
  - `/Users/alex/_/{internals}/Skills/work-atoms/classify.py` — canonical-prefer path.
  - `/Users/alex/_/KG/Project/_registry.yaml` — Track 2 child now `session_ids: []` (two UUIDs); all three tracks got `name:` + `status:` for cleaner Obsidian rendering.
  - `/Users/alex/A/SessionManager/TASKS.md` — Track 2 UUID + Track 1/3 swap fix.

### How to verify quickly

```bash
# Resolver + stage idempotence (both should return processed=0):
/Users/alex/RAN/AI/SessionManager/.venv/bin/python3 -m sessions.orchestrator run link_project --emit-obsidian
# Second run should write 0 pages:
/Users/alex/RAN/AI/SessionManager/.venv/bin/python3 -m sessions.orchestrator run link_project --emit-obsidian

# Emitted blocks:
grep -A 5 'SessionSkills:auto BEGIN' /Users/alex/_/Projects/SessionSkills.md
grep -A 5 'SessionSkills:auto BEGIN' /Users/alex/_/KG/Project/Chmo.md

# work-atoms canonical lookup:
/Users/alex/RAN/AI/SessionManager/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '/Users/alex/_/{internals}/Skills/work-atoms')
from classify import lookup_canonical
print(lookup_canonical('f56a50a4-3dd9-49d9-a907-8ec1ee14859b'))"
# → ('SessionManager', 'agents')
```

### Non-obvious pitfalls picked up this session

1. **`obsidian_page: Projects/ETL and CRM`** in the registry points to a directory, not a `.md` file. The emitter now guards with `page.is_file()`. Consider cleaning the registry entry or creating the page; left as-is for now.
2. **YAML comments are precious.** `_append_new_project` in `review_tui.py` does a *text append* (not load/dump) so the heavily-commented registry survives. Any future alias-self-healing on existing entries needs a line-targeted edit or ruamel.yaml — don't let PyYAML round-trip the whole file.
3. **sm-tui runs from `/RAN`**, not `/A`. Writing to only `/A/SessionManager/scripts/sm-tui.py` won't take effect. When 2.6 lands, sync to `/Users/alex/RAN/AI/SessionManager/scripts/sm-tui.py` too.
4. **Track 2 owns both session UUIDs.** Registry now uses `session_ids:` (plural) for Track 2 to hold both `66afd881` (initial) and `a2e8beb5` (resume). The resolver already handles both `session_id` and `session_ids`.

---

## Checkpoint 2026-04-21 (session `66afd881-8b89-4e24-bd00-64bdb7704dae`)

Written by session `66afd881-8b89-4e24-bd00-64bdb7704dae` on 2026-04-21
to hand work off mid-flight. Read this **before** picking up — it
captures what landed, what didn't, and the non-obvious quirks you'll
hit if you skim only the spec.

### Status

| Subtask | Status | Notes |
|---|---|---|
| 2.1 Canonical project registry | ✅ | 39 entries at `~/_/KG/Project/_registry.yaml` (8 work-atoms originals + sessionmanager-with-tasks + 21 KG/Project pages + 9 Projects/ pages + suntrust + preservator). |
| 2.2 Resolver library | ✅ | `sessions/projects.py`. Returns `(canonical_project_id, task_id)`. Caches by file mtime. Priority: existing→tasks-session_id→slug→agent→tag→fuzzy. |
| 2.3 link_project pipeline stage | ✅ | `sessions/stages/link_project.py`. Eligible states: analyzed/memorized/clustered/classified. Wired into `orchestrator.KNOWN_STAGES` and `sessionskills.yaml` default+nightly pipelines. Stage does **not** advance state — runs idempotently. `--emit-obsidian` flag wired (delegate not yet implemented). Verified: 3/3 store records resolve correctly (sessionmanager + 2x chmo). |
| 2.9 Shared skill | ✅ | `~/SD.agents/skills/projects-sessions/SKILL.md`. Instruction-style (per user feedback "Its not supposed to be a script. Backstop is a skill that instructs claude code…"). No `scripts/` subdir — agents/Claude Code use `python3 -c "from sessions.projects import …"` one-liners shown in the SKILL. |
| 2.7 work-atoms prefer canonical | ⏳ | not started |
| 2.4 Obsidian emitter | ⏳ | `link_project.py` already imports `from . import _obsidian_emit` lazily; just write that module. |
| 2.6 TUI Projects view | ⏳ | not started |
| 2.5 Unlinked-project review flow | ⏳ | `link_project.py` already enqueues `kind='unlinked_project'` items into `~/.sessionskills/review_queue.json`. Just extend `sessions/review_tui.py` to handle the kind. |
| 2.8 Task-hierarchy schema | 🟡 partial | Registry already carries `tasks:` block under `sessionmanager`. Resolver returns `task_id`. Stage writes `task_id` and `task_parent_path` to `classification`. Remaining: Obsidian task-tree renderer (folds into 2.4) + reduce TASKS.md to a pointer (do this last, after 2.4 ships). |

## Files touched

NEW:
  - `/Users/alex/_/KG/Project/_registry.yaml`
  - `/Users/alex/A/SessionManager/sessions/projects.py`
  - `/Users/alex/A/SessionManager/sessions/stages/link_project.py`
  - `/Users/alex/SD.agents/skills/projects-sessions/SKILL.md`
  - `/Users/alex/A/SessionManager/docs/tracks/track-2-handoff.md` (this file)
  - `/Users/alex/A/SessionManager/docs/tracks/spawn/track-2-resume.prompt.txt`

MODIFIED:
  - `/Users/alex/A/SessionManager/sessions/orchestrator.py` — added `link_project` to `KNOWN_STAGES`; added `--emit-obsidian` CLI flag; passed through to `cmd_run`.
  - `/Users/alex/A/SessionManager/sessionskills.yaml` — added `link_project` to `default` and `nightly` pipelines.
  - `/Users/alex/A/SessionManager/TASKS.md` — set Track 2 spawned-session UUID.

## Non-obvious quirks (read these — they will bite you)

1. **`sessions/` package lives in `/A` only.** `/Users/alex/RAN/AI/SessionManager` does NOT have a `sessions/` directory. `bin/_bootstrap.sh` sets `SM_PY` from the venv at `/RAN/AI/SessionManager/.venv/`, but `bin/sm-pipeline` then `cd`s into the dir that *does* contain `sessions/` (which is `/A/SessionManager`). So when you create new `sessions/*.py` files, write them to `/A/SessionManager/sessions/` only — do NOT mirror to `/RAN`.

2. **`scripts/sm-tui.py` IS mirrored to `/RAN`.** `bin/sm-tui` runs from `$SM_REPO/scripts/sm-tui.py` where `SM_REPO=/Users/alex/RAN/AI/SessionManager`. So sm-tui edits MUST be written to BOTH locations. Currently in sync (43866 bytes, mtime 20:21 — Track 1's last edit). When task 2.6 lands, `cp /A/SessionManager/scripts/sm-tui.py /RAN/AI/SessionManager/scripts/sm-tui.py` after the edit.

3. **work-atoms skill location.** `/Users/alex/_/{internals}/Skills/work-atoms/` (literal `{internals}` braces in the path; that's not a shell variable). The migration to `SD.agents/skills/` is task #15 in TASKS.md (pending). For 2.7, edit at the current location; the future migration will carry the patch.

4. **Resolver priority gotcha.** Slug-based matching alone is insufficient — the same slug `-Users-alex-RAN-AI` could mean either the RAN umbrella or any project rooted there (SessionSkills happens to live at `/RAN/AI/SessionManager`, but its raw_jsonl path is `~/.claude/projects/-Users-alex-RAN-AI/`). The resolver fixes this by checking `tasks: session_ids` first (priority 1.5, before slug). Verified: f56a50a4 (Phase 2) resolves to `sessionmanager`, 2ead04b6 (random RAN/AI work) resolves to `ran`.

5. **Registry mtime caching.** `load_registry()` re-reads only when the YAML's mtime changes. After editing the registry programmatically, call `load_registry(force=True)` or wait one second so mtime ticks.

6. **Track 1 and Track 3 are spawning sessions in parallel.** Their session UUIDs are recorded in TASKS.md (Track 1: c5ef017d, Track 3: b1c418ff). They may modify shared files (TASKS.md notably) while you're working — re-read before editing. Track 1 is also actively touching scripts/sm-tui.py — coordinate before doing 2.6.

## Verification snippets

Resolver loads + smoke test:

```bash
/Users/alex/RAN/AI/SessionManager/.venv/bin/python3 -c "
import json
from sessions.projects import load_registry, resolve_by_source_id
print('registry:', len(load_registry()))
print(json.dumps(resolve_by_source_id('claude-code','f56a50a4-3dd9-49d9-a907-8ec1ee14859b'), indent=2))"
```

Stage idempotence:

```bash
/Users/alex/RAN/AI/SessionManager/.venv/bin/python3 -m sessions.orchestrator run link_project
# expect: processed=0 skipped=3 (or whatever current count) errors=0
```

Linked records in store:

```bash
sqlite3 ~/.sessionskills/store.sqlite "
SELECT json_extract(json,'\$.classification.canonical_project') AS p, COUNT(*)
FROM records GROUP BY p"
```

## Pending work order

Recommend: 2.4 first (Obsidian emitter — finishes the bidirectional view that
makes everything else demonstrable), then 2.5 (review TUI — small), then 2.7
(work-atoms — small), then 2.6 (TUI Projects view — coordinate with Track 1),
then 2.8 finalization (TASKS.md → pointer).

---

**Session 66afd881 closed 2026-04-22.** Track-2 ownership transferred to
session `a2e8beb5-d2e9-426c-9c0c-eeb279bbae0f` (resume), which shipped
2.4 / 2.5 / 2.7 — see the latest checkpoint at the top of this file.
Remaining for the next session: **2.6** (TUI Projects view — narrow
additive change to scripts/sm-tui.py; coordinate with Track 1) and
**2.8 finalization** (reduce TASKS.md to a one-line pointer to the
registry's `tasks:` block).
