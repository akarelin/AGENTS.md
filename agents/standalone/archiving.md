# Archiving Agent Instructions

This document contains specialized instructions for the Archiving Agent, designed to handle all archival tasks following the comprehensive guidelines in [ARCHIVAL.md](../ARCHIVAL.md).

## Agent Purpose

The Archiving Agent handles systematic archival of outdated code, cancelled projects, deprecated configurations, and obsolete files while preserving project history and maintaining proper documentation.

## Core Procedures

### Project Archival Workflow

When a user requests to archive a project or says a project is cancelled:

1. **Identify Archive Target**
   - Determine if it's a project, script collection, legacy code, or miscellaneous files
   - Check current location and structure

2. **Apply Proper Naming Convention**
   - Projects: `project-name.{status}/` where status is:
     - `.completed` - Successfully finished projects
     - `.cancelled` - Projects abandoned by user decision  
     - `.paused` - Temporarily suspended projects
   - Scripts: `script-name.{status}/` where status is:
     - `.saved` - No longer used but contain important knowledge
     - `.superseded` - Replaced by newer versions
     - `.obsolete` - No longer relevant

3. **Move to Proper Archive Location**
   ```bash
   # Projects go to archive/projects/
   mv projects/project-name archive/projects/project-name.cancelled/
   
   # Legacy code goes to archive/legacy/
   mv old-configs archive/legacy/services/old-configs-YYYY-MM-DD/
   
   # Scripts go to archive/scripts/
   mv old-script archive/scripts/script-name.saved/
   ```

4. **Update Archive Inventory**
   - Add entry to archive contents table in `archive/README.md`
   - Update archive tree structure
   - Add detailed documentation section
   - Update archive statistics

5. **Document in CHANGELOG.md**
   - Add entry with proper format: `[YYYY-MM-DD] - {Description}`
   - Use "Changed" section for archival actions
   - Include reason for archival and what was moved

### Archive Documentation Requirements

#### Archive Contents Table Format
```markdown
| Type | Name | Status | Start | End | Description |
|------|------|--------|-------|-----|-------------|
| Project | Project Name | CANCELLED | YYYY-MM-DD | YYYY-MM-DD | Brief description and reason |
```

#### Archive Tree Requirements
- Required when projects span multiple folders
- Shows folder structure only (no individual files)
- Update whenever archive structure changes

#### Detailed Documentation Sections
Each archived item must have:
- **Status**: Current state (CANCELLED, COMPLETED, SUPERSEDED, etc.)
- **Start Date**: When project/feature began
- **End Date**: When archived (today's date)
- **Description**: What the item was and its purpose
- **Reason**: Why it was archived (if cancelled/superseded)

### Date Tracking Guidelines

#### Determining Start Dates
1. Check git history: `git log --reverse --oneline path/to/file | head -1`
2. Look for creation timestamps
3. Check CHANGELOG.md entries
4. Use earliest evidence of project existence

#### End Dates
- Always use archival date (today)
- Represents when item was deprecated/cancelled/superseded

### Roadmap Management

When archiving projects referenced in ROADMAP.md:
1. Remove project details from roadmap
2. Update active projects section
3. If no active projects remain, show: `*No active projects currently*`
4. Maintain roadmap structure for future projects

### Error Recovery

If archival process encounters issues:
1. **Incomplete moves**: Complete the move operation first
2. **Missing documentation**: Add required entries to archive/README.md
3. **Changelog missing**: Add proper CHANGELOG.md entry
4. **Statistics wrong**: Recalculate and update archive statistics

## Quality Checklist

Before completing archival task, verify:
- [ ] Item moved to correct archive subdirectory with proper naming
- [ ] Archive contents table updated with new entry
- [ ] Archive tree updated if structure changed  
- [ ] Detailed documentation section added
- [ ] Archive statistics updated (total count, category counts)
- [ ] CHANGELOG.md entry added with proper format
- [ ] Any references in active codebase updated/removed
- [ ] ROADMAP.md updated if project was listed there

## Integration with AGENTS.md

This agent should be referenced from the main AGENTS.md file under the "Archive outdated code" command section. The main instructions should point to this specialized agent documentation for detailed procedures.

## File Structure Requirements

When archiving, maintain this structure:
```
archive/
├── README.md           # Central inventory (maintained by this agent)
├── legacy/             # Superseded working code
├── projects/           # Project archives with status extensions
├── scripts/            # Script collections with status extensions  
├── experiments/        # Failed attempts and POCs
└── misc/              # Backup files and orphaned items
```

## Automation Guidelines

### Use TodoWrite Tool
Always use TodoWrite to track archival progress:
1. Identify what needs to be archived
2. Move files to proper locations  
3. Update archive documentation
4. Update CHANGELOG.md

### Batch Operations
When archiving multiple items:
- Process similar items together (all projects, then scripts, etc.)
- Update documentation after each major category
- Use parallel operations where possible

### Validation
After archival:
- Verify all files moved successfully
- Check that no broken references remain
- Confirm archive inventory is accurate and complete

## Common Scenarios

### Project Cancellation
```bash
# User says: "Project X is cancelled. Archive it."
1. mv projects/project-x archive/projects/project-x.cancelled/
2. Update archive/README.md with CANCELLED status
3. Remove from ROADMAP.md if present
4. Add CHANGELOG.md entry explaining cancellation
```

### Legacy Code Replacement
```bash  
# User says: "Archive old configs, they're replaced by new system"
1. mv Services/old-configs archive/legacy/services/old-configs-YYYY-MM-DD/
2. Update archive/README.md with SUPERSEDED status
3. Add CHANGELOG.md entry explaining replacement
4. Leave reference file if needed
```

### Experimental Code Cleanup
```bash
# User says: "Archive failed experiments"
1. mv failed-feature archive/experiments/failed-features/feature-name/
2. Update archive/README.md with learning notes
3. Document what was learned and why it failed
4. Add CHANGELOG.md entry
```

This agent ensures consistent, thorough archival following all established guidelines while preserving valuable project history and maintaining system organization.