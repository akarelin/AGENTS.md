# akarelin-skills — Claude Code Plugin Marketplace

Personal productivity plugins for Claude Code.

## Installation

```bash
# Add the marketplace
/plugin marketplace add akarelin/AGENTS.md --path skills

# Browse available plugins
/plugin marketplace list akarelin-skills

# Install individual plugins
/plugin install everything-search@akarelin-skills
/plugin install organize@akarelin-skills
/plugin install session-manager@akarelin-skills
/plugin install medical-scan-organizer@akarelin-skills
/plugin install skill-manager@akarelin-skills
```

## Available Plugins

| Plugin | Description | Platform |
|--------|-------------|----------|
| **everything-search** | Fast file search via voidtools Everything MCP server | Windows |
| **organize** | File organizer with sub-skills (includes arxiv paper organizer) | Any (PyMuPDF) |
| **session-manager** | Sync/list/resume/clean Claude sessions across repos | Any (Python 3) |
| **medical-scan-organizer** | Medical scans → bilingual Obsidian vault | Any |
| **skill-manager** | Patch, test, rebuild, and deploy plugin skills | Any |

## Plugin Details

### everything-search
MCP server wrapping [voidtools Everything](https://www.voidtools.com/) for instant filename search. Requires Everything running on Windows with `es.exe` in PATH.

### organize
File organizer with a sub-skill architecture. The meta-organizer discovers `organize-*` sub-skills, runs each one's scan on the target folder, presents a combined plan, and executes on approval. Currently includes **organize-arxiv** — identifies arxiv PDFs by filename or page-1 text, fetches metadata from the arxiv API, renames with `{id} {#tags} {Title} {version}.pdf`, and moves to a structured library.

### session-manager
CLI tool for managing Claude Code session folders across multiple repos and hosts. Supports sync, list, resume, rename, and cleanup operations.

### medical-scan-organizer
Converts medical scan images (discharge instructions, diagnostic studies, lab reports) into a structured Obsidian vault with bilingual EN/RU notes, per-study summaries, and a Map of Content.

### skill-manager
End-to-end workflow for improving plugin skills: gather feedback, patch code, test, rebuild `.plugin` files, and deploy.
