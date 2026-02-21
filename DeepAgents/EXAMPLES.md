# DAPY - Usage Examples

This document provides practical examples of using DAPY for common workflows.

## Table of Contents

- [Basic Commands](#basic-commands)
- [Development Workflow](#development-workflow)
- [Knowledge Management](#knowledge-management)
- [Advanced Features](#advanced-features)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)

---

## Basic Commands

### Check What's Next

Start your session by checking priorities:

```bash
dapy next
```

**Output:**
```markdown
# What's Next

## Current Priorities

- Implement user authentication
- Fix bug in data processing pipeline
- Update documentation for API changes
- Review pull requests from team

## Git Status

- Branch: feature/auth-system
- Status: 3 staged files, 2 unstaged files

## Recommended Next Steps

**Complete work in progress:**
  - Uncommitted changes in 5 files

**Priority tasks from 2Do.md:**
  - Implement user authentication
  - Fix bug in data processing pipeline
  ... and 2 more tasks
```

### Ask a Question

Execute any query:

```bash
dapy ask "What files have changed since last commit?"
```

```bash
dapy ask "Update the changelog with recent changes"
```

```bash
dapy ask "Archive the old implementation in legacy/"
```

### Document Changes

Automatically update CHANGELOG.md from git diff:

```bash
dapy document
```

**Output:**
```markdown
# Changes Documented

## Detected Changes

- Modified dapy/cli.py
- Modified dapy/tools/changelog.py
- Added tests/test_changelog.py

## Actions Taken

- Detected 3 changed files
- Classified 3 changes
- Updated CHANGELOG.md: Added 3 entries

## Status

- CHANGELOG.md: Updated
```

### Close Session

End your work session:

```bash
dapy close
```

**Output:**
```markdown
# Session Closed Successfully

## Actions Taken

- Session analysis complete
- Git status: Branch: main, Staged: 0, Unstaged: 2, Untracked: 0
- Updated 2Do.md with session summary
- Checked for mistakes - none found
- Checked for files to archive - none found

## Status

- 2Do.md: Updated
- Mistakes: Checked
- Archive: 0 files archived

## Git Status

- Branch: main, Staged: 0, Unstaged: 2, Untracked: 0

## Ready for Next Session

Review 2Do.md for next steps.
```

### Push Changes

Commit and push with changelog verification:

```bash
dapy push "Implemented user authentication"
```

With pull request:

```bash
dapy push "Implemented user authentication" --pr
```

---

## Development Workflow

### Typical Session Flow

**1. Start Session:**
```bash
# Check what's next
dapy next

# Output shows:
# - Current priorities from 2Do.md
# - Work in progress from git status
# - Recommended next steps
```

**2. Work on Tasks:**
```bash
# Make changes to code
vim dapy/auth.py

# Test changes
pytest tests/test_auth.py
```

**3. Document Changes:**
```bash
# Update changelog automatically
dapy document

# Review generated changelog
cat CHANGELOG.md
```

**4. Commit and Push:**
```bash
# Push with changelog verification
dapy push "Implemented OAuth2 authentication"

# Or create PR
dapy push "Implemented OAuth2 authentication" --pr
```

**5. Close Session:**
```bash
# Update 2Do.md and prepare for next session
dapy close
```

### Feature Development Example

**Scenario:** Implementing a new feature

```bash
# 1. Check current status
dapy next

# 2. Create feature branch (manual)
git checkout -b feature/new-tool

# 3. Implement feature
# ... make changes ...

# 4. Test implementation
pytest

# 5. Document changes
dapy document

# 6. Review and commit
git diff
dapy push "Added new tool for X"

# 7. Create PR
dapy push --pr

# 8. Close session
dapy close
```

---

## Knowledge Management

### Archive Old Code

Archive outdated implementations:

```bash
dapy ask "Archive the old authentication code in legacy/"
```

**What happens:**
1. Tool identifies files to archive
2. Creates timestamped archive directory
3. Copies files to archive
4. Updates archive README.md with inventory
5. Returns summary

### Process Mistakes

Document a mistake for learning:

```bash
dapy ask "Document mistake: deleted production file without backup"
```

The system will:
1. Prompt for context and details
2. Check for similar past mistakes
3. Document in AGENTS_mistakes.md
4. Suggest prevention strategies

### Search Knowledge Base

Find information across markdown files:

```bash
dapy ask "Search for all references to authentication in docs"
```

```bash
dapy ask "Find TODO items in project documentation"
```

### Update Documentation

Update markdown files:

```bash
dapy ask "Update 2Do.md to mark authentication task as complete"
```

```bash
dapy ask "Add new section to ROADMAP.md about Q2 goals"
```

---

## Advanced Features

### Breakpoints

Pause execution at specific tools for inspection:

```bash
dapy ask "Archive old code" --breakpoint archive_tool
```

**Interactive Breakpoint Menu:**
```
BREAKPOINT

Tool: archive_tool

Arguments:
{
  "files": ["old_auth.py", "deprecated_utils.py"],
  "reason": "Replaced by new implementation",
  "archive_type": "legacy"
}

Current State (summary):
{
  "config": {...},
  "progress_updates": [...]
}

Options:
  c - Continue execution
  s - Skip this tool call
  a - Abort execution
  i - Inspect with debugger (pdb)
  m - Modify arguments

Action: _
```

### Multiple Breakpoints

Set breakpoints on multiple tools:

```bash
dapy ask "Update changelog and push" \
  --breakpoint changelog_tool \
  --breakpoint git_push_tool
```

### Custom Configuration

Use custom config file:

```bash
# Create config
cat > my-config.yaml << EOF
model: openai:gpt-4o-mini
debug: true
snapshot_enabled: false
auto_approve: true
EOF

# Use config
dapy --config my-config.yaml ask "What's next?"
```

### Debug Mode

Enable verbose output:

```bash
dapy --debug ask "Document changes"
```

**Output includes:**
```
-> Calling tool: git_status_tool
  Args: {}
<- Completed: git_status_tool (0.15s)
  Result: {'branch': 'main', 'dirty': True, ...}

-> Calling tool: git_diff_tool
  Args: {'staged': False}
<- Completed: git_diff_tool (0.23s)
  Result: {'diff': '...', 'files_changed': [...]}
```

### Disable Tracing

Turn off LangSmith tracing:

```bash
dapy --no-trace ask "What's next?"
```

### Auto-Approve All

Skip approval prompts:

```bash
dapy ask "Archive and push" --approve-all
```

---

## Debugging and Troubleshooting

### Diagnostics

Check system status:

```bash
dapy diag
```

**Output:**
```
DAPY Diagnostic Information

Configuration:
  model: openai:gpt-4o
  debug: False
  trace: True
  snapshot_enabled: True
  ...

Environment:
  LANGCHAIN_TRACING_V2: true
  LANGCHAIN_PROJECT: dapy-dev
  OPENAI_API_KEY: sk-proj-...

Checkpointer: SqliteSaver

Git Status:
  Branch: main
  Dirty: True
  Untracked files: 2
```

### Review Snapshots

Snapshots are saved to `./snapshots/` as JSON files:

```bash
# List recent snapshots
ls -lt snapshots/ | head -10

# View specific snapshot
cat snapshots/snapshot_tool_call_20251126_143022_123456.json
```

**Snapshot Structure:**
```json
{
  "type": "tool_call",
  "timestamp": "2025-11-26T14:30:22.123456",
  "state": {
    "messages": [...],
    "config": {...}
  },
  "metadata": {
    "phase": "before_tool_call",
    "tool": "changelog_tool",
    "args": {...}
  }
}
```

### LangSmith Traces

View execution traces in LangSmith:

1. Go to https://smith.langchain.com
2. Select your project (e.g., "dapy-dev")
3. Click on recent runs
4. Explore tool calls, model invocations, and timing

### Common Issues

**Issue: "API key not found"**

```bash
# Check environment
dapy diag | grep API_KEY

# Set keys
export LANGCHAIN_API_KEY=lsv2_pt_...
export OPENAI_API_KEY=sk-...
```

**Issue: "Git command failed"**

```bash
# Verify git repository
git status

# Check git config
git config --list
```

**Issue: "Tool execution failed"**

```bash
# Enable debug mode
dapy --debug ask "Your query here"

# Check LangSmith traces for details
# Review snapshots for state at failure
```

**Issue: "Database connection failed"**

```bash
# For SQLite (default)
ls -la dapy.db

# For PostgreSQL
echo $POSTGRES_CONN_STRING
```

---

## Docker Examples

### Development Container

```bash
# Start container
docker-compose up -d

# Enter container
docker-compose exec dapy-dev bash

# Inside container
cd /repos/your-project
dapy next
dapy ask "What's next?"
```

### Production Deployment

```bash
# Deploy to GCP
cd deployment/gcp
./deploy.sh

# Run commands remotely
docker-compose exec dapy dapy next

# View logs
docker-compose logs -f dapy
```

---

## Integration Examples

### With Git Hooks

Create `.git/hooks/pre-push`:

```bash
#!/bin/bash
# Ensure changelog is updated before push

dapy document
git add CHANGELOG.md
```

### With Cron Jobs

Schedule periodic tasks:

```bash
# Add to crontab
0 9 * * * cd /path/to/project && dapy next > daily-status.txt
0 17 * * * cd /path/to/project && dapy close
```

### With CI/CD

In GitHub Actions:

```yaml
- name: Document changes
  run: |
    pip install dapy
    dapy document
    git add CHANGELOG.md
    git commit -m "Update changelog [skip ci]" || true
    git push
```

---

## Best Practices

1. **Start every session with `dapy next`**
   - Review priorities
   - Check work in progress
   - Plan your session

2. **Document changes frequently**
   - Run `dapy document` after significant work
   - Keep CHANGELOG.md current
   - Makes git history more useful

3. **Close sessions properly**
   - Run `dapy close` at end of day
   - Updates 2Do.md with progress
   - Prepares for next session

4. **Use breakpoints for new workflows**
   - Test new tools with breakpoints
   - Inspect state before critical operations
   - Learn tool behavior

5. **Review LangSmith traces**
   - Understand agent decision-making
   - Optimize prompts and tools
   - Debug unexpected behavior

6. **Keep snapshots for debugging**
   - Don't delete snapshots immediately
   - Review when troubleshooting
   - Learn from failures

---

## Next Steps

- Read [deployment/README.md](deployment/README.md) for deployment options
- Check [README.md](README.md) for architecture details
- Explore [dapy/prompts/](dapy/prompts/) for prompt customization
- Review [dapy/tools/](dapy/tools/) for tool implementations
