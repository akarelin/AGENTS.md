# DAPY - Deep Agents in PYthon

Production-ready personal knowledge management system built with LangChain and LangGraph.

DAPY reimplements the cascading markdown-based agent workflow into an observable, deployable system — preserving markdown-driven prompts while adding breakpoints, snapshots, human-in-the-loop controls, and durable state persistence.

## Quick Start

```bash
git clone https://github.com/akarelin/AGENTS.md.git
cd AGENTS.md/DAPY
pip install -e .

export LANGCHAIN_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here

dapy next
```

Or with Docker:

```bash
cp .env.example .env   # add your API keys
docker-compose up -d
docker-compose exec dapy-dev bash
dapy next
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `next` | Show what to work on | `dapy next` |
| `ask` | Execute a query | `dapy ask "Archive old code"` |
| `document` | Update CHANGELOG.md from git diff | `dapy document` |
| `push` | Commit and push with changelog check | `dapy push "Implemented X"` |
| `close` | End session, update 2Do.md | `dapy close` |
| `diag` | Show diagnostics | `dapy diag` |
| `version` | Show version | `dapy version` |

```bash
# Breakpoint on a specific tool
dapy ask "Archive old code" --breakpoint archive_tool

# Auto-approve all operations
dapy ask "Update changelog" --approve-all

# Debug mode
dapy --debug ask "What's next?"

# Custom config
dapy --config my-config.yaml ask "What's next?"
```

## Features

**Observability** — LangSmith tracing, state snapshots at every step, timing metrics, `dapy diag` for troubleshooting.

**Human-in-the-Loop** — Approval gates for critical operations (git push, archive). Interactive breakpoint controls: continue, skip, abort, inspect.

**Durable State** — SQLite for local dev, PostgreSQL for production. LangGraph checkpointing for multi-session workflows with recovery after interruptions.

**Deployment** — Local Docker Compose (dev), GCP VM with PostgreSQL/Nginx/SSL (prod), LangChain Cloud (serverless). See [deployment/README.md](deployment/README.md).

## Architecture

```
DAPY/
├── dapy/                          # Python package
│   ├── __init__.py
│   ├── cli.py                     # Click CLI
│   ├── orchestrator.py            # Agent creation
│   ├── config.py                  # Configuration
│   ├── observability.py           # LangSmith tracing, snapshots
│   ├── persistence.py             # State checkpointing
│   ├── inspect.py                 # State inspector
│   ├── inspector_service.py       # FastAPI inspector service
│   ├── feedback.py                # Feedback collection
│   ├── feedback_dashboard.py      # Feedback dashboard
│   ├── manus_feedback_agent.py    # Feedback agent
│   ├── debug_export.py            # Debug export utility
│   ├── middleware/
│   │   ├── snapshot.py            # State capture
│   │   ├── breakpoint.py          # Interactive debugging
│   │   └── logging.py             # Enhanced logging
│   ├── tools/
│   │   ├── changelog.py           # CHANGELOG.md management
│   │   ├── archive.py             # Code archival
│   │   ├── git_operations.py      # Git commands
│   │   ├── knowledge_base.py      # Markdown operations
│   │   ├── mistake_processor.py   # Mistake documentation
│   │   └── validation.py          # Standards checking
│   ├── workflows/
│   │   ├── close_session.py       # Session cleanup
│   │   ├── document_changes.py    # Change documentation
│   │   └── whats_next.py          # Priority analysis
│   └── prompts/
│       └── system_prompt.md       # System prompt
├── deployment/
│   ├── gcp/                       # GCP VM deployment
│   ├── server-five/               # Server-five deployment
│   └── langchain-cloud/           # LangChain Cloud deployment
├── tools/                         # Utility docs (log ingestion)
├── Dockerfile                     # Production image
├── Dockerfile.dev                 # Development image
├── Dockerfile.inspector           # Inspector service image
├── docker-compose.yml             # Local development
└── pyproject.toml                 # Package config
```

**Middleware stack:**

```
Request → Logging → Breakpoint → Snapshot → Human-in-the-Loop → Tool Execution
```

## Tools

| Tool | Description |
|------|-------------|
| `changelog_tool` | Manage CHANGELOG.md |
| `archive_tool` | Archive outdated code |
| `mistake_processor_tool` | Document mistakes |
| `validation_tool` | Check standards |
| `git_push_tool` | Commit and push |
| `git_status_tool` | Get git status |
| `git_diff_tool` | Show git diff |
| `read_markdown_tool` | Read markdown files |
| `search_markdown_tool` | Search markdown |
| `update_markdown_tool` | Update markdown |

## Configuration

DAPY works with zero configuration. To customize, create `config.yaml`:

```yaml
model: openai:gpt-4o
debug: false
trace: true
snapshot_enabled: true
snapshot_dir: ./snapshots
persistence_backend: sqlite  # or postgres
db_path: ./dapy.db
auto_approve: false
approval_tools:
  - git_push_tool
  - archive_tool
todo_file: 2Do.md
roadmap_file: ROADMAP.md
changelog_file: CHANGELOG.md
```

**Environment variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGCHAIN_API_KEY` | Yes | LangSmith API key |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project (default: `dapy-dev`) |
| `DAPY_MODEL` | No | Model override (default: `openai:gpt-4o`) |
| `PERSISTENCE_BACKEND` | No | `sqlite` or `postgres` |
| `POSTGRES_CONN_STRING` | If postgres | PostgreSQL connection string |

## Development

```bash
pip install -e ".[dev]"
pytest
black dapy/
ruff check dapy/
mypy dapy/
```

## License

MIT
