# work

Workplace productivity tools with sub-skills for M365, Slack, and Jira/Confluence.

## Installation

```
/plugin install work@akarelin-skills
```

## Sub-skills

### work-m365
User-level Microsoft 365 operations via Graph beta API. Mail, Calendar, Teams Chat/Channels, OneDrive Files, To Do Tasks, Contacts, OneNote, Meetings, Presence. Requires `pip install msal requests`.

### work-slack
Slack workspace integration via official Slack MCP server. Messaging, search, channels, threads, user profiles, canvases. Includes reference guides for message formatting and search modifiers.

### work-jira
Jira + Confluence via official Atlassian MCP server. Includes 5 workflow skills: bug triage, meeting notes to tasks, status report generation, spec to backlog conversion, and company knowledge search.

## MCP Connectors

Installing this plugin registers two remote MCP servers:
- **Slack** (`mcp.slack.com`) — OAuth-authenticated
- **Atlassian** (`mcp.atlassian.com`) — browser-authenticated
