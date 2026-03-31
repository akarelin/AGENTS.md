---
name: work
description: >
  This skill should be used when the user asks to "check my email",
  "send a message on Slack", "create a Jira ticket", "schedule a meeting",
  "check my calendar", "send a Teams message", "search OneDrive",
  "triage a bug", "search company docs", "capture tasks from meeting notes",
  "check gmail", "search google drive", "send personal email",
  or any workplace productivity task involving M365, Slack, Jira, or Google.
---

# Work

Meta-skill that routes to the appropriate workplace sub-skill.

## Sub-skills

| Sub-skill | Scope | Connector |
|-----------|-------|-----------|
| work-m365 | Microsoft 365: Mail, Calendar, Teams, Files, Tasks, Contacts, OneNote, Presence | CLI (Graph API) |
| work-google | Personal Google: Gmail, Drive | CLI (Google API, OAuth2) |
| work-slack | Slack: messaging, search, channels, threads, canvases | MCP (mcp.slack.com) |
| work-jira | Jira + Confluence: issues, triage, status reports, specs, knowledge search | MCP (mcp.atlassian.com) |

## Routing

- **M365 email, calendar, Teams, OneDrive, To Do, contacts, presence** → `work-m365`
- **Gmail, Google Drive, personal email** → `work-google`
- **Slack messages, channels, search** → `work-slack` (uses Slack MCP tools)
- **Jira issues, Confluence docs, bugs, sprints, reports** → `work-jira` (uses Atlassian MCP tools)
- **Ambiguous "email"** → ask the user whether they mean M365 (work) or Gmail (personal)
