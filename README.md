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

[![DA Build](https://github.com/akarelin/AGENTS.md/actions/workflows/da-build.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/da-build.yml) [![DA version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=da-v*&label=DA&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=da)
[![DAPY Build](https://github.com/akarelin/AGENTS.md/actions/workflows/dapy-build.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/dapy-build.yml) [![DAPY version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=dapy-v*&label=DAPY&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=dapy)
[![Gadya Build](https://github.com/akarelin/AGENTS.md/actions/workflows/gadya-android.yml/badge.svg)](https://github.com/akarelin/AGENTS.md/actions/workflows/gadya-android.yml) [![Gadya version](https://img.shields.io/github/v/release/akarelin/AGENTS.md?filter=gadya-v*&label=Gadya&color=blue&style=flat-square)](https://github.com/akarelin/AGENTS.md/releases?q=gadya)

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

# Gadya (Гадя)

A voice-first iOS/Android mobile assistant built with React Native / Expo and TypeScript. Designed for hands-free, one-handed interaction with LLMs — speak a question, get an AI answer read aloud, and optionally save or search personal notes via voice.
**Status:** All major features are implemented and checked complete.

### Core Capabilities

- **Continuous voice mode** — tap once to start; the app listens, transcribes, sends to AI, speaks the response via TTS, then auto-resumes listening. Stop with "stop", "стоп", "хватит", or "enough".
- **Dual LLM routing** — default model is Gemini 2.5 Flash; say "Ask Claude..." or "Клод,..." to route to Claude Sonnet 4 via Anthropic API.
- **Dictation mode** — record speech, transcribe, then rephrase with AI (formal / casual / concise / expanded) and save as a markdown note.
- **Obsidian integration** — reads `.md` files from Android external storage, searches them for context, and injects the top 3 matching notes into the AI prompt (RAG).
- **Background audio** — keeps listening while the app is backgrounded (iOS audio/voip/fetch/processing entitlements; Android foreground service with microphone).

### Screens

| Screen | Purpose |
|--------|---------|
| **Home** | Main voice interface — large mic button, conversation cards, mode toggle (Ask AI / Dictate) |
| **Dictate** | Dedicated dictation mode with rephrase and save-to-note |
| **Notes** | Browse and search local markdown notes |
| **Note Detail** | View and edit a single note |
| **Settings** | App configuration |

### LangChain Chains (Backend)

The backend (`server/services/langchain.ts`) implements seven chains:

| Chain | Model | Purpose |
|-------|-------|---------|
| **Chat** | Gemini 2.5 Flash | Main conversational AI with conversation history and Obsidian context |
| **Claude** | Claude Sonnet 4 | On-demand Claude routing triggered by voice commands |
| **RAG** | Gemini 2.5 Flash | Answers questions grounded in personal notes, cites sources |
| **Rephrase** | Gemini 2.5 Flash | Rewrites dictated text in a chosen style |
| **Summarize** | Gemini 2.5 Flash | Summarizes notes at brief/medium/detailed length |
| **Intent Classifier** | Gemini 2.5 Flash | Detects voice command intent (ask_claude, search_notes, save_note, etc.) |
| **Search Query Extractor** | Gemini 2.5 Flash | Pulls search terms from natural language |

### Voice System

The continuous voice mode (`hooks/use-continuous-voice.ts`) is a state machine:

```
idle → listening → processing → speaking → (auto-resume) → listening
                                         → (manual) → idle
```

- Uses `@react-native-voice/voice` (native) with Web Speech API fallback
- Partial results displayed while user speaks
- Error recovery: auto-restarts on "No match" and "Client side" errors
- App backgrounding: pauses/resumes gracefully

### Technology Stack

Expo ~54, React Native 0.81, React 19, TypeScript. Backend: Express + tRPC v11, Drizzle ORM (MySQL/TiDB), S3 storage. Voice: `@react-native-voice/voice`, `expo-speech` (TTS), `expo-av` (audio recording). LLM: `@langchain/openai`, `@langchain/anthropic`, `langchain` (TypeScript).

### Build & CI

GitHub Actions workflow (`.github/workflows/build-android.yml`) for automated Android builds. App works without authentication (login requirement removed).

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

A production-ready personal knowledge management system and agentic workflow tool built with LangChain 1.0 and LangGraph 1.0 (Python). It reimplements the original cascading markdown-based subagents and tools as native LangChain tools and LangGraph workflows — preserving the markdown-driven philosophy while adding enterprise-grade observability, persistence, and deployment options.

**Status:** Code exists but has not been tested or deployed. Everything awaits user approval and iterative validation.

### CLI Commands

| Command | Description |
|---------|-------------|
| `dapy ask "..."` | Execute any query via the main agent |
| `dapy next` | Analyze 2Do.md, ROADMAP.md, git status — recommend what to do next |
| `dapy close` | Close session: update 2Do.md, document mistakes, archive work |
| `dapy document` | Auto-generate CHANGELOG.md from git diff |
| `dapy push "msg"` | Commit + push with changelog verification |
| `dapy daemon` | Run as background HTTP daemon |
| `dapy inspect` | Show recent executions and snapshots |
| `dapy feedback submit` | Submit feedback (bug/feature/etc.) |
| `dapy export-debug` | Package debug info for remote inspection |
| `dapy diag` | Diagnostic info: config, env vars, git status |

Advanced flags: `--breakpoint <tool>` (pause at any tool), `--no-snapshot`, `--approve-all`, `--debug`.

### 10 LangChain Tools

All tools migrated from the original markdown-based subagents:

| Tool | Source Agent | Purpose |
|------|-------------|---------|
| `changelog_tool` | changelog-agent.md | Manages CHANGELOG.md (Keep a Changelog format) |
| `archive_tool` | archive-agent.md | Archives outdated code with inventory |
| `mistake_processor_tool` | mistake-review-agent.md | Documents mistakes for learning |
| `validation_tool` | validation-agent.md | Checks code/docs against standards |
| `git_push_tool` | git-operations.md | Commits and pushes with verification |
| `git_status_tool` | git-operations.md | Gets current git status |
| `git_diff_tool` | git-operations.md | Shows git diffs |
| `read_markdown_tool` | knowledge-base.md | Reads markdown with frontmatter |
| `search_markdown_tool` | knowledge-base.md | Searches across markdown files |
| `update_markdown_tool` | knowledge-base.md | Updates markdown content |

### 3 LangGraph Workflows

1. **Close Session** — Sequential state machine: analyze session → update todo → check mistakes → archive work → generate summary
2. **Document Changes** — Detects git diff, classifies changes (Added/Changed/Fixed/Removed), updates CHANGELOG.md
3. **What's Next** — Reads 2Do.md, ROADMAP.md, and git status to determine recommended next steps

### Middleware Stack

Each tool call passes through an ordered middleware pipeline:

```
Request → EnhancedLogging → Breakpoint → Snapshot → HumanInTheLoop → Tool Execution
```

- **EnhancedLogging** — captures timing for every tool call
- **Breakpoint** — pauses execution at configured tools with an interactive menu (continue / skip / abort / inspect / PDB)
- **Snapshot** — saves JSON state before/after each tool call to `./snapshots/`
- **HumanInTheLoop** — approval gates for destructive operations

### Observability

- **LangSmith tracing** — every execution traced (tool calls, model invocations, workflow transitions)
- **State snapshots** — JSON files saved before/after each tool call
- **Remote inspection API** — external agents can access snapshots and traces
- **Debug export** — `dapy export-debug` packages everything for remote troubleshooting

### Technology Stack

Python 3.11, LangChain >= 0.3.0, LangGraph >= 0.2.0, LangSmith >= 0.2.0, Click (CLI), Rich (terminal UI), GitPython, PyYAML. SQLite (local) or PostgreSQL (production) for state persistence.

### Deployment Options

1. **Local Docker Compose** — Hot reload, SQLite, volume-mounted repos
2. **GCP VM** — PostgreSQL, Nginx reverse proxy with SSL, automated deploy.sh
3. **LangChain Cloud** — Serverless, auto-scaling 1–5 instances (chosen option, not yet started)

### LLM Log Ingestion

Included tools (`DAPY/tools/`) import ChatGPT and Claude conversation exports into LangSmith datasets, then query them to detect patterns, generate test cases, and export golden examples for prompt optimization.

---

