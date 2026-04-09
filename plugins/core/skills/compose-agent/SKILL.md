---
name: compose-agent
description: >
  Create an agent from multiple existing agents or skills. Use when
  the user says "create an agent", "combine agents", "compose agent",
  "deploy agent", or wants to build a new agent from existing ones.
  Supports both local Claude Code subagents and cloud Managed Agents.
allowed-tools: [Read, Write, Glob, Grep, Bash, AskUserQuestion]
---

# Compose Agent

Create a new agent by combining existing agents and skills. Supports two deployment targets:
- **Local** — Claude Code subagent (`.md` file)
- **Cloud** — Anthropic Managed Agent (API deployment)

## Workflow

1. **Discover available agents and skills**
   - Scan `~/.claude/agents/`, `.claude/agents/`, and plugin `agents/` directories
   - Scan `skills/` directories across all plugins
   - Present available components to the user

2. **Gather requirements**
   - Ask which agents/skills to combine
   - Ask for the new agent's name and purpose
   - Ask for deployment target: **local** or **cloud**
   - For local: ask for scope — user (`~/.claude/agents/`), project (`.claude/agents/`), or plugin
   - For cloud: ask for environment config (networking, packages)

3. **Determine configuration**
   - **tools**: union of all component agents' tools, or restrict per user preference
   - **skills**: list all skills from selected components
   - **mcpServers**: merge MCP servers from selected components (check `.mcp.json` files)
   - **model**: ask user or default to `inherit` (local) / `claude-sonnet-4-6` (cloud)
   - **permissionMode**: ask if needed (local only)
   - **memory**: ask if the agent should persist learnings (local only)

4. **Deploy**
   - **Local**: write `.md` file with YAML frontmatter and system prompt
   - **Cloud**: create agent and environment via Anthropic API, optionally start a session

5. **Validate**
   - Local: verify all referenced skills and MCP servers exist
   - Cloud: verify agent and environment were created successfully

---

## Local Agent (Claude Code Subagent)

### File Format

```markdown
---
name: <agent-name>
description: >
  <when Claude should delegate to this agent>
model: <sonnet|opus|haiku|inherit>
tools: <comma-separated tool list or omit for all>
skills:
  - <skill-1>
  - <skill-2>
mcpServers:
  <server-name>:
    type: http
    url: <url>
permissionMode: <default|acceptEdits|auto|plan>
memory: <user|project|none>
---

<system prompt with routing logic>
```

### Frontmatter Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Lowercase with hyphens |
| `description` | yes | When to delegate — Claude uses this for routing |
| `model` | no | Model: `sonnet`, `opus`, `haiku`, `inherit` |
| `tools` | no | Tool allowlist (default: inherit all) |
| `disallowedTools` | no | Tool denylist |
| `skills` | no | Skills loaded into context at startup |
| `mcpServers` | no | MCP servers available to this agent |
| `permissionMode` | no | Permission mode |
| `maxTurns` | no | Max agentic turns |
| `memory` | no | Persistent memory scope |
| `background` | no | Run as background task |
| `isolation` | no | `worktree` for git isolation |
| `color` | no | UI color |

### Example

```markdown
---
name: daily-standup
description: >
  Daily standup agent. Use when the user asks for a standup summary.
model: sonnet
skills:
  - search
  - work-m365
  - work-atlassian
mcpServers:
  M365:
    type: http
    url: https://mcp.karelin.ai/m365
  atlassian:
    type: http
    url: https://mcp.atlassian.com/v1/mcp
memory: user
color: blue
---

You are a daily standup agent. When invoked:
1. Search yesterday's email and calendar (work-m365)
2. Check Jira for recently updated tickets (work-atlassian)
3. Summarize: what was done, what's planned, any blockers
```

---

## Cloud Agent (Anthropic Managed Agent)

Deploys via the Anthropic API. Requires `ANTHROPIC_API_KEY` env var.
All API calls require the `managed-agents-2026-04-01` beta header.

### Step 1: Create Agent

```bash
curl -sS https://api.anthropic.com/v1/agents \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{
    "name": "<agent-name>",
    "model": "claude-sonnet-4-6",
    "system": "<system prompt>",
    "tools": [{"type": "agent_toolset_20260401"}]
  }'
```

Save the returned `id` and `version`.

### Step 2: Create Environment

```bash
curl -sS https://api.anthropic.com/v1/environments \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{
    "name": "<env-name>",
    "config": {
      "type": "cloud",
      "networking": {"type": "unrestricted"}
    }
  }'
```

### Step 3: Start Session (optional)

```bash
curl -sS https://api.anthropic.com/v1/sessions \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{
    "agent": "<agent-id>",
    "environment_id": "<environment-id>",
    "title": "<session-title>"
  }'
```

### Step 4: Send Message & Stream

```bash
# Send message
curl -sS "https://api.anthropic.com/v1/sessions/$SESSION_ID/events" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{"events": [{"type": "user.message", "content": [{"type": "text", "text": "<prompt>"}]}]}'

# Stream response
curl -sS -N "https://api.anthropic.com/v1/sessions/$SESSION_ID/stream" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "Accept: text/event-stream"
```

### Cloud Concepts

| Concept | Description |
|---------|-------------|
| **Agent** | Model, system prompt, tools, MCP servers |
| **Environment** | Container template (packages, network access) |
| **Session** | Running agent instance performing a task |
| **Events** | Messages exchanged (user turns, tool results, status) |

### Cloud Tools

`agent_toolset_20260401` enables: bash, file operations, web search, and more.
For per-tool control, specify individual tool types instead.
