# SessionManager + SessionSkills

Two layers in one repo:

- **SessionManager** (`scripts/`, `bin/sm*`): original Langfuse deposit CLI + TUI.
  Ships Claude Code session JSONLs to Langfuse on SessionEnd.
- **SessionSkills** (`sessions/`, `bin/sm-pipeline`, `bin/sm-review`): unified
  local-LLM pipeline owning the full session lifecycle (ingest → merge → name →
  analyze → write_to_memory → cluster → classify → review → prune → archive).
  See [`docs/sessionskills-ADR.md`](docs/sessionskills-ADR.md) and
  [vault project page](../../_/Projects/SessionSkills.md).

## Architecture

```
SessionSkills (local-first, Ollama)            SessionManager (Langfuse)
────────────────────────────────────────       ───────────────────────────────
~/.claude/projects/*.jsonl      ┐              SessionEnd hook
~/.openclaw/agents/*/sessions/  ├─► ingest     ──► session-to-langfuse.py
langfuse.karelin.ai API (pull)  ┘      │                │
                                       ▼                ▼
                        ~/.sessionskills/store.sqlite   langfuse.karelin.ai
                                       │                (trace upsert, OTEL)
                                       ▼
                        merge → name → analyze → write_to_memory →
                        cluster → classify → review → prune → archive
                                       │
                                       ▼
                        ~/.openclaw/memory/<agent>.sqlite  (chunks + FTS)
                        ~/_/{internals}/session-intel/analyzed/*.md
                        ~/.openclaw/agents/*/sessions-named/*  (symlinks)
```

## Setup

- **Langfuse:** Self-hosted on `34.162.201.120` (alex.xsolla.com)
- **SSL:** Let's Encrypt cert via certbot (auto-renew)
- **Python venv:** `.venv/` (langfuse SDK 4.0.6)
- **CLI:** `scripts/lf` → symlinked to `/usr/local/bin/lf`
- **Hook:** `scripts/session-to-langfuse.py` → symlinked from `~/.claude/hooks/`

## SessionSkills CLI

```bash
sm-pipeline doctor                          # health: ollama + store
sm-pipeline stats                           # records by state

sm-pipeline run ingest                      # scan filesystem → canonical records
sm-pipeline run merge                       # stitch .reset/.deleted/topic chains
sm-pipeline run name                        # LLM slug → parallel symlink dir
sm-pipeline run analyze                     # session-intel summary via local Ollama
sm-pipeline run write_to_memory             # chunks → OpenClaw agent memory SQLite
sm-pipeline run cluster                     # sentence-transformers themes
sm-pipeline run classify                    # work-atoms project assignment
sm-pipeline run review                      # collect low-confidence → review queue
sm-pipeline run prune                       # move to .trash/<ts>/ with manifest
sm-pipeline run archive                     # tar.gz old sessions + side JSON

sm-pipeline run default                     # whole pipeline (from sessionskills.yaml)
sm-pipeline run nightly                     # cluster + classify only
sm-pipeline run weekly                      # prune + archive only

sm-review                                   # interactive HITL queue
sm-review --notify                          # count-only (for launchd reminder)
```

Flags: `--dry-run`, `--force`, `--limit N`, `--source {claude-code|openclaw|langfuse}`,
`--source-id <uuid>`.

### One-time setup

```bash
brew install ollama && brew services start ollama
ollama pull qwen3:8b            # ~5 GB
ollama pull nomic-embed-text    # ~270 MB
sm-pipeline doctor              # verify
```

### Launchd schedules (user-approved install)

```bash
./launchd/install.sh
```

Installs 5 agents:
- `ai.sessionskills.ingest` — every 15 min (ingest + merge)
- `ai.sessionskills.analyze` — hourly :05 (name + analyze + write_to_memory, limit 50)
- `ai.sessionskills.nightly` — 01:15 (cluster + classify)
- `ai.sessionskills.weekly`  — Sun 03:00 (prune + archive)
- `ai.sessionskills.review-reminder` — 09:00 (notify if queue non-empty)

## SessionManager (legacy Langfuse CLI)

```bash
# Sessions
lf resume [search]                    # list & resume (interactive)
lf rename <target> <name> [--tag t]   # rename + tag
lf merge <t1> <t2> [--name n]         # merge under shared session
lf archive <target> [--undo]          # archive/unarchive
lf deposit <file|id|dir|all>          # push local JSONL → Langfuse
lf deposit-all                        # bulk push everything
# dir form lets preservator hand a staged pull tree (before RAR):
lf deposit /mnt/d/Cache/batch_<ts>/<host>/llms/

# Projects
lf projects [name]                    # list by project
lf combine <project>                  # group project sessions
lf assoc <target> <project>           # associate session → project
```

**Targets:** `last` | `#N` (1-indexed) | partial session/trace ID

## Claude Code Hook

`SessionEnd` hook in `~/.claude/settings.json` auto-deposits every session:

```json
{
  "hooks": {
    "SessionEnd": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/hooks/.venv/bin/python3 ~/.claude/hooks/session-to-langfuse.py",
        "timeout": 30000
      }]
    }]
  }
}
```

## Files

```
scripts/
  lf                          # Main CLI
  session-to-langfuse.py      # JSONL parser + Langfuse depositor
  lf-resume                   # Legacy standalone (superseded)
  lf-rename                   # Legacy standalone (superseded)
.venv/                        # Python venv with langfuse SDK
```

## Langfuse API Notes

- Tags are **additive** via ingestion API — cannot remove tags through `trace-create` upsert
- Tag removal (unarchive) goes through ClickHouse directly via SSH
- ClickHouse table: `traces` (ReplacingMergeTree), requires `OPTIMIZE TABLE traces FINAL` after ALTER
- List API has ~2-5s eventual consistency lag
