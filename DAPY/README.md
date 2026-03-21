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
│   ├── feedback_agent.py    # Feedback monitoring agent
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

## Workflows

3 LangGraph workflows:

1. **Close Session** — Sequential state machine: analyze session → update todo → check mistakes → archive work → generate summary
2. **Document Changes** — Detects git diff, classifies changes (Added/Changed/Fixed/Removed), updates CHANGELOG.md
3. **What's Next** — Reads 2Do.md, ROADMAP.md, and git status to determine recommended next steps

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

## Technology Stack

Python 3.11, LangChain >= 0.3.0, LangGraph >= 0.2.0, LangSmith >= 0.2.0, Click (CLI), Rich (terminal UI), GitPython, PyYAML. SQLite (local) or PostgreSQL (production) for state persistence.

## LLM Log Ingestion

Included tools (`tools/`) import ChatGPT and Claude conversation exports into LangSmith datasets, then query them to detect patterns, generate test cases, and export golden examples for prompt optimization.

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
