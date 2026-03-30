---
name: work-m365
description: "User-level Microsoft 365 operations via Graph beta API. Use when the user mentions: outlook, email, calendar, onedrive, microsoft, office 365, ms365, my meetings, my emails, schedule meeting, send email, check calendar, to do, tasks, teams chat, onenote, presence, contacts."
user-invocable: true
argument-hint: "<command> [subcommand] [options]"
allowed-tools:
  - Bash
  - Read
  - Skill(get-secret)
---

# /m365 — User Microsoft 365 Operations

Access Microsoft 365 as a specific user via delegated permissions (Graph beta API).
Mail, Calendar, Teams Chat, Channels, Files, Tasks, Contacts, OneNote, Meetings, Presence.

Arguments passed: $ARGUMENTS

## Authentication

Application permissions via client credentials flow — routes `/me/` to `/users/{aad_id}/` per user.

**Credentials**: Use `/get-secret` to retrieve from Azure Key Vault:
- `chmo-graph-app-id` → set as `MS365_CLIENT_ID`
- `chmo-graph-client-secret` → set as `MS365_CLIENT_SECRET`
- Tenant ID: `052461ba-115a-49f9-8564-1857461f2161` → set as `MS365_TENANT_ID`

Or configure `tenants.json` alongside the script.

**App Registration**: Chmo Graph API (App ID: fa9fd725-d395-4db5-ba88-cf48325f17ac)

## User Routing

The `--user` flag selects which M365 mailbox to act on:
- `--user alex` → Alex Karelin (be083348-9398-4a22-acef-c48ab74806c1)
- `--user irina` → Irina Bushmakina (6fff1ee8-31ca-4480-b7b2-04dc6d20c81e)
- Default: alex

## CLI Reference

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/m365.py`. Run via:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" [--user USER] [--tenant TENANT] <command> [subcommand] [options]
```

If $ARGUMENTS is provided, parse and execute the matching command below.
If no arguments, show available commands.

### Auth
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex login
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex status
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex whoami
```

### Mail
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail list [--top N] [--folder FOLDER_ID]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail read MESSAGE_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail send --to "a@b.com" --subject "Subj" --body "Body" [--cc "c@d.com"] [--html]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail draft --to "a@b.com" --subject "Subj" --body "Body"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail reply MESSAGE_ID --body "Reply text"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex mail folders
```

### Calendar
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex cal list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex cal today
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex cal search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex cal create --subject "Meeting" --start "2026-04-01T10:00:00" --end "2026-04-01T11:00:00" [--attendees "a@b.com,c@d.com"] [--online] [--timezone "America/Los_Angeles"]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex cal delete EVENT_ID
```

### Teams Chat
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex chat list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex chat messages CHAT_ID [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex chat send CHAT_ID "message"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex chat search "query" [--top N]
```

### Teams Channels
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex channel list TEAM_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex channel messages TEAM_ID CHANNEL_ID [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex channel send TEAM_ID CHANNEL_ID "message"
```

### Files (OneDrive)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex files list [--path "Documents/subfolder"]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex files search "query"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex files sites "query"
```

### Tasks (To Do)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex tasks lists
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex tasks list LIST_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex tasks create LIST_ID --title "Task" [--due "2026-04-01"] [--body "Details"]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex tasks complete LIST_ID TASK_ID
```

### Contacts
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex contacts list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex contacts search "name"
```

### OneNote
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex notes notebooks
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex notes sections NOTEBOOK_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex notes pages SECTION_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex notes search "query" [--top N]
```

### Meetings
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex meetings create --subject "Standup" --start "2026-04-01T10:00:00Z" --end "2026-04-01T10:30:00Z"
```

### Presence
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex presence get
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex presence set Available [--activity "Available"]
```

### Unified Search (cross-entity)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365.py" --user alex search "query" [--top N] [--types "message,driveItem,event,chatMessage,site,list,listItem"]
```
Searches across multiple entity types in a single call via `/search/query`. Default types: message, driveItem, event.

## Implementation Notes

- All API calls use Graph beta endpoint
- The `--user` flag maps to AAD object IDs internally; `/me/` paths are rewritten to `/users/{aad_id}/`
- Output is JSON
- Requires `msal` and `requests` Python packages
