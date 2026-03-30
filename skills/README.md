# akarelin-skills — Claude Code Plugin Marketplace

Personal productivity plugins for Claude Code.

## Installation

```bash
# Add the marketplace
/plugin marketplace add akarelin/AGENTS.md

# Browse available plugins
/plugin marketplace list akarelin-skills

# Install individual plugins
/plugin install organize@akarelin-skills
/plugin install work@akarelin-skills
/plugin install devops-m365@akarelin-skills
/plugin install search@akarelin-skills
/plugin install session-manager@akarelin-skills
/plugin install skill-manager@akarelin-skills
```

## Available Plugins (6)

| Namespace | Plugin | Sub-skills | Description |
|-----------|--------|-----------|-------------|
| organize-* | **organize** | organize-arxiv, medical-scan-obsidian | File organizer (arxiv papers, medical scans) |
| work-* | **work** | work-m365, work-slack, work-jira | Workplace tools: M365, Slack (MCP), Jira/Confluence (MCP) |
| devops-* | **devops-m365** | — | M365 tenant admin: Users, Groups, Licenses, Audit, Security |
| search-* | **search** | search-everything, search-m365 | File search (Everything MCP) + M365 unified search |
| — | **session-manager** | — | Sync/list/resume/clean Claude sessions across repos |
| — | **skill-manager** | — | Patch, test, rebuild, and deploy plugin skills |

## Plugin Details

### organize
File organizer with sub-skill architecture:
- **organize-arxiv** — identifies arxiv PDFs, fetches metadata, renames to `{id} {#tags} {Title} {version}.pdf`, moves to library
- **medical-scan-obsidian** — converts medical scan images into a structured bilingual EN/RU Obsidian vault

### work
Workplace productivity with 3 sub-skills:
- **work-m365** — User-level M365 via Graph beta API: Mail, Calendar, Teams, Files, Tasks, Contacts, OneNote, Presence. CLI-based.
- **work-slack** — Slack via official MCP server (mcp.slack.com, OAuth). Messaging, search, channels, threads.
- **work-jira** — Jira + Confluence via official Atlassian MCP server. 5 workflow skills: bug triage, meeting notes → tasks, status reports, spec → backlog, knowledge search.

### devops-m365
M365 tenant administration via Graph beta API. User CRUD, group management, Teams admin, license assignment, directory roles, audit logs, devices, security alerts/score. Admin-only.

### search
Search with 2 sub-skills:
- **search-everything** — Fast local file search on Windows via voidtools Everything MCP server (16 tools). Also available as MCPB desktop extension.
- **search-m365** — Cross-entity M365 search via Graph `/search/query` API (emails, files, events, chat, SharePoint).

### session-manager
CLI tool for managing Claude Code session folders across multiple repos and hosts. Supports sync, list, resume, rename, and cleanup operations.

### skill-manager
End-to-end workflow for improving plugin skills: gather feedback, patch code, test, rebuild `.plugin` files, and deploy.
