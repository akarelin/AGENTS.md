---
name: work-slack
description: >
  This skill should be used when the user mentions Slack, asks to
  "send a Slack message", "check Slack", "search Slack", "list channels",
  "find a Slack message", "read a thread", or any Slack communication task.
---

# Slack Integration

Slack workspace operations via the official Slack MCP server.

## MCP Connection

Uses the Slack MCP remote server (OAuth):
```json
{
  "slack": {
    "type": "http",
    "url": "https://mcp.slack.com/mcp",
    "oauth": {
      "clientId": "1601185624273.8899143856786",
      "callbackPort": 3118
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `slack_send_message` | Send a message to a channel or DM |
| `slack_send_message_draft` | Draft a message for user review |
| `slack_create_canvas` | Create a Slack Canvas |
| `slack_search_public` | Search public channels |
| `slack_search_public_and_private` | Search all channels (requires consent) |
| `slack_search_channels` | Find channels by name/description |
| `slack_search_users` | Find people by name/email/role |
| `slack_read_thread` | Read full thread context |
| `slack_read_channel` | Read channel messages in a time range |
| `slack_read_user_profile` | Get user profile details |

## Reference Files

- `references/slack-messaging.md` — formatting guide and message best practices
- `references/slack-search.md` — search strategy, modifiers, and filters
