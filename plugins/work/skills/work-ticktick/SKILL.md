---
name: work-ticktick
description: "Manage TickTick tasks and projects. Use when the user mentions: ticktick, tasks, to-do, todo, task list, create task, complete task, reminders, due date."
user-invocable: true
argument-hint: "<command> [subcommand] [options]"
allowed-tools:
  - Bash
  - Read
  - Skill(get-secret)
---

# /ticktick — TickTick Task Management

Manage TickTick tasks and projects via OAuth2 API.

Arguments passed: $ARGUMENTS

## Authentication

OAuth2 with client credentials. Tokens stored in `~/.openclaw/credentials/ticktick/config.json`.

**First-time setup:**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" auth --client-id <id> --client-secret <secret>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" auth --status
```

For headless servers, use `--manual` to paste the redirect URL.

## CLI Reference

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" <command> [options]
```

Always use `--json` for machine-readable output.

### Projects

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" lists --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" list "New Project" --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" list "Old Name" --update --new-name "New Name" --json
```

### Tasks

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" tasks --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" tasks --list "Work" --status pending --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" task "Buy groceries" --list "Personal" --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" task "Review PR" --list "Work" --priority high --due tomorrow --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" task "Meeting" --list "Work" --due "2026-04-15" --tag urgent --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" task "Buy groceries" --update --priority medium --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" complete "Buy groceries" --json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tt.py" abandon "Old task" --json
```

## Due Dates

`today`, `tomorrow`, `in 3 days`, `next monday`, or ISO date (`2026-04-15`).

## Priorities

`none`, `low`, `medium`, `high`

## Workflow

1. `lists --json` — get project names/IDs
2. `task "Title" --list "Project" --json` — create
3. `complete "Title" --json` — mark done

Use task IDs (8+ char hex from `--json` output) when names are ambiguous.

## Implementation Notes

- TickTick Open API v1 (https://developer.ticktick.com/api)
- Rate limits: 100/min, 300/5min — auto-retry with backoff
- Auto token refresh on expiry
- Requires `requests` Python package
