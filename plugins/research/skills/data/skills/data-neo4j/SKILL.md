---
name: data-neo4j
description: >
  Neo4j graph database exploration via Cypher. Use when the user mentions
  Neo4j, Cypher, graph queries, nodes, relationships, or knowledge graph.
---

# Neo4j Data Exploration

Interactive Neo4j graph database exploration via Neo4j MCP.

## MCP Connection

Uses the Neo4j endpoint (auto-discovers servers from Key Vault):
```json
{
  "Neo4j": {
    "type": "http",
    "url": "https://mcp.karelin.ai/neo4j",
    "headers": {"x-api-key": "${MCP_KARELIN_PSK}"}
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `neo4j_list_servers` | List available Neo4j servers (auto-discovered from Key Vault) |
| `neo4j_use_server` | Select which Neo4j server to use |
| `read_neo4j_cypher` | Execute a read-only Cypher query |
| `write_neo4j_cypher` | Execute a write Cypher query |
| `get_neo4j_schema` | Get graph schema (labels, relationship types, properties) |

## Workflow

1. Call `neo4j_list_servers` to discover available databases
2. If multiple servers — present options and ask user which to use
3. If single server — auto-select it
4. Call `neo4j_use_server` with the chosen server name
5. Call `get_neo4j_schema` to understand the data model
6. Execute Cypher queries with `read_neo4j_cypher` or `write_neo4j_cypher`

## Server Discovery

Servers are auto-discovered from Azure Key Vault by matching secrets:
- `neo4j-{name}-uri` — connection string
- `neo4j-{name}-password` — authentication

Known servers: `default` (neo4j.karel.in), `xsolla-aura` (AuraDB)
