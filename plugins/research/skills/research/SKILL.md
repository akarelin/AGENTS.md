---
name: research
description: >
  Research router. Use when the user needs to search knowledge sources,
  explore databases, query data, find information, or investigate across
  systems. Routes to search-knowledge or dex based on intent.
---

# Research

Search and data exploration across all connected sources.

## Tools

| Tool | Description |
|------|-------------|
| search-knowledge | Search across providers (Obsidian, m365, Everything, Atlassian, Neo4j) |
| dex | Interactive data exploration: Neo4j (Cypher) and relational DBs (SQL) |

## Routing

- **"search for", "find", "look up", "where is"** → search-knowledge
- **"query", "explore data", "schema", "cypher", "SQL", "database"** → dex
