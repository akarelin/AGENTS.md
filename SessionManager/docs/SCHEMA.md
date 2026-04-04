# SessionManager — Database Schema

## Overview

PostgreSQL schema for multi-user LLM session & project management.

```
users ──< sessions >── projects
              │
              ├── messages (conversation content)
              ├── session_content (raw JSONL)
              ├── session_relations (links between sessions)
              ├── llm_analyses (auto-naming, correlation)
              ├── sync_log (Langfuse deposit/withdraw)
              └── audit_log (all operations)
```

## Core Tables

| Table | Purpose |
|-------|---------|
| `users` | Operators who create sessions |
| `projects` | Group related sessions |
| `sessions` | One LLM conversation — source, model, tokens, cost, timing |
| `messages` | Individual messages within a session |
| `session_content` | Full JSONL stored as-is for replay/export |
| `session_relations` | Links: continuation, related, parent/child, merged |
| `tags` | Controlled tag vocabulary |
| `llm_analyses` | LLM-generated names, summaries, correlations |
| `sync_log` | Langfuse sync tracking |
| `audit_log` | Full operation audit trail |

## Key Design Decisions

1. **`sessions` is the hub** — everything hangs off it
2. **`session_content`** stores raw JSONL separately (large, rarely queried)
3. **`messages`** parsed out for searchability, but JSONL is source of truth
4. **`session_relations`** for LLM-detected correlations + manual merges
5. **`llm_analyses`** caches LLM calls (prompt hash for dedup)
6. **Soft deletes** via `status='archived'` / `archived_at`
7. **Merge tracking** via `merged_into_id` + `merged_from` relation
8. **Views** for common queries (v_sessions, v_project_stats, v_user_activity)
9. **pg_trgm** for fuzzy name search, pgvector reserved for future semantic search
10. **Langfuse is the viewer**, Postgres is the source of truth

## Session Lifecycle

```
local JSONL → deposit → sessions + messages + session_content
                  ↓
            sync_log (deposit)
                  ↓
            Langfuse (trace + generations)
```

## Token Tracking

Sessions track 4 token types:
- `input_tokens` — prompt tokens
- `output_tokens` — completion tokens  
- `cache_read_tokens` — prompt cache hits
- `cache_write_tokens` — prompt cache writes

`cost_usd` is estimated from token counts × model pricing.

## Planned Extensions

- **pgvector** on `messages.content` for semantic session search
- **Materialized views** for dashboard aggregations
- **Partitioning** on `messages` by `session_id` if table grows large
