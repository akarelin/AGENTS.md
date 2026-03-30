---
name: search-everything
description: >
  This skill should be used when the user asks to "search for files",
  "find files by name", "locate a file", or needs fast filename search
  on Windows using voidtools Everything. Provides instant file search
  via the Everything MCP server.
---

# Everything Search

Fast file search on Windows using voidtools Everything (1.4 and 1.5a) via the `es.exe` CLI, exposed as an MCP server.

## Requirements

- Windows only
- [voidtools Everything](https://www.voidtools.com/) installed and running
- `es.exe` CLI tool in PATH (typically `C:\Program Files\Everything 1.5a\`)

## How It Works

The plugin registers an MCP server that wraps `uvx mcp-everything-search`.
Claude can then use the search tools to find files by name, path, extension, or regex.

## Configuration

- **EVERYTHING_INSTANCE**: Instance name for Everything 1.5a (leave empty for 1.4)
- **es_exe_dir**: Folder containing `es.exe`
