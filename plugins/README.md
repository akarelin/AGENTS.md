# akarelin — Claude Code Plugin Marketplace

Personal productivity plugins for Claude Code.

## Installation

```bash
# Add the marketplace
/plugin marketplace add akarelin/AGENTS.md

# Browse available plugins
/plugin marketplace list akarelin

# Install individual plugins
/plugin install core@akarelin
/plugin install research@akarelin
/plugin install work@akarelin
/plugin install organize@akarelin
/plugin install manage@akarelin
/plugin install administer@akarelin
```

## Available Plugins (6)

| Plugin | Skills | Description |
|--------|--------|-------------|
| **core** | memory, session, skill, compose-agent, learn | Agent primitives: memory, sessions, skill management, agent composition |
| **research** | search, data (data-neo4j, data-sql) | Search + data exploration: knowledge search, Neo4j, SQL |
| **work** | work-m365, work-slack, work-atlassian | Workplace: M365, Slack (MCP), Jira/Confluence (MCP) |
| **organize** | organize-arxiv, organize-scan-medical | File organizer (arxiv papers, medical scans) |
| **manage** | session, skill | Session and skill management |
| **administer** | admin-m365, admin-gcp | Cloud admin: M365 tenant + GCP resources |

## Plugin Details

### core
- **memory** — Persist and recall facts, secrets, state across sessions
- **session** — Claude Code sessions: sync, list, resume, rename, cleanup
- **skill** — Plugin skills: review feedback, patch, test, rebuild, deploy
- **compose-agent** — Create managed agents from multiple agents/skills (local + cloud)

### research
- **search** — Multi-provider search (Obsidian, m365, Everything, Atlassian, Neo4j) scoped by ownership
- **data** — Interactive data exploration
  - **data-neo4j** — Neo4j graph via Neo4j MCP: schema, Cypher queries, auto-discovers servers from Key Vault
  - **data-sql** — Relational DBs via DBHub MCP: PostgreSQL, MySQL, SQLite, SQL Server

### work
- **work-m365** — M365 via Graph API: Mail, Calendar, Teams, Files, Tasks, Contacts, Presence
- **work-slack** — Slack via official MCP (mcp.slack.com, OAuth): messaging, search, channels, threads
- **work-atlassian** — Jira + Confluence via Atlassian MCP: triage, meeting notes, status reports, spec→backlog

### organize
- **organize-arxiv** — arxiv PDFs: identify, fetch metadata, rename, move to library
- **organize-scan-medical** — medical scans → bilingual EN/RU Obsidian vault

### manage
- **session** — Claude Code sessions: sync, list, resume, rename, cleanup
- **skill** — Plugin skills: review feedback, patch, test, rebuild, deploy

### administer
- **admin-m365** — M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security
- **admin-gcp** — GCP administration: Projects, Compute, IAM, Storage, Cloud Run, Secrets
