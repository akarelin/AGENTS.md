---
name: core
description: >
  Core agent primitives. Use when the agent needs to manage secrets,
  memorize/recall facts, manage sessions, manage skills, coordinate agents,
  or learn from feedback.
---

# Core

Foundational tools for agent self-management. These are primitives consumed by other plugins.

## Tools

| Tool | Scope | Description |
|------|-------|-------------|
| secrets | Azure Key Vault (`karelin`) | get, list, save, update — API keys, tokens, credentials |
| memory | my/team/project/company | Get, set, save — persist and recall facts, state |
| session | — | Sync, list, resume, rename, delete Claude Code sessions |
| skill | — | Patch, test, deploy skills |
| compose-agent | — | Create a managed agent from multiple existing agents/skills |
| learn | — | Learn from feedback and mistakes (stub) |

## Secrets

Secrets live in the `karelin` Azure Key Vault and are accessed via the `Karelin Keys` MCP server (`mcp.karelin.ai/keys`). Three tools, all routed here — not through `memory`:

| MCP tool | Use when |
|----------|----------|
| `secret_get(name)` | "what's the X key", "get the Y token", reading a stored credential |
| `secret_list()` | "what secrets do we have", browsing for the right name |
| `secret_set(name, value)` | Storing a fresh credential or rotating an existing one (idempotent — creates if absent, adds a new version if present; old versions stay in vault history) |

**Policy:** every credential generated during a task (SAS, account key, OAuth token, API key, PGP key) must be persisted via `secret_set` before the task is considered complete — terminal-only credentials are treated as lost. Naming is kebab-case with a service/purpose prefix matching existing vault conventions (`slack-*`, `msgraph-*`, `ssl-karelin-*`, etc.).

## Routing

- **"get/set secret", API keys, tokens, credentials** → secrets
- **"remember this", "save this", "where does X go"** → memory
- **"list sessions", "resume session", "sync"** → session
- **"fix skill", "deploy plugin", "patch"** → skill
- **"create agent", "combine agents", "compose agent"** → compose-agent
- **"I corrected you", mistakes, feedback** → learn
