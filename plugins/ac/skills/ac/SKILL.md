---
name: ac
description: >
  Agentic Cognition router. Use when the agent needs to memorize/recall facts,
  search knowledge, manage sessions, manage skills, coordinate agents,
  or learn from feedback. Routes to the appropriate AC tool.
---

# AC — Agentic Cognition

Foundational tools for agent self-management. These are primitives consumed by other plugins.

## Tools

| Tool | Scope | Description |
|------|-------|-------------|
| memory | my/team/project/company | Get, set, save — persist and recall facts, secrets, state |
| search-knowledge | my/team/project/company | Search across providers (Obsidian, m365, Everything, Atlassian, Neo4j) |
| dex | — | Data exploration: Neo4j graph (Cypher) and relational DBs (SQL) |
| session | — | Sync, list, resume, rename, delete Claude Code sessions |
| skill | — | Patch, test, deploy skills |
| agent | — | Agent coordination (stub) |
| learn | — | Learn from feedback and mistakes (stub) |

## Routing

- **"remember this", "save this", "where does X go", secrets** → memory
- **"search for", "find", "look up"** → search-knowledge
- **"query database", "explore data", "cypher", "SQL"** → dex
- **"list sessions", "resume session", "sync"** → session
- **"fix skill", "deploy plugin", "patch"** → skill
- **agent coordination** → agent
- **"I corrected you", mistakes, feedback** → learn
