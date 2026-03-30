# akarelin-skills — Claude Code Plugin Marketplace

Personal productivity plugins for Claude Code.

## Installation

```bash
# Add the marketplace
/plugin marketplace add akarelin/AGENTS.md --path skills

# Browse available plugins
/plugin marketplace list akarelin-skills

# Install individual plugins
/plugin install everything-search@akarelin-skills
/plugin install organize@akarelin-skills
/plugin install session-manager@akarelin-skills
/plugin install skill-manager@akarelin-skills
/plugin install m365@akarelin-skills
/plugin install m365-admin@akarelin-skills
```

## Available Plugins

| Plugin | Description | Platform |
|--------|-------------|----------|
| **everything-search** | Fast file search via voidtools Everything MCP server | Windows |
| **organize** | File organizer with sub-skills (arxiv papers, medical scans) | Any |
| **session-manager** | Sync/list/resume/clean Claude sessions across repos | Any (Python 3) |
| **skill-manager** | Patch, test, rebuild, and deploy plugin skills | Any |
| **m365** | User-level M365 ops: Mail, Calendar, Teams, Files, Tasks, Contacts, Presence | Any (Python 3) |
| **m365-admin** | M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security | Any (Python 3) |

## Plugin Details

### everything-search
MCP server wrapping [voidtools Everything](https://www.voidtools.com/) for instant filename search. Requires Everything running on Windows with `es.exe` in PATH.

### organize
File organizer with a sub-skill architecture. Sub-skills included:
- **organize-arxiv** — identifies arxiv PDFs by filename or page-1 text, fetches metadata, renames with `{id} {#tags} {Title} {version}.pdf`, moves to library
- **medical-scan-obsidian** — converts medical scan images into a structured bilingual EN/RU Obsidian vault with discharge notes, per-study notes, and diagnostics summary

### session-manager
CLI tool for managing Claude Code session folders across multiple repos and hosts. Supports sync, list, resume, rename, and cleanup operations.

### skill-manager
End-to-end workflow for improving plugin skills: gather feedback, patch code, test, rebuild `.plugin` files, and deploy.

### m365
User-level Microsoft 365 operations via Graph beta API. Ported from OpenClaw workspace skill. Supports Mail, Calendar, Teams Chat/Channels, OneDrive Files, To Do Tasks, Contacts, OneNote, Meetings, and Presence. Uses client credentials flow with `/me/` → `/users/{aad_id}/` rewriting for per-user routing. Requires `msal` and `requests` packages.

### m365-admin
Microsoft 365 tenant administration via Graph beta API with application permissions. Ported from OpenClaw workspace skill. Full admin capabilities: user CRUD, group management, Teams admin, license assignment, directory roles, audit logs, device listing, domain/org info, and security alerts/score. Restricted to admin users only. Requires `msal` and `requests` packages.
