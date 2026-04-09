---
name: core
description: >
  Core agent primitives. Use when the agent needs to memorize/recall facts,
  manage sessions, manage skills, coordinate agents, or learn from feedback.
---

# Core

Foundational tools for agent self-management. These are primitives consumed by other plugins.

## Tools

| Tool | Scope | Description |
|------|-------|-------------|
| memory | my/team/project/company | Get, set, save — persist and recall facts, secrets, state |
| session | — | Sync, list, resume, rename, delete Claude Code sessions |
| skill | — | Patch, test, deploy skills |
| agent | — | Agent coordination (stub) |
| learn | — | Learn from feedback and mistakes (stub) |

## Routing

- **"remember this", "save this", "where does X go", secrets** → memory
- **"list sessions", "resume session", "sync"** → session
- **"fix skill", "deploy plugin", "patch"** → skill
- **agent coordination** → agent
- **"I corrected you", mistakes, feedback** → learn
