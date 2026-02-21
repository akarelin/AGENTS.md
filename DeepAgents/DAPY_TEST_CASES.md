# DAPY Test Cases

## Overview

10 test cases extracted from user's actual workflows in RAN and CRAP repositories. These represent real tasks the user performs with Claude Code that DAPY should handle.

---

## Test Case 1: "What's next?"

**Source:** `/home/alex/RAN/AGENTS.md` - Session Management Commands

**User Input:**
```
What's next?
```

**Expected Behavior:**
1. Read `/repos/RAN/2Do.md` for current priorities
2. Read `/repos/RAN/ROADMAP.md` for active epics
3. Run `git status` in `/repos/RAN` to check work in progress
4. Present concise summary with:
   - Current status from 2Do.md
   - Next immediate task
   - Any work in progress
5. Wait for user approval

**Success Criteria:**
- Reads 2Do.md correctly
- Identifies current focus
- Lists immediate tasks
- Checks git status
- Provides actionable summary

**Example Output:**
```
Current Status (from 2Do.md):
- Focus: Multi-Subagent Workflow Architecture Project
- Phase 2: Agent Implementation COMPLETED

Immediate Tasks:
1. Setup browser-use-mcp as WSL remote MCP server
2. Create PowerShell script templates in knowledge base

Git Status:
- Clean working directory
- On branch: master

Recommended Next: Start with browser-use-mcp setup?
```

---

## Test Case 2: "Document"

**Source:** `/home/alex/RAN/AGENTS.md` - Session Management Commands

**User Input:**
```
document
```

**Expected Behavior:**
1. Run `git diff` in `/repos/RAN` to detect changes
2. Run `git status` to see new/modified files
3. Analyze changes (Added/Changed/Fixed/Removed)
4. Update `/repos/RAN/CHANGELOG.md` with entries
5. Update relevant documentation if needed
6. Provide summary of what was documented

**Success Criteria:**
- Detects all git changes
- Classifies changes correctly
- Updates CHANGELOG.md in proper format
- Preserves existing CHANGELOG structure
- Provides clear summary

**Example Output:**
```
Changes Detected:
- Modified: dapy/cli.py (Added feedback command)
- Added: dapy/feedback.py (New module)

CHANGELOG.md Updated:
### Added
- Feedback command for user input collection
- LangSmith feedback API integration

Documentation Updated:
- README.md: Added feedback command documentation

Summary: 2 changes documented in CHANGELOG.md
```

---

## Test Case 3: "Close"

**Source:** `/home/alex/RAN/AGENTS.md` - Session Management Commands

**User Input:**
```
close
```

**Expected Behavior:**
1. Read current `/repos/RAN/2Do.md`
2. Update with session progress
3. Add next steps based on current state
4. Check for mistakes to document in `AGENTS_mistakes.md`
5. Archive completed work if any
6. Clean up temporary files
7. Provide session summary

**Success Criteria:**
- Updates 2Do.md with progress
- Marks completed tasks
- Adds clear next steps
- Documents mistakes if any
- Provides comprehensive summary

**Example Output:**
```
Session Summary:

Progress Made:
- Implemented feedback system
- Added LangSmith integration
- Updated documentation

2Do.md Updated:
- Marked "Add feedback command" as complete
- Added next steps: "Test feedback in production"

Mistakes Documented:
- None this session

Ready for Next Session:
- Feedback system ready for testing
- All code committed
- Documentation up to date

Session closed successfully.
```

---

## Test Case 4: "Push"

**Source:** `/home/alex/RAN/AGENTS.md` - Session Management Commands

**User Input:**
```
push
```

**Expected Behavior:**
1. Verify `/repos/RAN/CHANGELOG.md` is updated
2. If not updated, prompt to document first
3. Stage all changes: `git add .`
4. Create commit message from CHANGELOG
5. Commit: `git commit -m "message"`
6. Push: `git push origin master`
7. Confirm success

**Success Criteria:**
- Checks CHANGELOG.md first
- Creates meaningful commit message
- Commits all changes
- Pushes successfully
- Confirms with user

**Example Output:**
```
Pre-push Checks:
CHANGELOG.md is up to date
All changes staged

Commit Message (from CHANGELOG):
"Add feedback system with LangSmith integration

- Added feedback command for user input
- Integrated LangSmith feedback API
- Updated documentation"

Committing...
Committed: abc123f

Pushing to origin/master...
Pushed successfully

All changes are now on GitHub.
```

---

## Test Case 5: Archive Old Code

**Source:** `/home/alex/RAN/agents/archive-agent.md`

**User Input:**
```
Archive the old authentication module in /repos/RAN/old_auth.py
```

**Expected Behavior:**
1. Identify file: `/repos/RAN/old_auth.py`
2. Create archive directory if needed: `/repos/RAN/ARCHIVE/`
3. Add timestamp to filename
4. Move file to archive
5. Update archive inventory
6. Provide summary

**Success Criteria:**
- File moved to ARCHIVE/
- Timestamp added to filename
- Original file removed
- Inventory updated
- Confirmation provided

