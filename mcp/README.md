# MCP Server

Seven MCP endpoints over Streamable HTTP transport: M365 Graph API, Azure Key Vault, Obsidian vault, Neo4j graph database, TickTick tasks, and QMD search index.

**Auth:** OAuth 2.0 against Microsoft Entra ID. The server exposes a shim
(`/.well-known/oauth-authorization-server`, `/register`, `/authorize`,
`/oauth/callback`, `/token`) that delegates user authentication to Entra and
returns Entra-issued JWTs. Inbound `Authorization: Bearer <jwt>` is validated
against Entra JWKS; the `oid` claim must appear in the `mcp-allowed-oids` Key
Vault secret. Legacy PSK (`x-api-key`) is still accepted in transition mode
(see `MCP_AUTH_MODE`).

## /keys — Secret Management (4 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `secret_get` | Retrieve a secret or API key by name from Azure Key Vault | name |
| `secret_list` | List available secret names in Azure Key Vault | |
| `secret_create` | Create a new secret. Fails on name collision. | name, value |
| `secret_update` | Update existing secret (new version). Fails if missing, unless `create=true`. | name, value, create? |

## /m365 — User M365 Operations (31 tools)

`user` parameter on all tools selects which mailbox/calendar to act on (default: env `MCP_DEFAULT_USER`)

| Tool | Description | Parameters |
|------|-------------|------------|
| `mail_list` | List recent email messages | user?, top?, folder? |
| `mail_read` | Read a specific email by ID | user?, message_id |
| `mail_search` | Search emails by keyword | user?, query, top? |
| `mail_send` | Send an email | user?, to, subject, body, cc?, html? |
| `mail_draft` | Create a draft email (not sent) | user?, to, subject, body |
| `mail_reply` | Reply to an email message | user?, message_id, body |
| `mail_folders` | List mail folders | user? |
| `cal_list` | List upcoming calendar events | user?, top? |
| `cal_today` | List today's calendar events | user? |
| `cal_search` | Search calendar events by keyword | user?, query, top? |
| `cal_create` | Create a calendar event | user?, subject, start, end, attendees?, online?, tz? |
| `cal_delete` | Delete a calendar event | user?, event_id |
| `chat_list` | List Teams chats | user?, top? |
| `chat_messages` | List messages in a Teams chat | user?, chat_id, top? |
| `chat_send` | Send a message in a Teams chat | user?, chat_id, message |
| `chat_search` | Search Teams chat messages across all chats | user?, query, top? |
| `channel_list` | List channels in a Teams team | user?, team_id |
| `channel_messages` | List messages in a Teams channel | user?, team_id, channel_id, top? |
| `channel_send` | Send a message to a Teams channel | user?, team_id, channel_id, message |
| `files_list` | List files in OneDrive folder | user?, path? |
| `files_search` | Search files in OneDrive | user?, query |
| `tasks_lists` | List all To Do task lists | user? |
| `tasks_list` | List tasks in a To Do list | user?, list_id |
| `tasks_create` | Create a new To Do task | user?, list_id, title, due?, body? |
| `tasks_complete` | Mark a To Do task as completed | user?, list_id, task_id |
| `contacts_list` | List contacts | user?, top? |
| `contacts_search` | Search people and contacts | user?, query |
| `notes_notebooks` | List OneNote notebooks | user? |
| `presence_get` | Get user presence/availability status | user? |
| `presence_set` | Set user presence status | user?, availability, activity? |
| `search` | Unified search across M365 (mail, files, events, chats, SharePoint) | user?, query, types?, top? |

## /m365-admin — Tenant Administration (13 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `users_list` | List all users in the tenant | top? |
| `users_get` | Get a specific user by ID or UPN | user_id |
| `users_search` | Search users by display name or email | query, top? |
| `groups_list` | List all groups in the tenant | top? |
| `groups_get` | Get a specific group by ID | group_id |
| `groups_members` | List members of a group | group_id |
| `domains_list` | List domains in the tenant | |
| `licenses_list` | List subscribed SKUs/licenses for the tenant | |
| `user_licenses` | List licenses assigned to a specific user | user_id |
| `devices_list` | List managed devices in the tenant | top? |
| `roles_list` | List directory roles in the tenant | |
| `role_members` | List members of a directory role | role_id |
| `org_info` | Get organization details | |

## /obsidian — Obsidian Vault Access (16 tools)

Tries hosts from `OBSIDIAN_HOSTS` env var in order. Requires Obsidian Local REST API plugin.

| Tool | Description | Parameters |
|------|-------------|------------|
| `vault_list` | List files/folders in a directory | path? |
| `vault_read` | Read note contents | path |
| `vault_search` | Full-text search across vault | query |
| `vault_search_dql` | Dataview DQL query | query |
| `vault_tags` | List all tags with counts | |
| `vault_active` | Get currently open note | |
| `vault_commands` | List Obsidian commands | |
| `vault_status` | Check which host is reachable | |
| `vault_write` | Create/overwrite a note | path, content |
| `vault_append` | Append to a note | path, content |
| `vault_patch` | Insert near heading/block/frontmatter | path, content, target_type, target |
| `vault_delete` | Delete file/folder | path |
| `vault_open` | Open note in Obsidian UI | path |
| `vault_command` | Execute Obsidian command | command_id |
| `vault_daily` | Get today's daily note | |
| `vault_daily_append` | Append to today's daily note | content |

