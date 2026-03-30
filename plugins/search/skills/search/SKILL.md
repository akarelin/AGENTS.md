---
name: search
description: >
  This skill should be used when the user asks to "search for files",
  "find a file", "search emails", "search m365", "search OneDrive",
  "search SharePoint", "search Slack", "find in Slack", "find a message",
  or wants to search across local files, Microsoft 365, or Slack.
---

# Search

Meta-skill that routes to the appropriate search sub-skill.

## Sub-skills

| Sub-skill | Scope | How |
|-----------|-------|-----|
| search-everything | Local files (Windows) | MCP server via voidtools Everything |
| search-m365 | Microsoft 365 (emails, files, events, chat, SharePoint) | Graph `/search/query` API via work-m365 script |
| search-slack | Slack (messages, channels, files, people) | Slack MCP server |

## Routing

- **Local file search** → use the `search-everything` MCP tools directly
- **Microsoft 365 search** → read `search-m365` sub-skill
- **Slack search** → use Slack MCP search tools (see `search-slack` sub-skill)
- **Ambiguous** → ask the user which source they mean
