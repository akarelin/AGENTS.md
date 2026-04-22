# Track 2 — Projects ↔ Sessions Linking

**Owner scope:** make "project" a first-class concept. Unify the five disparate notions of project across the stack + give every session a canonical `project` handle with bidirectional links.

## Context

"Project" exists in five unreconciled forms across Alex's stack:

| # | Where | What it is | Storage | Example |
|---|---|---|---|---|
| 1 | Claude Code project slug | cwd-encoded dir name | `~/.claude/projects/<slug>/` (→ SD-synced) | `-Users-alex-RAN-AI` |
| 2 | OpenClaw agent (per-agent "project") | Each agent has its own sessions dir | `~/.openclaw/agents/<agent>/sessions/` | `alex`, `irina`, `knowledge` |
| 3 | work-atoms project | Logical/business work area assigned by `work-atoms/classify.py` | `~/_/{internals}/classification/<slug>_atoms.json` | `SmartHome`, `ETLs`, `Xsolla/OfficeFortress`, `Agents/Chmo` |
| 4 | Obsidian Project page | Human-authored note | `~/_/Projects/*.md` or `~/_/KG/Project/*.md` | `[[SessionSkills]]`, `[[OpenClaw]]`, `[[NER from session-intel]]` |
| 5 | Langfuse `project` tag | Metadata on each trace | Langfuse server | `project:-Users-alex-RAN-AI` |

These don't know about each other. Some specific symptoms:
- `sm-tui`'s Projects view (key `3`) only aggregates form 5.
- Classifying a session into `SmartHome` (form 3) has no effect on the Obsidian `[[SmartHome]]` note (form 4).
- When Alex opens `[[SmartHome]].md` in Obsidian, there's no direct list of sessions that contributed to it.
- Different projects with similar names (`Chmo`, `Agents/Chmo`, `chmo-mgmt` agent, `/Users/alex/RAN/AI/chmo` cwd) aren't recognized as the same thing.

## Goal

One canonical **Project** entity (the `project_id`) that every layer knows by. Then bidirectional link:
- **Session → Project**: `record.classification.canonical_project = 'project:smarthome'` (stable ID).
- **Project → Sessions**: dataview-style query on the Obsidian project page lists every session record (with description, date, outcome).

## Current state

- No canonical project registry exists. All five forms float independently.
- `work-atoms/classify.py` hardcodes 8 projects (`SmartHome`, `Tools/gppu`, `ETLs`, `Xsolla/OfficeFortress`, `Agents`, `Agents/Chmo`, `FileIndexer`, `Transcription`). Not used by TUI or store.
- Obsidian has ~30 project pages under `~/_/KG/Project/` and `~/_/Projects/`; most have frontmatter but no structured ID.
- The classify stage writes `classification.work_atom_project` to the store — so layer 3 is the furthest along. Track 2 extends it.

## Work items

### 2.1 — Define the canonical Project registry

- **New file:** `/Users/alex/_/KG/Project/_registry.yaml` — authoritative list of project IDs, each with:
  ```yaml
  - id: smarthome
    name: SmartHome
    aliases: [SmartHome, smart-home, ha, home-assistant]
    claude_code_slugs: [-Users-alex-Hassios, -Users-alex-RAN-Hassios]
    openclaw_agents: []
    work_atom_slug: smarthome
    langfuse_tag: project:smarthome
    obsidian_page: KG/Project/SmartHome.md
  - id: sessionskills
    name: SessionSkills
    aliases: [sessionskills, session-skills, SessionManager]
    claude_code_slugs: [-Users-alex-A-SessionManager, -Users-alex-RAN-AI-SessionManager]
    openclaw_agents: []
    work_atom_slug: agents
    langfuse_tag: project:sessionskills
    obsidian_page: Projects/SessionSkills.md
  - id: chmo
    name: Chmo
    aliases: [chmo, Agents/Chmo, openclaw]
    claude_code_slugs: [-Users-alex-RAN-AI-chmo]
    openclaw_agents: [chmo-mgmt, manage-chmo]
    work_atom_slug: chmo
    langfuse_tag: project:chmo
    obsidian_page: KG/Project/Chmo.md
  # ... one entry per project
  ```
- Initial set: one entry per existing work-atoms project + every existing `~/_/KG/Project/*.md`.
- `aliases` drives fuzzy matching for session → project resolution.

