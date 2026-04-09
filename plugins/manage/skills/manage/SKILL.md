---
name: manage
description: >
  This skill should be used when the user asks to manage Claude Code sessions
  (list, resume, sync, rename, cleanup) or manage plugins/skills
  (patch, test, deploy, review feedback).
---

# Manage

Session and skill management.

## Sub-skills

| Sub-skill | Description |
|-----------|-------------|
| session | Claude Code sessions: sync, list, resume, rename, cleanup |
| skill | Plugin skills: review feedback, patch, test, rebuild, deploy |

## Routing

- **"list sessions", "resume session", "sync sessions"** → session
- **"fix skill", "deploy plugin", "patch skill"** → skill
- **M365/GCP admin** → use `administer` plugin instead
