# Xsolla — Claude Code Plugin Marketplace

**v0.0.1** — A plugin marketplace for Claude Code and Cowork. Meta-skills, reusable agents, MCP connections, and nested skill hierarchies — packaged as installable plugins.

[![organize](https://img.shields.io/badge/plugin-organize-green?style=flat-square)](#organize)
[![work](https://img.shields.io/badge/plugin-work-blue?style=flat-square)](#work)
[![search](https://img.shields.io/badge/plugin-search-orange?style=flat-square)](#search)
[![manage](https://img.shields.io/badge/plugin-manage-red?style=flat-square)](#manage)
[![shurick-start](https://img.shields.io/badge/plugin-shurick--start-purple?style=flat-square)](#shurick-start)

## Quick Start

```bash
# Add the marketplace
/plugin marketplace add xsolla/claude-plugin-marketplace

# Browse available plugins
/plugin marketplace list xsolla

# Install a plugin
/plugin install work@xsolla
```

In Cowork, use the plugin manager UI or ask Claude to install a plugin by name.

---

## Core Concepts

### Plugins

A **plugin** is the distribution unit — a `.plugin` zip containing skills, scripts, MCP server definitions, and commands. Each plugin has a `plugin.json` manifest and lives under `plugins/<name>/`.

```
plugin-name/
├── .claude-plugin/plugin.json    # Manifest (name, version, description)
├── skills/                       # Skill definitions (SKILL.md files)
├── scripts/                      # Bundled Python/Shell implementations
├── commands/                     # Slash commands (.md files)
├── .mcp.json                     # MCP server definitions (optional)
└── README.md
```

### Skills

A **skill** is defined by a single `SKILL.md` file with YAML frontmatter. It is the atomic unit of capability — a set of instructions that tells Claude how to accomplish a specific task.

```yaml
---
name: work-m365
description: "Microsoft 365: Mail, Calendar, Teams, Files, Tasks"
user-invocable: true
---
```

The description doubles as the trigger — Claude reads it to decide when to invoke the skill.

### Meta-Skills (Routing & Dispatch)

A **meta-skill** is a skill that performs no work itself. It acts as a router: its `SKILL.md` contains a routing table that tells Claude which sub-skill to invoke based on context.

Example — the `work` meta-skill routes like this:

| Request mentions | Routes to |
|---|---|
| Outlook, Exchange, Teams, OneDrive | `work-m365` |
| Gmail, Google Drive | `work-google` |
| Slack messages, channels | `work-slack` (MCP) |
| Jira issues, Confluence pages | `work-jira` (MCP) |
| Ambiguous "email" | Asks the user |

There is no hardcoded dispatcher. Routing is natural language in markdown — Claude reads the routing section and makes a judgment call. This makes the system flexible and context-aware without requiring code changes.

### Nesting & Hierarchy

Skills nest up to two levels:

```
Meta-skill (router)
└── Concrete skill (does work)
    └── Nested workflow (sub-task within a skill)
```

Real example:

```
work/                              ← meta-skill (routes by platform)
├── work-m365/                     ← concrete skill (Graph API)
├── work-slack/                    ← concrete skill (Slack MCP)
└── work-jira/                     ← concrete skill (Atlassian MCP)
    ├── triage-issue/              ← nested workflow
    ├── capture-tasks-from-meeting-notes/
    ├── generate-status-report/
    ├── spec-to-backlog/
    └── search-company-knowledge/
```

Deeper nesting is intentionally avoided to keep the mental model simple.

### Connections (MCP Servers)

Plugins connect to external services via **MCP servers** defined in `.mcp.json`:

| Connection | Protocol | Auth |
|---|---|---|
| Slack | `https://mcp.slack.com/mcp` | OAuth |
| Atlassian (Jira/Confluence) | `https://mcp.atlassian.com/v1/mcp` | Browser auth |
| voidtools Everything | Local `uvx` process | None |
| Microsoft Graph API | CLI script (`m365.py`) | Azure Key Vault client credentials |

MCP connections provide tools that skills can use. CLI scripts provide capabilities where no MCP server exists.

### Reusable Agents

Skills and their scripts are designed to be reusable across plugins. The `manage-skills` skill provides a full lifecycle for plugin development: review feedback, patch, test, rebuild `.plugin` zip, deploy. Version tracking is enforced — every change bumps the patch version in both `plugin.json` and `SKILL.md` frontmatter.

---

## Using Cowork & Dispatch

### Cowork Mode

In Cowork (Claude desktop app), plugins are installed via the UI or by asking Claude. Once installed, skills appear in Claude's available skill list and are triggered automatically by keywords in your request.

**How dispatch works**: When you say "check my Jira backlog", Claude matches your request against installed skill descriptions, loads the `work` meta-skill, reads its routing table, and dispatches to `work-jira`. No slash commands needed — just describe what you want.

**Explicit invocation** is also supported:
```
/skill work-jira
/skill search-m365
/skill organize
```

### Claude Code CLI

Same plugins work in Claude Code. Install via `/plugin install`, invoke via `/skill` or let Claude auto-dispatch based on your prompt.

---

## Available Plugins (5)

### organize
File organizer with sub-skill discovery. Scans a folder, runs each sub-skill in `--scan` (dry-run) mode, presents a combined plan, waits for approval.

| Sub-skill | Description |
|---|---|
| `organize-arxiv` | Identify arXiv PDFs, fetch metadata, rename, move to library |
| `medical-scan-obsidian` | Convert medical scans into bilingual EN/RU Obsidian vault |

### work
Workplace productivity hub. Routes to the right platform based on your request.

| Sub-skill | Description |
|---|---|
| `work-m365` | Mail, Calendar, Teams Chat, Files, Tasks, Contacts, OneNote, Presence |
| `work-google` | Gmail, Google Drive |
| `work-slack` | Messaging, search, threads, canvases (Slack MCP) |
| `work-jira` | Issues, epics, sprints, Confluence docs (Atlassian MCP) — includes 5 nested workflows |

### search
Cross-platform search. Routes by target: local files, M365, or Slack.

| Sub-skill | Description |
|---|---|
| `search-everything` | voidtools Everything MCP — 16 tools, Windows-only |
| `search-m365` | Unified search across emails, files, events, chat, SharePoint |
| `search-slack` | Messages, channels, files, people |

### manage
Administration and lifecycle management.

| Sub-skill | Description |
|---|---|
| `manage-sessions` | Claude Code sessions: sync, list, resume, rename, cleanup |
| `manage-skills` | Plugin skills: review, patch, test, rebuild, deploy |
| `manage-m365` | M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security |

### shurick-start
CEO workspace — 51 skills covering employee rewards, Neuronet knowledge graph, Quest Platform, Neo4j, Cloud Run, mini-apps, Atlassian, Slack, Gmail, GCP, and multi-agent orchestration.

---

## Contributing

**Wanted: contributors for these integrations:**

- **Okta / Auth0** — Identity & access management skill (SSO, user provisioning, MFA policies, audit logs). If your org uses Okta, we'd love help building an `work-okta` or `manage-okta` sub-skill.
- **GCP testing** — The `shurick-start` plugin includes GCP / Cloud Run skills that need testing across different project configurations and IAM setups. If you have a GCP sandbox, please help validate.

To contribute a new skill:

1. Fork the repo
2. Create `plugins/<parent>/skills/<your-skill>/SKILL.md` with frontmatter
3. Add implementation scripts under `plugins/<parent>/scripts/`
4. Update `plugin.json` and `marketplace.json`
5. Open a PR

See `plugins/manage/skills/manage-skills/references/plugin-structure.md` for the full spec.

---

## Earlier Projects

This repository evolved from a series of earlier experiments in agentic tooling. For historical context:

| Project | Status | Description |
|---|---|---|
| **DA (ДА)** | Active — see [DA/](DA/) | Multi-agent CLI/TUI built on Anthropic SDK. Sessions, tools, remote hosts. |
| **Gadya (Гадя)** | Active — see [Gadya/](Gadya/) | Voice-first iOS/Android assistant (React Native / Expo) |
| ~~AGENTS.md pattern~~ | ~~Superseded by plugins~~ | ~~Single markdown file to control agent behavior per repo~~ |
| ~~Multi-agent orchestration~~ | ~~Superseded by meta-skills~~ | ~~Specialized subagents (changelog, docs, archive, validation, push) coordinated by parent agent~~ |
| ~~Mistake-driven improvement~~ | ~~Folded into manage-skills~~ | ~~Agents log mistakes; patterns feed back into instructions~~ |
| ~~DAPY CLI~~ | ~~Abandoned~~ | ~~LangChain/LangGraph CLI for agentic workflows~~ |
| ~~Agent swarm~~ | ~~Abandoned~~ | ~~ORCHESTRATOR.md-based multi-agent experiments~~ |
| ~~Subagent definitions~~ | ~~Replaced by skills/~~ | ~~Standalone .md agent specs in agents/ directory~~ |
| ~~Archive templates~~ | ~~Inlined~~ | ~~README, AGENTS, archive templates in archive/templates/~~ |

---

```
Xsolla — Claude Code Plugin Marketplace
v0.0.1
```

---

```
      ░████             ░██        ░██░██       ░███                                        ░██
    ░██  ░██            ░██           ░██      ░██░██                                       ░██
   ░██   ░██  ░███████  ░████████  ░██░██     ░██  ░██   ░████████  ░███████  ░████████  ░████████
  ░██    ░██ ░██    ░██ ░██    ░██ ░██░██    ░█████████ ░██    ░██ ░██    ░██ ░██    ░██    ░██
  ░██    ░██ ░█████████ ░██    ░██ ░██░██    ░██    ░██ ░██    ░██ ░█████████ ░██    ░██    ░██
  ░██    ░██ ░██        ░███   ░██ ░██░██    ░██    ░██ ░██   ░███ ░██        ░██    ░██    ░██
  ░█████████  ░███████  ░██░█████  ░██░██    ░██    ░██  ░█████░██  ░███████  ░██    ░██     ░████
░██        ░██                                                 ░██
Агент который только говорит ДА                          ░███████
```
Multiple workstations, dozens of projects, across hundereds of instances of Claude Code/Gemini/Codex. No problem.
Tired of CLI agents asking for permissions in Approve All mode, but afraid to go YOLO. No problem.

[![DA Build](https://github.com/akarelin/AGENTS.md/actions/workflows/da-build.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/da-build.yml) [![DA version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=da-v*&label=DA&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=da)<br>
[![Gadya Build](https://github.com/akarelin/AGENTS.md/actions/workflows/gadya-android.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/gadya-android.yml) [![Gadya version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=gadya-v*&label=Gadya&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=gadya)<br>
[![DAPY Build](https://github.com/akarelin/AGENTS.md/actions/workflows/dapy-build.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/dapy-build.yml) [![DAPY version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=dapy-v*&label=DAPY&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=dapy)<br>

An unfinished, evolving collection of everything agentic — prompt engineering patterns, autonomous agent instructions, multi-agent orchestration experiments, and tooling. This is a working dumping ground, not a polished framework.

## Table of Contents
- [In development](#in-development)
  - [DA (ДА)](#da-да)
  - [Gadya (Гадя)](#gadya-гадя)
- [No longer developed](#no-longer-developed)
  - [DAPY CLI](#dapy-cli)
- [What's where](#whats-where)

## In development
- **DA (ДА)**: Personal multi-agent CLI and TUI built directly on the Anthropic SDK. Multi-session support, tool execution, Claude session browsing, and remote host management.
- **Gadya (Гадя)**: A voice-first iOS/Android mobile assistant built with React Native / Expo and TypeScript. Designed for hands-free, one-handed interaction with LLMs — speak a question, get an AI answer read aloud, and optionally save or search personal notes via voice.
- ~~**DAPY CLI**: A more ambitious attempt to wrap the whole workflow into a LangChain-based CLI tool~~

---

# DA (ДА) - Агент который только говорит ДА

Superagent to manage cli coding agents, projects, tools. Makes Claude Code compliant (not asking too many questions).

## Features
### Session Management
Browse sessions across multiple machines. 
<p align="center"><img src="docs/sessions-claude.png" width="800" alt="Sessions — Claude session tree with detail panel"></p>

Delete, rename, move and merge.

<p align="center"><img src="docs/sessions-delete.png" width="800" alt="Sessions — delete confirmation dialog"></p>

The tree expands to show full session history with timestamps. Selected sessions show recent conversation messages and available actions in the detail panel.

<p align="center"><img src="docs/sessions-detail.png" width="800" alt="Sessions — expanded tree with session detail and recent messages"></p>

### Obsidian Integration

Obsidian vault integrated. Used to manage Projects - an abstraction above sessions.

<p align="center"><img src="docs/obsidian.png" width="800" alt="Obsidian — vault browser with folder tree and note preview"></p>

### Editor

A tree-based browser for tools, agents, and YAML config files. Da can be fully configured from its own ui or using its own chat interface.

<p align="center"><img src="docs/config.png" width="800" alt="Config Editor — tool and agent tree with YAML config preview"></p>

### REPL
<p align="center"><img src="docs/da-chat.png" width="800" alt="DA Chat — agent conversation view with ASCII banner and tab bar"></p>


### CLI Commands

| Command | Description |
|---------|-------------|
| `da` | Launch full TUI (default) |
| `da rich` | Rich TUI — 5-tab layout with Projects, Chat, Sessions, Obsidian, Config |
| `da tui` | Sidebar TUI — session list + conversation layout |
| `da repl` | Interactive REPL with slash commands and tab completion |
| `da manage` | Session manager — browse, rename, copy, move, delete |
| `da ask "<query>"` | One-shot query to the orchestrator agent |
| `da sessions` | List recent sessions |
| `da resume <id>` | Resume a previous session |
| `da analyze` | Analyze Claude Code conversation history |
| `da diag` | Show diagnostic info (model, hosts, tools) |
| `da next` | Read 2Do.md, ROADMAP.md, git status — recommend what to do |
| `da close` | Close session — update 2Do.md, document progress |
| `da document` | Generate CHANGELOG.md from git diff |
| `da push [msg]` | Commit and push with changelog verification |

Flags: `--model / -m` (model override), `--debug`, `--config / -c`.

### Tools (23)

| Category | Tools |
|----------|-------|
| Shell | `shell_exec` — run arbitrary commands |
| Git | `git_status`, `git_diff`, `git_log`, `git_commit_push` |
| Docker | `docker_ps`, `docker_logs`, `docker_exec`, `docker_compose` |
| SSH | `ssh_exec`, `ssh_batch` (parallel multi-host) |
| Files | `read_file`, `write_file`, `list_dir`, `find_files`, `delete_file`, `copy_file`, `move_file`, `edit_file` |
| Search | `grep_search`, `glob_find` |
| Sessions | `list_sessions`, `get_session`, `delete_session` |

### REPL Shortcuts

Slash commands in the REPL and TUI input:

| Command | Action |
|---------|--------|
| `/model [opus\|sonnet\|haiku]` | Switch model or show current |
| `/tools` | List all available tools |
| `/hosts` | Show configured remote hosts |
| `/git [status\|diff\|log\|commit\|push]` | Git operations |
| `/docker [ps\|logs\|exec\|up\|down]` | Docker operations |
| `/ssh <host> [cmd]` | Execute on remote host |
| `/grep <pattern>`, `/find <glob>` | Search files |
| `/cat <path>`, `/ls [path]` | Read file / list directory |
| `/sessions`, `/switch <id>`, `/delete [id]` | Session management |
| `/compact` | Summarize and trim conversation context |
| `!<command>` | Direct shell execution |

Tab completion for commands, model names, hosts, git/docker subcommands, and file paths.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1`–`F5` | Switch views: Projects, Chat, Sessions, Obsidian, Config |
| `Ctrl+N` | New session |
| `Ctrl+Q` | Quit |
| `Esc` | Back / close editor |

---

See [Gadya/README.md](Gadya/README.md) for full documentation.

---


## What's where

```
.
├── AGENTS.md                  → Master instructions for autonomous agents (Claude, Gemini, etc.)
├── CLAUDE.md / GEMINI.md      → Per-LLM instruction pointers
│
├── DA/                       → Personal multi-agent CLI/TUI (Anthropic SDK)
│   ├── da/                   → Python package (cli, tui, agents, tools)
│   ├── scripts/              → Install script
│   └── config.yaml           → Model, hosts, session settings
│
├── DAPY/                → LangChain/LangGraph CLI for agentic workflows
│   ├── dapy/            → Python package (orchestrator, tools, middleware)
│   ├── deployment/            → Docker, GCP, LangChain Cloud configs
│   └── tools/                 → LLM log ingestion and querying
│
├── Gadya/                     → Voice-first mobile assistant (React Native / Expo)
│   ├── app/                   → Expo app screens and navigation
│   ├── server/                → Express + tRPC backend with LangChain chains
│   ├── hooks/                 → Voice system, continuous listening
│   └── services/              → LLM integration, notes, storage
│
├── agents/                    → Moved to kar1024/archive-A (history preserved)
│
└── archive/                   → Moved to kar1024/archive-A (history preserved)
```

## No longer developed
- **AGENTS.md as a pattern**: A single markdown file that tells any LLM agent how to behave in a repository — session management, git workflow, mistake tracking, changelog conventions
- **Multi-agent orchestration**: Experiments with specialized subagents (changelog, docs, archive, validation, push) coordinated by a parent knowledge-management agent
- **Mistake-driven improvement**: Agents log their own mistakes; those patterns feed back into better instructions


## DAPY CLI

See [DAPY/README.md](DAPY/README.md) for full documentation.

---


```                          
      ░████                     ░███    
    ░██  ░██                   ░██░██                      
   ░██   ░██                  ░██  ░██  
  ░██    ░██       _    _ _  ░█████████               _   
  ░██    ░██   ___| |__(_) | ░██    ░██  __ _ ___ _ _| |_ 
  ░██    ░██  / -_) '_ \ | | ░██    ░██ / _` / -_) ' \  _|
  ░█████████  \___|_.__/_|_| ░██    ░██ \__, \___|_||_\__|
░██        ░██                           |___/             
Агент который только говорит ДА
```
