# everything-search

Fast file search using [voidtools Everything](https://www.voidtools.com/) (1.4 and 1.5a) via MCP server.

## Requirements

- Windows
- voidtools Everything installed and running
- `es.exe` CLI tool (typically at `C:\Program Files\Everything 1.5a\`)

## Installation

```
/plugin install everything-search@akarelin-skills
```

The plugin registers an MCP server that wraps `uvx mcp-everything-search`, giving Claude access to instant filename search across all indexed drives.
