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
/plugin install search@akarelin-skills
/plugin install manage@akarelin-skills
```

## Available Plugins (4)

| Plugin | Sub-skills | Description |
|--------|-----------|-------------|
| **organize** | organize-arxiv, medical-scan-obsidian | File organizer (arxiv papers, medical scans) |
| **work** | work-m365, work-slack, work-jira | Workplace: M365, Slack (MCP), Jira/Confluence (MCP) |
| **search** | search-everything, search-m365 | File search (Everything MCP) + M365 unified search |
| **manage** | manage-sessions, manage-skills, manage-m365 | Sessions, plugins, M365 tenant admin |

## Plugin Details

### organize
- **organize-arxiv** — arxiv PDFs: identify, fetch metadata, rename, move to library
- **medical-scan-obsidian** — medical scans → bilingual EN/RU Obsidian vault

### work
- **work-m365** — M365 via Graph API: Mail, Calendar, Teams, Files, Tasks, Contacts, Presence (CLI)
- **work-slack** — Slack via official MCP (mcp.slack.com, OAuth): messaging, search, channels, threads
- **work-jira** — Jira + Confluence via Atlassian MCP: triage, meeting notes, status reports, spec→backlog, knowledge search

### search
- **search-everything** — voidtools Everything MCP (16 tools, Windows). Also available as MCPB desktop extension.
- **search-m365** — Cross-entity M365 search (emails, files, events, chat, SharePoint)

### manage
- **manage-sessions** — Claude Code sessions: sync, list, resume, rename, cleanup
- **manage-skills** — Plugin skills: review feedback, patch, test, rebuild, deploy
- **manage-m365** — M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security
