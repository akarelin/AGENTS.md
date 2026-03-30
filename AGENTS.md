# Autonomous agent instructions

This file contains instructions for autonomous agents working in the RAN and CRAP repositories.

## Multi-Agent System

This repository uses Claude Code's native multi-agent system configured in `.claude-code.yaml`. Specialized subagents handle specific tasks automatically:

### Available Agents
- **knowledge-management-agent**: Parent agent for documentation tasks
  - Spawns: changelog, docs, archive, validation agents
- **changelog-agent**: CHANGELOG.md management
- **push-agent**: Git operations and commits
- **archive-agent**: Code archival and cleanup
- **validation-agent**: Standards compliance
- **docs-agent**: README and documentation updates
- **mistake-review-agent**: Error pattern analysis

### Agent Invocation
Agents are triggered automatically by keywords in conversation or manually via:
```
/agents changelog
/agents knowledge-management
/agents push
```

For detailed agent information, see `/home/alex/RAN/agents/` directory.

## Session Management Commands

### Start of Session: "What's next?"
When user asks "What's next?" or similar at session start:
1. Read 2Do.md for current priorities and status
2. Check ROADMAP.md for active epics
3. Run git status to check for work in progress
4. Present a concise summary and wait for approval

### Session Commands

#### "Close" - End session and prepare for next
When user says "close":
1. Update 2Do.md with current progress and next steps
2. Archive any completed work to appropriate directories
3. Document any new mistakes in AGENTS_mistakes.md
4. Clean up temporary files if any
5. Provide summary of what's prepared for next session

#### "Document" - Detect and record changes
When user says "document":
1. Run git diff to detect all changes
2. Identify changes made by humans or other agents
3. Update CHANGELOG.md with discovered changes
4. Update relevant documentation as needed

#### "Push" - Git operations
When user says "push":
1. Ensure CHANGELOG.md is updated
2. Commit all changes with appropriate message
3. Push to repository
4. Create PR if on feature branch

### Command Combinations
- **"Close and push"**: End session + commit/push all work
- **"Document and push"**: Record external changes + commit/push

## Tool Use Guidelines
If prompt asks for an action (Fix or Create) should just be done. If tools are not working as expected - ask me to fix first.
If prompt asks for research (Research, explain or why) - you can respond with text to read.

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

## Skills (Claude Code Plugins)

Custom skills are in the `skills/` directory, each as `skills/<name>/SKILL.md` with Python implementations.

| Skill | Type | Description |
|-------|------|-------------|
| **m365** | user-invocable | User-level M365 operations: Mail, Calendar, Teams Chat, Channels, Files, Tasks, Contacts, OneNote, Meetings, Presence |
| **m365-admin** | user-invocable | Tenant admin: Users, Groups, Teams, Licenses, Directory Roles, Audit, Devices, Domains, Security |

Both skills use Microsoft Graph beta API with client credentials flow. Credentials are stored in Azure Key Vault (`karelin`).

## Precedence
This AGENTS.md file takes precedence over CLAUDE.md or GEMINI.md files in other repositories when working across multihomed workspaces.

## Repository-Specific Rules
### _ (Obsidian Vault)
**CRITICAL: This repository should ONLY be pulled on Alex-Surface.**
- **NEVER** pull this repository on any other host
- **NEVER** make changes to this repository from any host other than Alex-Surface
- **Reason:** Uses Obsidian native sync - git operations create sync conflicts
### RAN
**CRITICAL: NEVER search from `/` (root) unless the user explicitly requests it.**

## File Operation Rules
### Protected Files
- **NEVER move .code-workspace files** - These should remain in root for easy access
- **NEVER modify .gitignore without explicit permission** - Changes can result in loss of important files with keys
- **NEVER delete documentation files (.md) without explicit archiving or permission** - Always preserve history
- **DO NOT TOUCH Y2/ad_unibridge/Creekview directory** - This is production and should not be modified

### File Movement Guidelines
- **Configuration and token files should be colocated with the code that uses them**
- **Before moving any file, search for related files that use it** - Validate dependencies first
- **When file location is not specified, consider repository context** - Global files go in repo root

## Workflow Rules
### Git Operations
- **Create feature branch before starting major restructuring** - Never commit major changes directly to master

### Plan Execution
- **Follow each phase EXACTLY - do not jump ahead or add extras** - Respect phase boundaries
- **When a plan mentions something in a later phase, DO NOT implement it early** - Maintain discipline

## Mistake Handling Process

### When Mistakes Occur
1. **Recognize immediately** - As soon as you realize an error was made
2. **Document in AGENTS_mistakes.md** - Add entry before continuing work
3. **Apply fix if possible** - Correct the mistake in the same session
4. **Learn from pattern** - Check if similar mistakes exist in AGENTS_mistakes.md

### AGENTS_mistakes.md Format
Each mistake entry must include:
- **Date and context** - When and during what task
- **What happened** - Factual description of the error
- **Why it was wrong** - Impact and violation of guidelines
- **Lesson learned** - Key takeaway to prevent recurrence
- **Fix applied/needed** - How it was or should be corrected