**Example Output:**
```
Archiving: old_auth.py

Archive Details:
- Source: /repos/RAN/old_auth.py
- Destination: /repos/RAN/ARCHIVE/old_auth_20250126.py
- Size: 2.3 KB
- Reason: Replaced by new auth system

Inventory Updated:
- Added entry to ARCHIVE/README.md
- Documented replacement

File archived successfully
```

---

## Test Case 6: Process Mistake

**Source:** `/home/alex/RAN/agents/mistake-review-agent.md`

**User Input:**
```
I accidentally deleted production data in the users table. Document this mistake.
```

**Expected Behavior:**
1. Open `/repos/RAN/AGENTS_mistakes.md`
2. Add new entry with:
   - Date
   - Description of mistake
   - Impact
   - Root cause
   - Prevention strategy
3. Analyze pattern (if recurring)
4. Update AGENTS.md if needed
5. Provide summary

**Success Criteria:**
- Mistake documented in AGENTS_mistakes.md
- Includes all required fields
- Identifies root cause
- Suggests prevention
- Updates AGENTS.md if pattern detected

**Example Output:**
```
Mistake Documented:

Date: 2025-01-26
Description: Accidentally deleted production data in users table
Impact: Production data loss
Root Cause: Ran DELETE query without WHERE clause on production DB
Prevention: Always use WHERE clause, test on copy first

Pattern Analysis:
- Similar mistake on 2025-01-15 (different table)
- Pattern: Direct production DB operations without safeguards

AGENTS.md Updated:
- Added rule: "ALWAYS backup before DELETE operations"
- Added rule: "Test destructive queries on copy first"

Mistake documented and prevention measures added
```

---

## Test Case 7: Validate Documentation

**Source:** `/home/alex/RAN/agents/validation-agent.md`

**User Input:**
```
Validate the README.md against documentation standards
```

**Expected Behavior:**
1. Read `/repos/RAN/README.md`
2. Check against standards:
   - Has title
   - Has description
   - Has installation instructions
   - Has usage examples
   - Has proper formatting
3. Identify violations
4. Provide report with recommendations

**Success Criteria:**
- All standards checked
- Violations identified
- Specific recommendations provided
- Line numbers for issues
- Actionable feedback

**Example Output:**
```
Validation Report: README.md

Has title
Has description
Missing installation instructions
Has usage examples
Code blocks not properly formatted (lines 45-52)

Violations Found: 2

Recommendations:
1. Add "## Installation" section with setup steps
2. Fix code block formatting on lines 45-52:
   - Use ```bash for shell commands
   - Ensure proper indentation

Overall: 80% compliant
Action needed: Add installation section and fix formatting
```

---

## Test Case 8: Update README

**Source:** `/home/alex/RAN/agents/docs-agent.md`

**User Input:**
```
Update README.md to reflect the new feedback feature
```

**Expected Behavior:**
1. Read `/repos/RAN/README.md`
2. Identify where to add feedback documentation
3. Add section about feedback command
4. Include usage example
5. Update table of contents if present
6. Preserve existing structure
7. Provide summary of changes

**Success Criteria:**
- README.md updated correctly
- New section added in logical place
- Includes usage example
- Formatting consistent
- TOC updated if present

**Example Output:**
```
README.md Updated:

Changes Made:
- Added "## Feedback" section after "Usage"
- Included command syntax and example
- Updated table of contents

New Section:
## Feedback

Submit feedback about DAPY behavior:

```bash
dapy feedback "The changelog command didn't detect my changes"
```

Feedback is logged to LangSmith for analysis and improvement.

README.md updated successfully
```

---

## Test Case 9: Search Knowledge Base

**Source:** `/home/alex/RAN/agents/knowledge-management-agent.md`

**User Input:**
```
Search for documentation about git workflows
```

**Expected Behavior:**
1. Search all markdown files in `/repos/RAN`
2. Look for "git", "workflow", "commit", "push" keywords
3. Find relevant files
4. Extract relevant sections
5. Provide summary with file paths

**Success Criteria:**
- Searches all markdown files
- Finds relevant content
- Provides file paths
- Shows relevant excerpts
- Ranks by relevance

**Example Output:**
```
Search Results: "git workflows"

Found in 3 files:

1. /repos/RAN/AGENTS.md (Most Relevant)
   Section: "Session Management Commands"
   Excerpt:
   > #### "Push" - Git operations
   > When user says "push":
   > 1. Ensure CHANGELOG.md is updated
   > 2. Commit all changes with appropriate message
   > 3. Push to repository

2. /repos/RAN/2Do.md
   Section: "Immediate Tasks"
   Excerpt:
   > - [ ] Request/build Git MCP tool for direct git operations

3. /repos/RAN/agents/push-agent.md
   Section: "Push Agent Instructions"
   Excerpt:
   > Handles all git commit and push operations

