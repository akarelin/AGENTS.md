---
name: search
description: >
  Search across knowledge sources scoped by ownership level.
  Use when the user says "search for", "find", "look up", "where is",
  "search my email", "search company docs", "find in Confluence",
  "search Slack", "search files", or any retrieval from external systems.
allowed-tools: [Read, Bash, Grep, Glob, AskUserQuestion]
---

# Search Knowledge

Single tool for searching across providers, parameterized by scope and provider.

## Scopes and Providers

| Scope | Providers | What's searched |
|-------|-----------|-----------------|
| my | Obsidian, m365, Everything, Neo4j | Personal vault, personal email/OneDrive/calendar, local files, knowledge graph |
| team | m365, Atlassian, Neo4j | Teams channels, shared drives, team Jira/Confluence, knowledge graph |
| project | m365, Atlassian | Project SharePoint, project Jira board/Confluence space |
| company | m365, Atlassian | Company-wide M365, all Confluence + Jira |

## Scope Detection

Detect scope from context:
- "my notes", "my email", "my files" → my
- "our team", "team channel" → team
- "this project", "project board" → project
- "company docs", "company wiki" → company
- Ambiguous → ask user

## Provider Routing

| Provider | How |
|----------|-----|
| Obsidian | Grep/Glob on vault path (my scope only) |
| m365 | Graph API search via work-m365 script |
| Everything | MCP server `mcp-everything-search` (my scope only) |
| Atlassian | Atlassian MCP — Rovo Search, CQL, JQL |
| Neo4j | Neo4j MCP — Cypher queries on knowledge graph (my, team scopes) |

## Workflow

1. Detect or ask for scope
2. Select providers available for that scope
3. Search in parallel across selected providers
4. Synthesize results with source attribution
5. Provide citations and links

## Absorbed Skills
This tool replaces:
- search-everything → search-knowledge scope:my provider:Everything
- search-m365 → search-knowledge scope:my provider:m365
- search-slack → handled via work-slack MCP (Slack is a work tool, not a knowledge source)
- search-company-knowledge → search-knowledge scope:company provider:Atlassian
