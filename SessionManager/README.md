# SessionManager

CLI and hooks for centralized LLM session management via Langfuse.

## Architecture

```
Local JSONL (Claude Code, OpenClaw, Codex)
    ↓ SessionEnd hook / manual deposit
Langfuse (https://langfuse.karelin.ai)
    ↑ lf CLI (list, rename, merge, archive, project ops)
```

## Setup

- **Langfuse:** Self-hosted on `34.162.201.120` (alex.xsolla.com)
- **SSL:** Let's Encrypt cert via certbot (auto-renew)
- **Python venv:** `.venv/` (langfuse SDK 4.0.6)
- **CLI:** `scripts/lf` → symlinked to `/usr/local/bin/lf`
- **Hook:** `scripts/session-to-langfuse.py` → symlinked from `~/.claude/hooks/`

## CLI Usage

```bash
# Sessions
lf resume [search]                    # list & resume (interactive)
lf rename <target> <name> [--tag t]   # rename + tag
lf merge <t1> <t2> [--name n]         # merge under shared session
lf archive <target> [--undo]          # archive/unarchive
lf deposit <file|id|all>              # push local JSONL → Langfuse
lf deposit-all                        # bulk push everything

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
