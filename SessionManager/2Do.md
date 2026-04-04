# SessionManager — 2Do

## State (2026-04-03)

### What Exists

**Infrastructure:**
- Langfuse v3 at https://langfuse.karelin.ai (Portainer stack, host Postgres, ClickHouse, Minio, Redis)
- Claude Code SessionEnd hook auto-deposits to Langfuse
- DNS A record for langfuse.karelin.ai, Let's Encrypt cert with auto-renew
- Repo: github.com/akarelin/SessionManager

**CLI Tools (both alex-mac and alex-vm):**
- `sm` — remote session management (resume, rename, merge, archive, deposit, projects, assoc, local)
- `sm-local` — interactive local session cleanup/merge/LLM-naming: scan→propose→act
- `sm-tui` — full Textual TUI with split panels, detail view, bulk deposit
- `sm-app` — gppu.tui TUILauncher top-level menu
- `sm-map` — user-provided session/project map navigator with sync
- `sm-import` — ChatGPT and Claude.ai export importer

**Core Modules:**
- `thread.py` — Thread/Chat linked chain abstraction (merge, prune, JSONL conversion)
- `store.py` — FolderStore: shared-folder session store (no server needed)
- `importers.py` — ChatGPT/Claude.ai export → JSONL conversion
- `session-to-langfuse.py` — JSONL parser + Langfuse deposit (Claude Code hook)

**Discovery:**
- `discovery_rules.yaml` — preservator-style YAML rules
- Finds: Claude Code, Claude Code Vertex, Claude Desktop, OpenClaw, Codex, Continue, Cursor, imported exports
- 149 sessions discovered locally (58.8M), 161 on server

**Design Docs:**
- `docs/schema.sql` — PostgreSQL schema for multi-user session management
- `docs/SCHEMA.md` — schema overview
- `docs/folder-structure.md` — shared-folder store design
- `sm-map.yaml.example` — user map config template

### What Works End-to-End
- [x] Claude Code session → auto-deposit to Langfuse on session close
- [x] `sm resume` — list remote sessions, pick one, `claude --resume <id>`
- [x] `sm rename` / `sm archive` — update traces in Langfuse
- [x] `sm deposit <file>` / `sm deposit-all` — push local JSONL to Langfuse
- [x] `sm-local` — interactive scan, propose cleanup, LLM naming via Vertex Claude
- [x] `sm-import chatgpt/claude <export.zip>` — import web UI exports
- [x] Session discovery via preservator-style rules
- [x] `sm-app` — top-level TUI launcher

### What's Partially Done
- [ ] **Folder store** — `store.py` written but not wired into CLI commands
- [ ] **Thread abstraction** — `thread.py` written, tested, but not used by sm-local or sm-tui yet
- [ ] **sm-map** — works but no one has created an sm-map.yaml yet
- [ ] **PostgreSQL schema** — designed but not created on any server
- [ ] **OpenClaw → Langfuse** — deposit script works but no auto-hook (only Claude Code has SessionEnd)
- [ ] **Bulk backfill** — only 1 session deposited to Langfuse (test), 149+ pending

## TODO

### High Priority
- [ ] Create sm-map.yaml for alex (declare all sources, projects, sync targets)
- [ ] Bulk backfill all 149 local + 161 server sessions to Langfuse
- [ ] Wire Thread abstraction into sm-local (replace raw JSONL manipulation)
- [ ] Wire FolderStore into sm commands (sm deposit → also writes to folder store)
- [ ] Create PostgreSQL database on host (apply schema.sql)

### Medium Priority
- [ ] OpenClaw session hook — auto-deposit on session end (needs OpenClaw plugin or cron)
- [ ] Codex session watcher (when Codex gets used)
- [ ] Deploy Mem0 alongside Langfuse for semantic memory
- [ ] Glue layer: `/resume` pulls relevant memories as context injection
- [ ] Create Langfuse projects matching real projects (neuronet, tool-catalog, greenjosh, etc.)
- [ ] sm-tui: integrate Tree widget from DA for hierarchical browsing
- [ ] sm-tui: add command input bar from DA session_manager
- [ ] Cost tracking — estimate USD per session from token counts × model pricing

### Low Priority
- [ ] Content-based exhaustive discovery (scan all drives for LLM logs by content patterns)
- [ ] Multi-machine sync (pull sessions from server, push to Langfuse)
- [ ] Session diff — compare two sessions
- [ ] Session search — full-text search across all session content
- [ ] pgvector semantic search on session content
- [ ] Web UI for session browsing (beyond Langfuse's built-in)
- [ ] Publish as pip package

### Integration Points
- **DA (AGENTS.md):** DA has its own session.py/session_manager.py. SM is standalone. DA can `from da.session import SessionStore` for DA sessions; SM handles everything else. Future: DA imports SM's Thread/FolderStore when needed.
- **Preservator:** SM uses same discovery_rules.yaml format. Preservator's `llm_folders` rule already collects `.claude`, `.codex` etc. SM could be a preservator job_group.
- **OpenClaw:** SessionEnd hook equivalent needed. Could be a cron job or OpenClaw skill that watches session files.
- **Langfuse:** SM is the primary client. All session data flows through SM → Langfuse. Langfuse is the viewer, SM is the manager.
