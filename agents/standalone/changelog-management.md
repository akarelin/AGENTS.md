# Changelog Management Guidelines
## When to Update CHANGELOG.md:
- **On every commit/checkin**: Document what was changed and why (include all changes)
- **On session close**: Summarize session work and decisions made
- **On session autocompact**: Record state before context reset
- **When reviewing existing changes**: If you discover uncommitted or recent changes, update CHANGELOG.md to document them

## CHANGELOG.md Organization:
- **Every project** should maintain its own CHANGELOG.md in the project's root folder
- **Project modules** can have their own CHANGELOG.md in their respective subfolders
- **Root CHANGELOG.md** serves as a succinct summary of all changes across all project CHANGELOG.md files
- This hierarchical structure ensures detailed history is preserved at the project level while maintaining a high-level overview at the repository root

## Compress CHANGELOG.md:
When the user requests to "compress changelog", reorganize CHANGELOG.md by moving verbose details to appropriate locations while maintaining a concise summary in the root. All removed items should be moved to either CHANGELOG_VERBOSE.md in the same directory, or to subdirectory-specific CHANGELOG.md files (e.g., Mailstore-related tasks go to Mailstore/CHANGELOG.md). The root CHANGELOG.md should contain high-level summaries with references to subdirectory changelogs using "See {path}/CHANGELOG.md for details". Search for existing CHANGELOG.md files in subdirectories and add summaries of their changes to the root if not already present. Preserve all contributor names exactly as they appear (e.g., [Claude], [Alex], [Manus]) and maintain the same date ordering. The compressed root CHANGELOG.md should provide an overview that helps users quickly understand what changed without overwhelming detail.

## CHANGELOG.md Format:

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
  - `[{agent}]` - Changes made by agent
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