---
name: work-jira
description: >
  This skill should be used when the user mentions Jira, Confluence, Atlassian,
  asks to "create a ticket", "check my Jira issues", "triage a bug",
  "search Jira", "create a status report", "convert spec to backlog",
  "search company docs", "capture tasks from meeting notes", or any
  Jira/Confluence project management task.
version: 0.1.0
---

# Jira / Atlassian Integration

Jira and Confluence operations via the official Atlassian MCP server.

## MCP Connection

Uses the Atlassian MCP remote server:
```json
{
  "atlassian": {
    "type": "http",
    "url": "https://mcp.atlassian.com/v1/mcp"
  }
}
```

## Workflow Skills

Read the sub-skill SKILL.md files for detailed instructions:

| Sub-skill | Use case |
|-----------|----------|
| `triage-issue` | Triage bugs, check duplicates, create/update tickets |
| `capture-tasks-from-meeting-notes` | Extract action items from notes → Jira tasks |
| `generate-status-report` | Jira issues → formatted status report in Confluence |
| `spec-to-backlog` | Confluence spec → Epics + implementation tickets |
| `search-company-knowledge` | Search across Confluence, Jira, internal docs |

## Reference Files

Each sub-skill has its own directory with a SKILL.md containing detailed workflow instructions.
