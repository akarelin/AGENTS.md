# m365

User-level Microsoft 365 operations via Graph beta API.

## Installation

```
/plugin install m365@akarelin-skills
```

Requires: `pip install msal requests`

## Capabilities

| Module | Operations |
|--------|-----------|
| **Mail** | list, read, search, send, draft, reply, folders |
| **Calendar** | list, today, search, create, delete |
| **Teams Chat** | list, messages, send, search |
| **Teams Channels** | list, messages, send |
| **Files (OneDrive)** | list, search, sites |
| **Tasks (To Do)** | lists, list, create, complete |
| **Contacts** | list, search |
| **OneNote** | notebooks, sections, pages, search |
| **Meetings** | create |
| **Presence** | get, set |
| **Unified Search** | cross-entity search (mail, files, events, chat) |

## Authentication

Uses client credentials flow with `/me/` to `/users/{aad_id}/` rewriting for per-user routing. Supports `--user` flag for mailbox selection.

## Usage

```bash
python3 m365.py --user alex mail list --top 5
python3 m365.py --user alex cal today
python3 m365.py --user alex chat list
```