### Purpose of AGENTS_mistakes.md
- **Learning repository** - Not just a log, but a teaching tool
- **Pattern detection** - Identify repeated error types
- **Instruction improvement** - Feed back into AGENTS.md updates
- **Continuity** - Help future sessions avoid past mistakes

### Critical Rule
**ALWAYS document mistakes AS THEY HAPPEN, not after being asked about them**

## Commands
### Validate
- When the user says "Validate", validate the results/output of the session for correctness and adherence to AGENTS.md/CLAUDE.md guidelines, and produce a summary report of findings

### Compress changelog
- When requested, reorganize CHANGELOG.md by moving verbose details to CHANGELOG_VERBOSE.md or subdirectory-specific CHANGELOG.md files
- Maintain high-level summaries in root CHANGELOG.md with references to detailed changelogs
- See CLAUDE.md for detailed compression instructions

### Archive outdated code
When user requests to "archive outdated code":
1. **Identify files to archive**:
   - Old versions of refactored code
   - Deprecated features or approaches  
   - Failed experiments (with notes)
   - Loose files in wrong directories
   - Temporary work and session files

2. **Create archive structure**:
   ```
   archive/
   ├── README.md      # Inventory with dates and reasons
   ├── legacy/        # Old but working code
   ├── experiments/   # Failed attempts
   ├── misc/          # Miscellaneous files
   └── workspaces/    # IDE workspace files
   ```

3. **Move files with context**:
   - Add entry to archive/README.md
   - Include date archived and reason
   - Preserve directory structure if relevant

4. **Update main README.md** to note archived content

5. **Commit**: "Archive outdated code and documentation"

**Important**: Archive, don't delete. History is valuable.

### Archiving Best Practices

#### When to Archive vs Delete

**Archive:**
- Previous versions of refactored code
- Deprecated but historically important features
- Failed experiments with learning value
- Old documentation that provides context
- Configuration files from previous setups

**Delete:**
- Generated files (*.pyc, __pycache__)
- Temporary files
- Log files (after backing up if needed)
- Duplicate files with no unique value

#### Standard Archive Structure
```
project/
└── archive/
    ├── README.md          # REQUIRED: Inventory of all archived items
    ├── legacy/            # Old versions of current code
    │   └── v1/
    │       └── [files]
    ├── experiments/       # Failed or abandoned attempts
    │   └── [experiment_name]/
    │       ├── README.md  # What was tried and why it failed
    │       └── [files]
    ├── misc/             # Miscellaneous files
    │   └── [loose files moved from root]
    └── docs/             # Old documentation
        └── [outdated docs]
```

#### Archive README Template
Each archive must have README.md with:
- Table of contents
- For each item:
  - Date archived
  - Original location
  - Reason for archiving
  - Brief description
  - Any warnings or notes

#### Handling Loose Files
Common loose files in root directories:
- Test scripts → archive/experiments/ or tests/
- Old configs → archive/legacy/configs/
- Workspace files → archive/workspaces/
- Contact/CRM files → Move to appropriate project
- Documentation → docs/ or archive/docs/

#### Archive Naming Conventions
- Use dates: `archive/legacy/v1_20250128/`
- Be descriptive: `archive/experiments/mqtt_bridge_attempt/`
- Keep extensions: Don't rename files during archiving

#### Git Considerations
- Always commit before major archiving
- Use descriptive commit messages
- Consider .gitignore for large archived files
- Tag releases before major reorganizations

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

## Documentation Standards

### Documentation Templates
Standard templates are available in `/home/alex/RAN/docs/templates/`:
- **README_TEMPLATE.md**: Standard format for project README files
- **AGENTS_TEMPLATE.md**: Template for project-specific agent instructions
- **ARCHIVE_README_TEMPLATE.md**: Template for archive inventory documentation

### Documentation Rules
1. **README.md is for humans**: Move all human-readable documentation from AGENTS.md to README.md
2. **AGENTS.md is for agents only**: Keep only agent-specific instructions and commands
3. **No duplication**: Reference parent documentation when appropriate
4. **Archive structure**: Every archive directory must have a README.md inventory
5. **One screen rule**: README files should fit on one screen when possible

### Archiving Standards
When archiving code or documentation:
1. Create structured archive directories (legacy/, experiments/, misc/, workspaces/)
2. Always include an archive README.md with inventory
3. Document date archived and reason
4. Update references in main documentation
5. Preserve history - never delete

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
When the user requests to "compress changelog", reorganize CHANGELOG.md by moving verbose details to appropriate locations while maintaining a concise summary in the root. All removed items should be moved to either CHANGELOG_VERBOSE.md in the same directory, or to subdirectory-specific CHANGELOG.md files (e.g., Mailstore-related tasks go to Mailstore/CHANGELOG.md). The root CHANGELOG.md should contain high-level summaries with references to subdirectory changelogs using "See {path}/CHANGELOG.md for details". Search for existing CHANGELOG.md files in subdirectories and add summaries of their changes to the root if not already present. Preserve all contributor names exactly as they appear (e.g., [Claude], [Alex], [Manus]) and maintain the same date ordering. The compressed root CHANGELOG.md should provide an overview that helps users quickly understand what changed without overwhelming detail.

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