Recommendation: Check AGENTS.md for complete git workflow documentation
```

---

## Test Case 10: Git Status

**Source:** Basic git operations from user's workflow

**User Input:**
```
What's the current git status?
```

**Expected Behavior:**
1. Run `git status` in `/repos/RAN`
2. Parse output
3. Identify:
   - Current branch
   - Modified files
   - Untracked files
   - Staged files
4. Present in readable format

**Success Criteria:**
- Runs git status
- Parses output correctly
- Categorizes files
- Provides clear summary
- Suggests next action if needed

**Example Output:**
```
Git Status: /repos/RAN

Branch: master
Status: Clean working directory

Modified Files: 2
- dapy/cli.py
- README.md

Untracked Files: 1
- dapy/feedback.py

Staged Files: 0

Summary:
- 3 files with changes
- No files staged for commit
- No conflicts

Suggested Action: Run "document" to update CHANGELOG, then "push"
```

---

## Test Execution Plan

### Phase 1: Setup (Day 1)
1. Deploy DAPY to LangChain Cloud
2. Configure with user's repos
3. Set up LangSmith tracing
4. Verify basic connectivity

### Phase 2: Basic Tests (Day 2-3)
Run tests 1-5 (session management):
1. What's next?
2. Document
3. Close
4. Push
5. Archive

**Expected:** Some failures, iterate on fixes

### Phase 3: Advanced Tests (Day 4-5)
Run tests 6-10 (specialized tasks):
6. Process mistake
7. Validate documentation
8. Update README
9. Search knowledge base
10. Git status

**Expected:** More failures, iterate on fixes

### Phase 4: Full Suite (Day 6)
- Run all 10 tests in sequence
- Verify all pass
- Document any remaining issues
- Prepare handoff

### Phase 5: Delivery (Day 7)
- Generate test report
- Provide LangSmith links
- Demonstrate working system
- Hand off to user

---

## Success Metrics

### Per Test
- Completes without errors
- Produces expected output
- Follows user's workflow patterns
- Trace shows correct tool usage
- Performance acceptable (<30s per test)

### Overall Suite
- All 10 tests pass
- No manual intervention needed
- Consistent behavior across runs
- Complete trace coverage in LangSmith
- Ready for user's own testing

---

## Iteration Strategy

### When Test Fails

1. **Analyze trace in LangSmith**
   - What tool was called?
   - What was the input?
   - What was the output?
   - Where did it fail?

2. **Identify root cause**
   - Wrong tool selected?
   - Tool implementation bug?
   - Prompt issue?
   - Workflow logic error?

3. **Apply fix**
   - Update tool code
   - Refine prompt
   - Fix workflow logic
   - Update configuration

4. **Redeploy**
   - Push changes to GitHub
   - Trigger LangChain Cloud redeployment
   - Wait for deployment

5. **Re-test**
   - Run failed test again
   - Verify fix works
   - Check for regressions

6. **Document**
   - Record issue in test log
   - Document fix applied
   - Update test expectations if needed

### Iteration Limit

- Max 3 iterations per test
- If still failing after 3 iterations:
  - Document issue
  - Mark test as "needs investigation"
  - Continue with other tests
  - Revisit after other tests pass

---

## Test Data

### Repository Structure

Tests assume repos are mounted at:
- `/repos/RAN/` - Main repository
- `/repos/CRAP/` - Secondary repository
- `/repos/_/` - Knowledge base
- `/repos/gppu/` - Additional repo

### Required Files

For tests to work, these files must exist:
- `/repos/RAN/2Do.md`
- `/repos/RAN/ROADMAP.md`
- `/repos/RAN/CHANGELOG.md`
- `/repos/RAN/AGENTS.md`
- `/repos/RAN/AGENTS_mistakes.md`
- `/repos/RAN/README.md`

### Git Configuration

- Git must be configured with user name/email
- SSH keys or tokens for push access
- Write access to repositories

---

## Deliverables

### Test Report

For each test:
- Test name and number
- Input provided
- Expected output
- Actual output
- Pass/Fail status
- LangSmith trace link
- Notes/observations

### Summary Report

- Total tests: 10
- Passed: X
- Failed: Y
- Success rate: Z%
- Total iterations: N
- Issues found: M
- Fixes applied: P

### LangSmith Project

- Project name: `dapy-testing`
- All 10 test traces
- Organized by test number
- Tagged with pass/fail
- Annotations on failures

### Handoff Package

- Working DAPY deployment
- Test report
- LangSmith project link
- Known issues (if any)
- Usage instructions
- Next steps for user

---

## Notes

### Real User Data

All tests use real data from user's repos. No synthetic test data.

### User's Workflow

Tests replicate exact commands user gives to Claude Code. This ensures DAPY works the same way.

### Iteration Expected

First run will likely have failures. This is normal. Manus will iterate until all tests pass.

### Timeline Flexible

7-day timeline is estimate. May be faster or slower depending on issues encountered.

### User Visibility

User can watch all testing in LangSmith dashboard in real-time. Full transparency.

---

## Ready to Start

Once user provides API keys, Manus will:
1. Deploy DAPY
2. Run these 10 tests
3. Iterate on failures
4. Deliver when all pass

**User won't touch anything until Manus shows 10 passing tests!**
