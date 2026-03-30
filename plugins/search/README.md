# search

Search plugin with two sub-skills for local file search and Microsoft 365 search.

## Installation

```
/plugin install search@akarelin-skills
```

## Sub-skills

### search-everything
Fast local file search on Windows using [voidtools Everything](https://www.voidtools.com/) via MCP server. Requires Everything running. Provides 16 MCP tools: filename search, regex, filters, type search, recent files, duplicates, large files, and more.

Also available as standalone MCPB desktop extension (`search-everything-0.4.0.mcpb`).

### search-m365
Cross-entity Microsoft 365 search via Graph `/search/query` API. Searches emails, files, events, chat messages, and SharePoint in one query. Requires `work-m365` plugin.