### 2.2 — Resolver library

- **New file:** `/Users/alex/A/SessionManager/sessions/projects.py`
- Loads `_registry.yaml` at import time; caches it.
- Function `resolve(record: SessionRecord) -> str | None` applies this priority:
  1. Already set? Return `record.classification['canonical_project']`.
  2. Claude Code source + slug match → project whose `claude_code_slugs` contains the slug.
  3. OpenClaw source + agent match → project whose `openclaw_agents` contains the agent.
  4. Langfuse tag match → project whose `langfuse_tag` matches a trace tag.
  5. Topic-slug fuzzy match against `aliases` (token overlap > 0.7).
  6. None → None (un-linked; goes to Track 2.5 for manual attention).

### 2.3 — New pipeline stage: `link_project`

- **New file:** `/Users/alex/A/SessionManager/sessions/stages/link_project.py`
- Input states: `analyzed`, `clustered`, `classified`.
- For each record, call `projects.resolve(record)` and set `classification.canonical_project` + `classification.project_name`.
- Records that don't resolve get flagged to the review queue (`kind='unlinked_project'`).
- Output state: unchanged (runs alongside existing stages — doesn't advance state).

Wire into the default pipeline in `sessionskills.yaml`:
```yaml
pipeline:
  default: [ingest, merge, name, analyze, write_to_memory, cluster, classify, link_project, review]
```

### 2.4 — Bidirectional view — sessions on project pages

Every `~/_/KG/Project/<name>.md` gets a dataview-or-custom block that queries the SessionSkills store:

```markdown
## Sessions

(auto-generated from ~/.sessionskills/store.sqlite)
- 2026-04-21 [[🤖]] [session-skills](session-intel/analyzed/claude-code/claude-code-...md) — f56a50a4
- 2026-04-18 [[🦀]] [loan-dispute-letter-update](...) — 232650be
```

Implementation options:
- **(a) Obsidian plugin query** — user has `obsidian-ops` skill; extend it to regenerate this block on demand.
- **(b) Nightly cron** — `sm-pipeline run link_project --emit-obsidian` writes the markdown directly.

Pick (b) — keeps the generation on the SessionSkills side; plain markdown; no plugin dependency.

### 2.5 — Unlinked-project review flow

When `link_project` can't resolve a record, enqueue a review item:
```json
{
  "kind": "unlinked_project",
  "record_ids": ["openclaw:abc123..."],
  "proposal": {"canonical_project": null},
  "reason": "no alias/slug/agent match; topic_slug='truist-payoff-dispute'",
  "confidence": 0
}
```

Reviewer (via `sm-review`) can pick an existing project, create a new one, or mark `ignore`. Accepting an existing pick adds the session's slug/agent to that project's `aliases` in the registry (self-healing — next similar session auto-links).

### 2.6 — TUI Projects view (key `3`) upgrade

Currently aggregates Langfuse traces by `metadata.project`. Upgrade to:
- Use the canonical project registry as the row source (every registry entry, even with 0 sessions).
- Show sessions-count (local + remote), theme, total tokens, last-activity age.
- Press `Enter` on a row → right pane shows the list of sessions (paginated) and a link to the Obsidian page.

### 2.8 — Project task hierarchy (phases + subtasks + session-as-task)

**What the user asked for (2026-04-21, verbatim):** *"add task for project management in session-skills to mark this task (and its session) as subtask of session manager - phase 2 and mark it completed, create new child tasks linked to new spawned claudes are parts of phase 3 (parallel)"*.

In plain words: **a project should be a hierarchical container of tasks, where a task can itself be a session**. This is a missing dimension of the canonical project registry — the registry (2.1) captures *identity* (which project a session belongs to) but not *structure* (where in the project's work breakdown this session sits).

#### The concrete hierarchy requested

```
SessionManager                               ← umbrella project (2.1 registry entry)
│
├── Phase 1: Legacy SessionManager CLI       ← pre-existing, status = done
│   (no specific session tied; history-only)
│
├── Phase 2: SessionSkills orchestrator build   ← status = COMPLETED (2026-04-21)
│   session: f56a50a4-3dd9-49d9-a907-8ec1ee14859b  (title: "session-skills")
│   delivered: ingest/merge/name/analyze/write_to_memory/cluster/classify/
│              prune/archive/review + launchd + Ollama + TUI + cache + migrate-skills
│              + orphan ingest + symlink hardening + sm-deposit idempotence
│
└── Phase 3: Parallel Tracks                 ← status = in_progress, parallel=true
    ├── Track 1: Sessions & Langfuse         ← session: <tbd-when-spawned>
    ├── Track 2: Projects ↔ Sessions linking ← session: <tbd>    ← owns THIS feature
    └── Track 3: Preservator → SessionSkills ← session: <tbd>
```

Already registered in two places:

1. **In-session task tracker** — tasks #25 (SessionManager meta), #26 (Phase 2, **completed**), #27 (Phase 3 parent, blocked-by #26), #28/#29/#30 (the three track children, blocked-by #27). Metadata carries `phase`, `parent_task`, `target_session_id` / `target_session_title`. Volatile — only persists within the current Claude Code session.
2. **Interim persistent file** — `/Users/alex/A/SessionManager/TASKS.md`. Same hierarchy, plain markdown, survives across sessions. **Use this as the source of truth until Track 2 lands the canonical registry** (see below).

#### Why this belongs in Track 2

Because every element of that hierarchy *is* or *contains* a project in the canonical sense: SessionManager is the umbrella project, each Phase is a sub-project, each Track is a sub-project with its own session. The registry from 2.1 already has one entry per project. Extending it to carry phase/subtask structure is a natural fit — no new primitive required.

#### Current home: `/Users/alex/A/SessionManager/TASKS.md` (interim)

While Track 2 is in flight, the task hierarchy lives in **`TASKS.md`** at the SessionManager repo root. It's plain markdown, versionable alongside the code, and already populated with the full Phase-1 / Phase-2 (complete) / Phase-3 (parallel) tree. When §2.1 lands the canonical registry, migrate this content into `~/_/KG/Project/_registry.yaml` under the `sessionmanager:` entry's `tasks:` block, and reduce `TASKS.md` to a one-line pointer.

#### Target schema extension to `_registry.yaml`

Add optional `tasks:` block per project entry:

```yaml
- id: sessionmanager                # 'SessionManager (meta project)'
  name: SessionManager
  aliases: [SessionManager, session-manager]
  obsidian_page: Projects/SessionManager.md     # to be created if absent
  tasks:
    - id: phase-1-legacy-cli
      name: "Phase 1: Legacy SessionManager CLI"
      status: done
      session_ids: []
    - id: phase-2-sessionskills-build
      name: "Phase 2: SessionSkills orchestrator build"
      status: completed
      completed_at: 2026-04-21
      session_ids: [f56a50a4-3dd9-49d9-a907-8ec1ee14859b]
      delivered:
        - ingest/merge/name/analyze/write_to_memory stages
        - cluster/classify/prune/archive/review stages
        - Ollama + Qwen3 + nomic-embed integration
        - sm-pipeline CLI + sm-tui enhancements + gppu cache
        - migrate-skills subcommand; orphan ingest; symlink hardening
        - sm deposit idempotence (deterministic observation IDs)
    - id: phase-3-parallel-tracks
      name: "Phase 3: Parallel tracks"
      status: in_progress
      parallel: true
      blocked_by: phase-2-sessionskills-build
      children:
        - id: track-1-sessions-langfuse
          doc: docs/tracks/track-1-sessions-langfuse.md
          session_id: null   # populate when spawn one-liner runs
        - id: track-2-projects-sessions
          doc: docs/tracks/track-2-projects-sessions.md
          session_id: null
        - id: track-3-preservator-pipeline
          doc: docs/tracks/track-3-preservator-pipeline.md
          session_id: null
```

#### Reverse link: session → task

Extend `SessionRecord.classification` with two optional fields (no schema migration — it's already a JSON dict):

| Field | Meaning |
|---|---|
| `classification.task_id` | The task this session belongs to (e.g. `phase-2-sessionskills-build` or `track-1-sessions-langfuse`) |
| `classification.task_parent_path` | Path of parent IDs, e.g. `sessionmanager/phase-3-parallel-tracks/track-1-sessions-langfuse` |

Populated automatically by `link_project` stage (2.3) whenever a session's title matches a task's registered `name` / `target_session_title`, or when the session_id is already listed under a task.

#### Obsidian bidirectional view (extends 2.4)

On every `~/_/Projects/<project>.md`, in addition to the flat session list, render a task tree:

```markdown
## Task tree

- **Phase 2: SessionSkills orchestrator build** — ✅ 2026-04-21 · [[sessions/f56a50a4...]]
- **Phase 3: Parallel tracks** — 🚧
  - **Track 1: Sessions & Langfuse** — [[sessions/<id-when-spawned>]]
  - **Track 2: Projects ↔ Sessions linking** — [[sessions/<id>]]
  - **Track 3: Preservator → SessionSkills** — [[sessions/<id>]]
```

Generator: same cron / `sm-pipeline run link_project --emit-obsidian` as 2.4, just with an extra pass that walks the registry's `tasks:` tree.

#### Implementation scope

- **New:** Task-tree section in `_registry.yaml` (no code change — pure data).
- **New:** Minor extension in `sessions/projects.py` to also load `tasks:` block and allow resolver to return `(canonical_project, task_id)` instead of just project.
- **New:** Templating helper in the Obsidian emitter (2.4's generator) for the task tree.
- **Optional:** A small `sm-pipeline tasks` subcommand mirroring what the external task-tracker (where #25–#30 live) shows — `list`, `add`, `done`, `link-session <uuid>`. Keeps the task data under the canonical registry, not scattered across tools.
- **Sync with the external task tracker:** when a tracked task has `target_session_title`, poll for a session whose record has a matching custom title and auto-fill `target_session_id`. This is the "linked to new spawned claudes" part of the user's ask — once the three Track-N sessions exist, link them back.

Patch `work-atoms/classify.py` to prefer `classification.canonical_project` when present (skip its own LLM classification call — already resolved). Major cost + consistency win.

- **Touch:** `/Users/alex/SD.agents/skills/work-atoms/classify.py` (or wherever it lands post-vault-mv).

### 2.9 — Expose as a shared skill (`projects-sessions`)

The functionality built in §2.1–§2.8 must be usable from **both chmo agents** (via OpenClaw's skill-discovery mechanism) **and from Claude Code** (via `~/.claude/skills` → `SD.agents/skills/`). Per the established rule ("everything related to skills is done around `SD.agents/skills/`"), Track 2 must land a skill at:

```
/Users/alex/SD.agents/skills/projects-sessions/
├── SKILL.md                    # frontmatter + triggers + subcommand map
└── scripts/
    ├── resolve.py              # thin CLI over sessions.projects.resolve()
    ├── link_session.py         # assign a session to a project/task
    ├── list_sessions.py        # list sessions under a project or task
    ├── list_projects.py        # list registered projects (from _registry.yaml)
    ├── add_project.py          # register a new project (appends to registry)
    └── sync_to_obsidian.py     # regenerate sessions lists on project pages
```

**Discovery triggers in SKILL.md** (draft):

```yaml
name: projects-sessions
description: "Canonical project registry and session↔project linking. Use when asked to 'show sessions for project X', 'link this session to project Y', 'list my projects', 'what work was done on SessionSkills', 'regenerate project pages', or anything that crosses the session/project/task boundary."
argument-hint: "<subcommand> [args]"
allowed-tools: [Bash, Read]
```

**Shared-library / CLI design.** The Python-level logic lives in `/Users/alex/A/SessionManager/sessions/projects.py` (from §2.2). The skill's scripts are thin wrappers that import or subprocess-call into that, so:

- `sessions/projects.py` is the single source of truth for resolver logic.
- `SD.agents/skills/projects-sessions/scripts/*.py` are minimal CLIs that both chmo and Claude Code can invoke by filesystem path.

Example wrapper body (`resolve.py`):

```python
#!/usr/bin/env python3
"""Resolve a session to its canonical project. CLI wrapper around
sessions.projects.resolve() for use by chmo agents + Claude Code."""
import sys
sys.path.insert(0, "/Users/alex/A/SessionManager")
from sessions.projects import resolve_by_source_id
import json
src, sid = sys.argv[1], sys.argv[2]
result = resolve_by_source_id(src, sid)
print(json.dumps(result, indent=2))
```

**Usage from chmo agents.** chmo's `openclaw agent` can call any SD.agents/skills/ script via a shell tool call — no new integration needed, the skill just needs to exist in the right place and have a SKILL.md that triggers appropriately.

**Usage from Claude Code.** Same — Claude Code auto-discovers skills under `~/.claude/skills/` (symlinked to `SD.agents/skills/`). After Track 2 lands, Claude Code sessions will see `projects-sessions` in their available skills list alongside `chmo`, `qmd-sessions-rename`, `session-intel`, etc.

**Venv + python interpreter.** The scripts run under whichever Python the caller uses. Because `sessions.projects` has no heavy deps beyond PyYAML (already in the SessionManager venv) and stdlib, the wrappers should work under system python3 on any host. For the rare cases where `sessions.projects` grows dependencies, the wrappers should shell out to `/Users/alex/A/SessionManager/bin/sm-pipeline` instead of importing — which already resolves the venv via `bin/_bootstrap.sh`.

**Acceptance:**

1. `ls /Users/alex/SD.agents/skills/projects-sessions/` — SKILL.md + scripts/ visible.
2. Claude Code's Skill tool lists `projects-sessions` after restart.
3. `openclaw agent --agent alex -m "list sessions for project smarthome"` — alex agent finds and invokes the skill's `list_sessions.py`.
4. `python3 /Users/alex/SD.agents/skills/projects-sessions/scripts/list_projects.py | head` — prints the registered projects from `_registry.yaml`.
5. All logic paths converge on `sessions.projects.*` — no logic duplication between the skill and the SessionManager module.

## Files in scope

**New:**
- `/Users/alex/_/KG/Project/_registry.yaml` — canonical project registry
- `/Users/alex/A/SessionManager/sessions/projects.py` — resolver library
- `/Users/alex/A/SessionManager/sessions/stages/link_project.py` — pipeline stage
- `/Users/alex/SD.agents/skills/projects-sessions/SKILL.md` — discovery metadata
- `/Users/alex/SD.agents/skills/projects-sessions/scripts/{resolve,link_session,list_sessions,list_projects,add_project,sync_to_obsidian}.py` — thin CLI wrappers

**Modified:**
- `/Users/alex/A/SessionManager/sessionskills.yaml` (add `link_project` to pipeline)
- `/Users/alex/A/SessionManager/sessions/record.py` (add `canonical_project` to the allowed `classification` keys doc-comment; no schema change)
- `/Users/alex/A/SessionManager/scripts/sm-tui.py` (new Projects view)
- `/Users/alex/A/SessionManager/sessions/review_tui.py` (handle `unlinked_project` kind)
- `/Users/alex/SD.agents/skills/work-atoms/classify.py` (prefer canonical over own LLM call)

## Verification

```bash
# 1. Registry loads cleanly
python3 -c "from sessions.projects import load_registry; print(len(load_registry()))"  # ≥ 20

# 2. All current records get linked (or flagged)
sm-pipeline run link_project
sqlite3 ~/.sessionskills/store.sqlite <<'SQL'
SELECT json_extract(json,'$.classification.canonical_project') AS proj,
       COUNT(*) FROM records GROUP BY proj ORDER BY 2 DESC;
SQL
# Expect: top rows are real project IDs; 'null' rows go into unlinked review.

# 3. Obsidian project page has session list
cat ~/_/Projects/SessionSkills.md | grep -c "^- "  # > 0

# 4. Fresh session auto-links
# - Run a short Claude Code session in ~/RAN/AI/SessionManager/
# - Wait for ingest; then:
sqlite3 ~/.sessionskills/store.sqlite \
  "SELECT json_extract(json,'$.classification.canonical_project')
   FROM records ORDER BY first_seen DESC LIMIT 1"
# Expect: 'sessionskills' without manual intervention.
```

## Dependencies

- **Track 1** already populates `topic_slug` (needed for alias matching) and `work_atom_project` (one input signal). Safe to run after Track 1's classify stage.
- **Track 3** can populate `claude_code_slugs` entries for cross-host sessions that come through preservator. Track 2 reads — doesn't block Track 3.

## Out of scope

- New Obsidian plugin — use plain markdown generation.
- Automatic project-page creation — if a registry entry has no `obsidian_page`, link_project stage logs but doesn't create.
- Historical re-classification of the 3000+ already-deposited Langfuse traces — one-off backfill script can do it later.
