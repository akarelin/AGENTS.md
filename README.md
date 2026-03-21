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
├── AGENTS_mistakes.md         → Log of agent mistakes and lessons learned
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
├── agents/                    → Specialized subagent definitions (legacy)
│   ├── knowledge-management-agent.md
│   ├── changelog-agent.md
│   ├── docs-agent.md
│   ├── archive-agent.md
│   ├── validation-agent.md
│   ├── push-agent.md
│   └── mistake-review-agent.md
│
├── agent-swarm/               → Multi-agent orchestration experiments (legacy)
│   ├── ORCHESTRATOR.md
│   ├── claude-code-orchestration-plan.md
│   └── agents/                → Alternative agent definitions
│
└── archive/                   → Previous iterations, old plans, templates, guides
    ├── INSTRUCTIONS_CORE.md, INSTRUCTIONS_EXPERIMENTAL.md
    ├── ROADMAP.md, 2Do.md
    ├── templates/             → README, AGENTS, archive templates
    ├── plans/                 → Subagent project plans
    └── guides/                → Best practices (archiving, etc.)
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
