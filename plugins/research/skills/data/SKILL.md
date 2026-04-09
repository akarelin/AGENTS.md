---
name: data
description: >
  Data exploration across databases. Use when the user says "query",
  "explore data", "show me the schema", "run cypher", "run SQL",
  "what's in the database", "list tables", "list nodes", or any
  interactive database exploration task.
---

# Data Exploration

Interactive exploration of graph and relational databases via MCP.

## Sub-skills

| Skill | Database | MCP Connection |
|-------|----------|----------------|
| data-neo4j | Neo4j graph databases | Karelin Neo4j (`mcp.karelin.com/neo4j`) |
| data-sql | Relational databases (PostgreSQL, MySQL, SQLite) | DBHub (`dbhub`) |

## Routing

- **"cypher", "graph", "nodes", "relationships", "neo4j"** → data-neo4j
- **"SQL", "postgres", "mysql", "tables", "select", "query the database"** → data-sql
- **"explore data", "what databases"** → list available servers from both sub-skills, ask user
