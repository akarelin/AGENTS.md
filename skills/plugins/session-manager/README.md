# session-manager

Manage Claude Code session folders across repos and hosts.

## Installation

```
/plugin install session-manager@akarelin-skills
```

Requires: Python 3

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Sync current session |
| `sync-all` | Sync all sessions with checkpoint message |
| `list` | List all sessions |
| `list --current` | List sessions for current repo |
| `resume <name>` | Print repo path for a session |
| `delete-empty` | Preview empty session cleanup |
| `delete-empty --apply` | Delete empty sessions |
| `rename <old> <new>` | Preview session rename |
| `rename <old> <new> --apply` | Apply session rename |
