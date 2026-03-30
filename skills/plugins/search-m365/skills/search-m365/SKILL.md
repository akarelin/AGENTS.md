---
name: search-m365
description: "Cross-entity Microsoft 365 search. Use when the user mentions: search m365, find email, find file in onedrive, search teams, search sharepoint, find in microsoft, search across office 365, search calendar events, search chat messages."
user-invocable: true
argument-hint: "<query> [--types message,driveItem,event,chatMessage,site,list,listItem] [--top N]"
allowed-tools:
  - Bash
  - Read
  - Skill(get-secret)
---

# /search-m365 — Microsoft 365 Unified Search

Search across multiple M365 entity types in a single call via the Graph `/search/query` API.

Arguments passed: $ARGUMENTS

## Authentication

Same credentials as work-m365. Use `/get-secret` to retrieve from Azure Key Vault:
- `chmo-graph-app-id` → `MS365_CLIENT_ID`
- `chmo-graph-client-secret` → `MS365_CLIENT_SECRET`
- Tenant ID: `052461ba-115a-49f9-8564-1857461f2161` → `MS365_TENANT_ID`

## User Routing

- `--user alex` → Alex Karelin (default)
- `--user irina` → Irina Bushmakina

## CLI Reference

Uses the work-m365 script:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/../work-m365/m365.py" --user alex search "query" [--top N] [--types "message,driveItem,event,chatMessage,site,list,listItem"]
```

### Searchable entity types

| Type | What it searches |
|------|-----------------|
| `message` | Outlook emails |
| `driveItem` | OneDrive / SharePoint files |
| `event` | Calendar events |
| `chatMessage` | Teams chat messages |
| `site` | SharePoint sites |
| `list` | SharePoint lists |
| `listItem` | SharePoint list items |

Default types: `message,driveItem,event`

### Examples

```bash
# Search emails and files for "budget"
python3 "${CLAUDE_PLUGIN_ROOT}/../work-m365/m365.py" --user alex search "budget"

# Search only Teams chats
python3 "${CLAUDE_PLUGIN_ROOT}/../work-m365/m365.py" --user alex search "standup" --types "chatMessage"

# Search everything, top 20
python3 "${CLAUDE_PLUGIN_ROOT}/../work-m365/m365.py" --user alex search "project plan" --top 20 --types "message,driveItem,event,chatMessage,site"
```

## Implementation Notes

- Uses Graph beta `/search/query` endpoint
- Results grouped by entity type
- Output is JSON (pretty-printed)
- Requires `work-m365` plugin to be installed (shares its `m365.py` script)
