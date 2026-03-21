# Autonomous agent instructions

This file contains instructions for autonomous agents working in the RAN and CRAP repositories.

## Tool Use Guidelines
If prompt asks for an action (Fix or Create) should just be done. If tools are not working as expected - ask me to fix first.
If prompt asks for research (Research, explain or why) - you can respond with text to read.

### Important Reminders
- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User

### Efficient Tool Usage
- **Batch Operations**: When multiple independent operations are needed, execute them in parallel using multiple tool calls in a single response
- **Minimize Context**: Avoid unnecessary file reads - use grep/search tools first to locate specific content
- **Direct Action**: For fix/create requests, proceed directly without asking for confirmation
- **Tool Failures**: If a tool fails unexpectedly, inform the user and ask for guidance rather than retrying repeatedly
- **Search Strategy**: Use targeted searches (grep, glob) before broad file reads to conserve context

### Tool Selection Priority
1. **For Finding Files**: Glob → Grep → Read
2. **For Code Search**: Grep with specific patterns → Read specific files
3. **For Modifications**: Edit for small changes → MultiEdit for multiple changes → Write only for new files
4. **For Research**: WebSearch → WebFetch → Read documentation files

## Precedence
This AGENTS.md file takes precedence over CLAUDE.md or GEMINI.md files in other repositories when working across multiple repositories.

## Repository-Specific Rules
### _ (Obsidian Vault)
**CRITICAL: This repository should ONLY be pulled on Alex-Surface.**
- **NEVER** pull this repository on any other host
- **NEVER** make changes to this repository from any host other than Alex-Surface
- **Reason:** Uses Obsidian native sync - git operations create sync conflicts
### RAN
**CRITICAL: NEVER search from `/` (root) unless the user explicitly requests it.**

## Commands
Note: _push_ and _close_ are used interchangably.

### Finalize and push
- Reread instructions in AGENTS.md
- Update CHANGELOG, commit and push

### Document and push  
- Review all changes made by agents and by user
- Reread instructions in AGENTS.md
- Update CHANGELOG.md with changes, commit and push

### Overview
- When user requests "overview" or "current status", use the specialized [Overview Agent](./agents/overview.md)
- Provides comprehensive repository status with visual formatting
- Identifies active projects, archival candidates, and actionable recommendations
- Includes interactive archival selection with ✅ checkboxes

### Validate
- When the user says "Validate", validate the results/output of the session for correctness and adherence to AGENTS.md guidelines, and produce a summary report of findings

### Compress changelog
- When requested, reorganize CHANGELOG.md by moving verbose details to CHANGELOG_VERBOSE.md or subdirectory-specific CHANGELOG.md files
- Maintain high-level summaries in root CHANGELOG.md with references to detailed changelogs
- See CLAUDE.md for detailed compression instructions

### Archive outdated code
When user requests to "archive outdated code" or mentions projects/files are cancelled/deprecated, use the specialized [Archiving Agent](./agents/archiving.md).

**Quick Summary**:
1. **Identify files to archive** using patterns and age criteria
2. **Create centralized archive structure** with proper categorization
3. **Document thoroughly** with start dates, end dates, and project context
4. **Preserve history and learnings** for future reference

**Important**: Archive, don't delete. History is valuable. Use one centralized archive per repository.

**Detailed Procedures**: See [agents/archiving.md](./agents/archiving.md) for complete workflow, naming conventions, and quality checklist.

### Archive README Guidelines
Archive README.md must include:
- **Archive Contents Table**: Type, Name, Status, Start/End dates, Description
- **Archive Tree**: Required when projects span multiple folders (folders only, no files)
- **Quick Navigation**: Links to Legacy Code, Projects, Experiments, Miscellaneous sections
- **Statistics**: Total items count by category

## README.md Best Practices

### README.md Organization
- **Every project** must have a README.md in its root folder
- **Start with**: One-line description, then annotated folder structure
- **Keep concise**: Should fit on one screen when possible
- **Include essential sections**:
  - Project title and one-line description
  - Directory structure with → navigation hints
  - Quick Start (3-5 steps max)
  - Key features or components
  - Dependencies/Requirements

### README.md Format Guidelines
- Use clear, concise language
- Include code examples in fenced code blocks with language syntax highlighting
- Add badges for build status, version, license (if applicable)
- Use relative links for referencing other docs in the repo
- Keep it updated - README should reflect current state of the project
- Avoid walls of text - use headers, lists, and formatting for readability

### README.md Examples
For scripts/tools:
```markdown
# Tool Name

Brief description of what the tool does.

## Requirements
- Python 3.8+
- Required packages: see requirements.txt

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python tool_name.py [options]
```