## /neo4j — Graph Database (5 tools)

Auto-discovers Neo4j servers from Key Vault secrets (neo4j-*-uri / neo4j-*-password).

| Tool | Description | Parameters |
|------|-------------|------------|
| `neo4j_list_servers` | List available Neo4j servers | |
| `neo4j_use_server` | Select which server to use | server |
| `read_neo4j_cypher` | Execute a read-only Cypher query | query, params? |
| `write_neo4j_cypher` | Execute a write Cypher query | query, params? |
| `get_neo4j_schema` | Get graph schema (labels, relationships, properties) | |

## /ticktick — Task Management (6 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `tt_lists` | List all TickTick projects/lists | |
| `tt_tasks` | List tasks, optionally filtered | list?, status? |
| `tt_create` | Create a new task | title, list, content?, priority?, due?, tags? |
| `tt_update` | Update an existing task | task, list?, title?, content?, priority?, due?, tags? |
| `tt_complete` | Mark a task as completed | task, list? |
| `tt_abandon` | Mark a task as won't do | task, list? |

## /qmd — QMD Search Index (4 tools)

Hybrid BM25+vector search over a local QMD index via subprocess.

| Tool | Description | Parameters |
|------|-------------|------------|
| `qmd_search` | Hybrid BM25+vector search | query, collection?, limit? |
| `qmd_vsearch` | Vector-only semantic search | query, collection?, limit? |
| `qmd_get` | Get a specific file from the index | file_path |
| `qmd_status` | Index status and collection list | |

## Add to claude.ai

Settings → Connectors → Add custom MCP server → URL
`https://mcp.karelin.ai/<endpoint>` (e.g. `/keys`, `/m365`, etc.). On first
connect, claude.ai discovers the OAuth metadata, registers a client, opens the
Entra sign-in window, and stores tokens. Your `oid` must be in
`mcp-allowed-oids`.

## Connect from Claude Code

```bash
claude mcp add karelin-keys https://mcp.karelin.ai/keys
```

Claude Code walks the same OAuth dance and caches tokens. Repeat per endpoint.

Static config (e.g. `~/.config/claude-code/.mcp.json`) — Bearer token from any
helper (MSAL device-code, manual paste, etc.):

```json
{
  "mcpServers": {
    "Karelin Keys":     {"type": "http", "url": "https://mcp.karelin.ai/keys",       "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin M365":     {"type": "http", "url": "https://mcp.karelin.ai/m365",       "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin M365 Admin": {"type": "http", "url": "https://mcp.karelin.ai/m365-admin", "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin Obsidian": {"type": "http", "url": "https://mcp.karelin.ai/obsidian",   "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin Neo4j":    {"type": "http", "url": "https://mcp.karelin.ai/neo4j",      "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin TickTick": {"type": "http", "url": "https://mcp.karelin.ai/ticktick",   "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}},
    "Karelin QMD":      {"type": "http", "url": "https://mcp.karelin.ai/qmd",        "headers": {"Authorization": "Bearer ${MCP_KARELIN_TOKEN}"}}
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_AUTH_MODE` | `psk` \| `entra` \| `both` \| `disabled` | `psk` |
| `MCP_API_KEY` | Pre-shared key for legacy `x-api-key`/Bearer-PSK auth | |
| `AZURE_KEYVAULT_NAME` | Azure Key Vault name (Entra config + allowlist live there) | |
| `GRAPH_USERS` | User hint map: `name:aad-id,name:aad-id` | |
| `MSGRAPH_SECRET_PREFIX` | Secret name prefix for Graph creds | `msgraph` |
| `MCP_DEFAULT_USER` | Default user hint for M365 tools | `default` |
| `OBSIDIAN_HOSTS` | Comma-separated host list | |
| `OBSIDIAN_PORT` | Obsidian REST API port | `27123` |
| `OBSIDIAN_SCHEME` | HTTP or HTTPS | `http` |
| `OBSIDIAN_API_KEY` | Obsidian REST API bearer token | |
| `TICKTICK_CLIENT_ID` | TickTick OAuth client ID | |
| `TICKTICK_CLIENT_SECRET` | TickTick OAuth client secret | |
| `TICKTICK_ACCESS_TOKEN` | TickTick access token | |
| `QMD_BIN` | Path to qmd binary | `qmd` |
| `QMD_XDG_CONFIG` | XDG_CONFIG_HOME for qmd | |
| `QMD_XDG_CACHE` | XDG_CACHE_HOME for qmd | |
| `QMD_TIMEOUT` | Subprocess timeout in seconds | `30` |
| `MCP_TOOL_TEXT_LIMIT` | Max chars per tool response | `12000` |

## Run

```bash
docker compose up -d --build
```
