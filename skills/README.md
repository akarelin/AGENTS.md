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
/plugin install skill-manager@akarelin-skills
```

## Available Plugins

| Plugin | Description | Platform |
|--------|-------------|----------|
| **everything-search** | Fast file search via voidtools Everything MCP server | Windows |
| **organize** | File organizer with sub-skills (arxiv papers, medical scans) | Any |
| **session-manager** | Sync/list/resume/clean Claude sessions across repos | Any (Python 3) |
| **skill-manager** | Patch, test, rebuild, and deploy plugin skills | Any |

## Plugin Details

### everything-search
MCP server wrapping [voidtools Everything](https://www.voidtools.com/) for instant filename search. Requires Everything running on Windows with `es.exe` in PATH.

### organize
File organizer with a sub-skill architecture. Sub-skills included:
- **organize-arxiv** — identifies arxiv PDFs by filename or page-1 text, fetches metadata, renames with `{id} {#tags} {Title} {version}.pdf`, moves to library
- **medical-scan-obsidian** — converts medical scan images into a structured bilingual EN/RU Obsidian vault with discharge notes, per-study notes, and diagnostics summary

### session-manager
CLI tool for managing Claude Code session folders across multiple repos and hosts. Supports sync, list, resume, rename, and cleanup operations.

### skill-manager
End-to-end workflow for improving plugin skills: gather feedback, patch code, test, rebuild `.plugin` files, and deploy.