## Options
- `--help`: Show help message
- `--verbose`: Enable verbose output
```

## File Migration Note
When encountering CLAUDE.md files in subdirectories:
- Merge unique content into corresponding AGENTS.md
- Leave note in CLAUDE.md referring to AGENTS.md
- Do not delete CLAUDE.md files

## Workflow
1. Make code changes
2. Update CHANGELOG.md with changes
3. For each changed file, if it has version constant defined, increment version 
4. Commit and push both together
5. **ALWAYS push at end of session** - Never leave commits unpushed when closing Claude Code
6. CHANGELOG.md serves as checkpoint for context continuity

## Signatures
**IMPORTANT**: The signature in commit messages should reflect who made the actual code changes, not who is documenting them:
When generating checkin comments use following template for signature: `🤖 Generated by {agent}@karelin.ai`. Valid agents include: codex, claude, gemini.
- Use `[Alex]` for user changes when the username is unknown
- If the user made the changes: Do NOT sign with {agent}@karelin.ai
- When documenting existing user changes, the commit author is still the user

## CHANGELOG.md Usage
**MANDATORY:** Always maintain and update CHANGELOG.md for checkpoint tracking.

### When to Update CHANGELOG.md:
- **On every commit/checkin**: Document what was changed and why (even if changes were made outside Claude Code)
- **On session close**: Summarize session work and decisions made
- **On session autocompact**: Record state before context reset
- **When reviewing existing changes**: If you discover uncommitted or recent changes, update CHANGELOG.md to document them

### CHANGELOG.md Organization:
- **Every project** should maintain its own CHANGELOG.md in the project's root folder
- **Project modules** can have their own CHANGELOG.md in their respective subfolders
- **Root CHANGELOG.md** serves as a succinct summary of all changes across all project CHANGELOG.md files
- This hierarchical structure ensures detailed history is preserved at the project level while maintaining a high-level overview at the repository root

### Compress CHANGELOG.md:
When the user requests to "compress changelog", reorganize CHANGELOG.md by moving verbose details to appropriate locations while maintaining a concise summary in the root. All removed items should be moved to either CHANGELOG_VERBOSE.md in the same directory, or to subdirectory-specific CHANGELOG.md files (e.g., Mailstore-related tasks go to Mailstore/CHANGELOG.md). The root CHANGELOG.md should contain high-level summaries with references to subdirectory changelogs using "See {path}/CHANGELOG.md for details". Search for existing CHANGELOG.md files in subdirectories and add summaries of their changes to the root if not already present. Preserve all contributor names exactly as they appear (e.g., [Claude], [Alex]) and maintain the same date ordering. The compressed root CHANGELOG.md should provide an overview that helps users quickly understand what changed without overwhelming detail.

### CHANGELOG.md Format:
- Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
- Use semantic versioning principles
- Analyze all changes made by agents and by user
- Document important changes with reasoning. 
- Do not document trivial changes like "Updated imports" or "Version incremented"
- For all changes identify if it was a fix, feature or refactoring.
- For Fixes, include the specific issue or bug fixed
- For Changes. Classify changes as Added, Changed, Fixed, or Removed.
- For Refactoring, explain the structural changes and their purpose
- **Version autoincrement**: 
  - If not new features were introduced, increment the patch version (e.g., 1.0.0 -> 1.0.1)
  - If new features were introduced, increment the minor version (e.g., 1.0.0 -> 1.1.0)
- **Version Headers**: Use actual version numbers instead of [Unreleased]
  - Version locations are documented in module-specific AGENTS.md files
- **Changed Section**: Actually describe what was changed, not just "Modified X"
- **Mark the author of changes**: Indicate who made the changes:
  - `[Alex]` - Manual changes by user 
  - `[Claude]` - Changes made by Claude Code
  - `[LLM:ModelName]` - Changes by other LLMs (specify model)
  - `[System]` - Git operations (merge, reflog, rebase, etc.)
  - `[Script]` - Automated scripts or batch operations

#### CHANGELOG.md bad example:
```markdown
- [Alex] y2.py - Updated to use new module structure:
  - Imports ADEntity, group_state, binary_state, sync_wrapper from y2util
  - Imports State, glob_list, _protocol_Entity from y2env
- [Alex] Y2_insteon.py - Updated imports:
  - Added y2util import for safe_int_from_state
  - Imports VER_Y2 and State from y2env
  - Uses VER_Y2 for version property
- [Alex] Y2_debug_ui.py - Updated imports:
  - Added y2util import for entity_state_age
  - Imports State and Environment from y2env
- [Alex] gppu.py - Version incremented:
  - Updated from 2.13.0 to 2.14.0.250213
```

#### CHANGELOG.md good example:
```markdown
  ## 2.14.0.250213 [2025-05-30]

  ### Features
    - Brand new two-tier storage system for email messages    
      -  [Alex] Designed two-tier storage system (raw + normalized) for email messages
      -  [Alex] Created comprehensive PostgreSQL schema with full-text search and JSONB support
      -  [Alex] Implemented universal message database supporting email, iMessage, Telegram, WhatsApp, SMS
      -  [Alex] Added provenance tracking system for complete data lineage
      -  [Alex] Built flexible configuration system with environment variable support
      -  [Alex] Created production-ready schema with optimized indexes and triggers

  ### Enhancements
    - [Claude] Mailstore Deduplication: Enhanced fs_dedup3.py with batch processing and improved error handling
    - [Claude] Added --batch parameter support for range specification (e.g., --batch 10-20)
    - [Claude] Improved deletion process with silent handling of missing records
    - [Claude] Enhanced user experience for large-scale deduplication operations
  
  ### Fixes
    - [Claude] Mailstore fs_dedup3.py: Fixed critical bugs in folder analysis and tag detection
    - [Claude] Fixed 'list' object has no attribute 'items' error by correcting fs.folders.items() to fs.folder_map.items()
```
