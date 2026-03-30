# akarelin-skills — Claude Code Plugin Marketplace

Personal productivity plugins for Claude Code.

## Installation

```bash
# Add the marketplace
/plugin marketplace add akarelin/AGENTS.md --path skills

# Browse available plugins
/plugin marketplace list akarelin-skills

# Install individual plugins
/plugin install organize@akarelin-skills
/plugin install work-m365@akarelin-skills
/plugin install devops-m365@akarelin-skills
/plugin install session-manager@akarelin-skills
/plugin install search-everything@akarelin-skills
/plugin install search-m365@akarelin-skills
/plugin install skill-manager@akarelin-skills
```

## Available Plugins

| Namespace | Plugin | Description |
|-----------|--------|-------------|
| organize-* | **organize** | File organizer with sub-skills (arxiv papers, medical scans) |
| work-* | **work-m365** | User-level M365: Mail, Calendar, Teams, Files, Tasks, Contacts, Presence |
| devops-* | **devops-m365** | M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security |
| — | **session-manager** | Sync/list/resume/clean Claude sessions across repos |
| search-* | **search-everything** | Fast file search via voidtools Everything MCP server (Windows) |
| search-* | **search-m365** | Cross-entity M365 search (emails, files, events, chat, SharePoint) |
| — | **skill-manager** | Patch, test, rebuild, and deploy plugin skills |

## Plugin Details

### organize
File organizer with a sub-skill architecture:
- **organize-arxiv** — identifies arxiv PDFs, fetches metadata, renames to `{id} {#tags} {Title} {version}.pdf`, moves to library
- **medical-scan-obsidian** — converts medical scan images into a structured bilingual EN/RU Obsidian vault

### work-m365
User-level Microsoft 365 operations via Graph beta API. Mail, Calendar, Teams Chat/Channels, OneDrive Files, To Do Tasks, Contacts, OneNote, Meetings, Presence. Uses client credentials with per-user routing.

### devops-m365
Microsoft 365 tenant administration via Graph beta API. User CRUD, group management, Teams admin, license assignment, directory roles, audit logs, devices, security alerts/score. Admin-only.

### session-manager
CLI tool for managing Claude Code session folders across multiple repos and hosts. Supports sync, list, resume, rename, and cleanup operations.

### search-everything
MCP server wrapping [voidtools Everything](https://www.voidtools.com/) for instant filename search. Windows only.

### search-m365
Cross-entity Microsoft 365 search via Graph `/search/query` API. Searches emails, files, events, chat messages, and SharePoint in one query. Depends on `work-m365`.

### skill-manager
End-to-end workflow for improving plugin skills: gather feedback, patch code, test, rebuild `.plugin` files, and deploy.
