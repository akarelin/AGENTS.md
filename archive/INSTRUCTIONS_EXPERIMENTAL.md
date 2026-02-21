# Experimental Instructions (Use Only When Requested)

**NOTE**: These are experimental features created during development sessions. Only use these instructions when explicitly asked by the user. Default to core instructions shared by all projects (RAN/CLAUDE.md).

## Enhanced Git Workflow

### Session Management
- Create branch for every session: `session-YYYY-MM-DD-HHMMSS` or `session-{description}`
- Auto-commit when git diff shows >4k changes during session
- Push session branch regularly after each auto-commit
- Track cumulative changes throughout session

### Session Startup Protocol
1. Check for unpushed branches with `git branch -r --no-merged`
2. For each unmerged branch, show summary and ask user:
   - "Merge this branch"
   - "Delete this branch" 
   - "Keep for later"
   - "Create PR now"

### Session Finalization
- Auto-commit on phrases like "finalize and close", "finish up", "wrap this up", "end session"
- Create final commit with comprehensive session summary
- Push branch to remote
- Create PR using `gh pr create` with:
  - Summary of all changes in session
  - List of files modified/created
  - Key accomplishments
  - Standard Claude Code attribution

### PR Creation Template
```
## Summary
[1-3 bullet points of main changes]

## Files Changed
- Created: [list]
- Modified: [list]
- Deleted: [list]

## Key Accomplishments
[List of major features/fixes implemented]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Advanced Contact Management Features
- Intelligent contact linking with confidence scoring
- Multi-source import with automatic deduplication
- Web UI for merge review workflow
- Batch processing operations
- Advanced search and filtering

## Conflict Resolution
When experimental features conflict with core instructions:
1. Pause and notify user of conflict
2. Offer options: use core behavior, override with experimental, or skip experimental
3. Always default to core instructions unless user explicitly chooses experimental