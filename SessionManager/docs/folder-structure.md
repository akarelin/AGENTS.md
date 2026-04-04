# Folder-Based Session Store

For environments without a database server. A shared folder (NAS, Dropbox, Syncthing, mounted drive) acts as the session store.

## Structure

```
sessions/                              ← root (configurable)
├── .sm/                               ← metadata
│   ├── config.yaml                    ← store config (users, settings)
│   └── index.json                     ← optional: cached session index for fast lookup
│
├── projects/                          ← project definitions
│   ├── neuronet/
│   │   ├── project.yaml              ← name, description, owner, tags
│   │   └── sessions/                 ← symlinks or session IDs referencing sessions below
│   │       ├── 5ccbb62b.yaml         ← session association metadata
│   │       └── 012f0b5e.yaml
│   ├── tool-catalog/
│   │   └── project.yaml
│   └── office-fortress/
│       └── project.yaml
│
├── users/                             ← per-user directories
│   └── alex/
│       ├── user.yaml                 ← display_name, email, settings
│       └── sessions/                 ← all sessions by this user
│           ├── 5ccbb62b/
│           │   ├── meta.yaml         ← name, source, model, tags, timestamps, stats
│           │   ├── session.jsonl     ← raw JSONL (source of truth)
│           │   └── summary.md        ← LLM-generated summary (optional)
│           ├── 012f0b5e/
│           │   ├── meta.yaml
│           │   ├── session.jsonl
│           │   └── analysis.yaml     ← LLM naming/correlation results
│           └── c314b553/
│               ├── meta.yaml
│               └── session.jsonl
│
└── archive/                           ← archived sessions (moved, not deleted)
    └── alex/
        └── old-session-id/
            ├── meta.yaml
            └── session.jsonl
```

## File Formats

### project.yaml
```yaml
name: Neuronet
slug: neuronet
description: Agent scope for Slack integration
owner: alex
tags: [ai, agents, slack]
created: 2026-04-02
git_repo: akarelin/neuronet
```

### user.yaml
```yaml
username: alex
display_name: Alex Karelin
email: alex@karel.in
```

### meta.yaml (per session)
```yaml
id: 5ccbb62b-4d87-4354-998a-5f2a13d6869f
name: Neo4j Tool Catalog Extraction     # human or LLM-assigned
name_source: llm-auto                    # manual | llm-auto
source: claude-code                      # claude-code | openclaw | claude-desktop | codex
source_host: alex-mac
source_file: ~/.claude/projects/-Users-alex-xsolla-tool-catalog/5ccbb62b.jsonl
model: claude-sonnet-4-6
provider: anthropic-vertex
project: tool-catalog                    # linked project slug (optional)
cwd: /Users/alex/xsolla-tool-catalog
git_branch: master
git_repo: akarelin/xsolla-tool-catalog
started: 2026-04-02T14:54:45Z
ended: 2026-04-02T15:30:00Z
messages: 62
generations: 38
input_tokens: 1458270
output_tokens: 11239
tags: [extraction, neo4j, v1]
status: completed                        # active | completed | archived | merged
merged_into: null
langfuse_trace_id: fbd463c179e0ad654a9b91b72a107fb7
```

### analysis.yaml (LLM results)
```yaml
analyses:
  - type: name
    model: claude-sonnet-4-6
    result:
      name: Neo4j Tool Catalog Extraction
      project: tool-catalog
      tags: [extraction, neo4j]
    applied: true
    timestamp: 2026-04-03T17:10:00Z

  - type: correlate
    model: claude-sonnet-4-6
    result:
      related: [012f0b5e, c314b553]
      group: infrastructure
      merge_suggestion: "continuation of same work"
    applied: false
    timestamp: 2026-04-03T17:11:00Z
```

## Operations

| Operation | Folder Action |
|-----------|---------------|
| Deposit | Copy JSONL → `users/<user>/sessions/<id>/session.jsonl`, create `meta.yaml` |
| Rename | Update `meta.yaml` name field |
| Archive | Move session dir to `archive/<user>/` |
| Merge | Create new session dir, concat JSONLs, update meta, move originals to archive |
| Associate to project | Create `projects/<slug>/sessions/<id>.yaml` with reference |
| Delete | `trash` the session directory |
| Search | Scan `meta.yaml` files (or use `index.json` cache) |
| Sync to Langfuse | Read `meta.yaml` + `session.jsonl`, deposit, update `langfuse_trace_id` |

## Index Cache

Optional `index.json` for fast listing without scanning all `meta.yaml` files:

```json
{
  "updated": "2026-04-03T17:25:00Z",
  "sessions": [
    {
      "id": "5ccbb62b",
      "user": "alex",
      "name": "Neo4j Tool Catalog Extraction",
      "source": "claude-code",
      "project": "tool-catalog",
      "started": "2026-04-02T14:54:45Z",
      "messages": 62,
      "tags": ["extraction", "neo4j"],
      "status": "completed"
    }
  ]
}
```

Rebuilt by `sm-local index` or on any write operation.

## Multi-User

Multiple users point to the same shared folder:
- Each user writes to `users/<their-name>/sessions/`
- Projects are shared — anyone can associate sessions
- No locking needed (append-only JSONL, separate meta files)
- Conflicts: last-write-wins on `meta.yaml` (rare, non-critical)

## Config

`config.yaml` at root or `~/.config/sm/config.yaml`:

```yaml
store:
  type: folder                # folder | postgres | langfuse-only
  path: /mnt/nas/sessions     # shared folder path
  user: alex                  # current user

langfuse:
  host: https://langfuse.karelin.ai
  public_key: pk-lf-...
  secret_key: sk-lf-...
```
