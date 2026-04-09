---
name: data-sql
description: >
  Relational database exploration via SQL. Use when the user mentions
  SQL, PostgreSQL, MySQL, SQLite, tables, queries, or relational database
  exploration.
---

# SQL Data Exploration

Interactive relational database exploration via DBHub MCP server.

## MCP Connection

Uses DBHub — a zero-dependency, multi-database MCP server:
```json
{
  "dbhub": {
    "command": "npx",
    "args": [
      "@bytebase/dbhub@latest",
      "--transport", "stdio",
      "--dsn", "${DB_DSN}"
    ]
  }
}
```

For Docker deployment (HTTP transport):
```bash
docker run --rm --init --name dbhub --publish 8080:8080 \
  bytebase/dbhub --transport http --port 8080 \
  --dsn "postgres://user:password@host:5432/dbname?sslmode=disable"
```

Supports: PostgreSQL, MySQL, MariaDB, SQL Server, SQLite.

## Available Tools

| Tool | Description |
|------|-------------|
| `execute_sql` | Execute SQL queries (read/write with transaction support) |
| `search_objects` | Explore schema — tables, columns, indexes, procedures |

## DSN Format

```
postgres://user:password@host:5432/dbname?sslmode=disable
mysql://user:password@host:3306/dbname
sqlite:///path/to/database.db
```

## Workflow

1. Determine which database the user wants to explore
2. Resolve credentials from Key Vault if available (`get_secret`)
3. Use `search_objects` to explore schema (tables, columns)
4. Execute SQL queries with `execute_sql`
5. Present results in readable format

## Known Databases

Credentials in Key Vault:
- `airflow-postgres-gcp` — Airflow metadata DB (GCP)
- `airflow-postgres-trix` — Airflow metadata DB (Trix)
- `emails-database-url` — Email processing DB
- `neon-postgres-connection-url` — Neon serverless Postgres
