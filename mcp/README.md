# MCP Server — mcp.karelin.com

Four MCP endpoints: M365 Graph API, Azure Key Vault, and Obsidian vault access.

**Auth:** OAuth 2.0 PKCE (claude.ai) or `x-api-key` header (Claude Code)

## /keys — Secret Management (2 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_secret` | Retrieve a secret or API key by name from Azure Key Vault | name |
| `list_secrets` | List available secret names in Azure Key Vault | |

## /m365 — User M365 Operations (31 tools)

`user` parameter on all tools: `alex` or `irina` (default: `alex`)

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

Tries hosts in order: alex-laptop, alex-mac, alex-pc (port 27123). Requires Obsidian Local REST API plugin.

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

## Connect from Claude Code

```json
{
  "mcpServers": {
    "Karelin Keys":       {"type": "http", "url": "https://mcp.karelin.com/keys",       "headers": {"x-api-key": "${MCP_KARELIN_PSK}"}},
    "Karelin M365":       {"type": "http", "url": "https://mcp.karelin.com/m365",       "headers": {"x-api-key": "${MCP_KARELIN_PSK}"}},
    "Karelin M365 Admin": {"type": "http", "url": "https://mcp.karelin.com/m365-admin", "headers": {"x-api-key": "${MCP_KARELIN_PSK}"}},
    "Karelin Obsidian":   {"type": "http", "url": "https://mcp.karelin.com/obsidian",   "headers": {"x-api-key": "${MCP_KARELIN_PSK}"}}
  }
}
```

## Run

```bash
docker compose up -d --build
```
