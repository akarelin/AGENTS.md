---
name: search-slack
description: >
  This skill should be used when the user asks to "search Slack",
  "find a Slack message", "search Slack channels", "find in Slack",
  or needs to search across Slack messages, channels, files, or people.
version: 0.1.0
---

# Slack Search

Search across Slack messages, channels, files, and people via the Slack MCP server.

## MCP Connection

Uses the Slack MCP remote server (same as work-slack):
```json
{
  "slack": {
    "type": "http",
    "url": "https://mcp.slack.com/mcp"
  }
}
```

## Search Tools

| Tool | Use When |
|------|----------|
| `slack_search_public` | Searching public channels only (no consent needed) |
| `slack_search_public_and_private` | Searching all channels including private, DMs, group DMs (requires consent) |
| `slack_search_channels` | Finding channels by name or description |
| `slack_search_users` | Finding people by name, email, or role |

## Search Modifiers

- `in:channel-name` — specific channel
- `from:username` — messages from user
- `before:` / `after:` / `on:` `YYYY-MM-DD` — date filters
- `"exact phrase"` — exact match
- `-word` — exclude
- `has:link` / `has:file` / `has:pin` — content filters
- `is:thread` — threaded messages
- `type:pdfs` / `type:images` — file type filters

## Follow-up

After finding results, use `slack_read_thread` for full thread context or `slack_read_channel` with timestamps for surrounding messages.
