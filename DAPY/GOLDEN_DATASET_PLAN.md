# Golden Dataset Plan for DeepAgents

## Overview

Using **LangSmith's native features** to create golden datasets from your real task examples, with no custom implementation needed.

---

## LangSmith Native Features We'll Use

### 1. Datasets
**What:** Collection of input/output examples for evaluation
**Use:** Store golden task examples from your repos
**Features:**
- Manual curation from traces
- Automatic capture via rules
- Annotation queues for review
- CSV/JSONL import
- AI-generated synthetic examples

### 2. Prompt Canvas
**What:** AI-assisted prompt editor
**Use:** Optimize DeepAgents prompts based on golden examples
**Features:**
- Chat sidebar for natural language edits
- Quick actions (reading level, length)
- Custom quick actions
- Diff viewer for versions
- Save and version prompts

### 3. Annotation Queues
**What:** Streamlined review interface for subject matter experts
**Use:** Mark past conversations as golden
**Features:**
- Filter traces for review
- Edit inputs/outputs before adding to dataset
- Hotkey support (D to add to dataset)
- Automatic rules for queue population

---

## Task Examples Extracted from Your Repos

### From RAN/AGENTS.md

**Example 1: "What's next?" Command**
```json
{
  "input": "What's next?",
  "expected_output": {
    "reads": ["/repos/RAN/2Do.md", "/repos/RAN/ROADMAP.md"],
    "git_status": "checked",
    "summary": "Current focus, immediate tasks, work in progress",
    "recommendation": "Next actionable step"
  },
  "reference_output": "Current Status (from 2Do.md):\n- Focus: Multi-Subagent Workflow Architecture Project\n- Phase 2: Agent Implementation ✅ COMPLETED\n\nImmediate Tasks:\n1. Setup browser-use-mcp as WSL remote MCP server\n2. Create PowerShell script templates in knowledge base\n\nGit Status:\n- Clean working directory\n- On branch: master\n\nRecommended Next: Start with browser-use-mcp setup?"
}
```

**Example 2: "Document" Command**
```json
{
  "input": "document",
  "expected_output": {
    "git_diff": "executed",
    "changes_classified": ["Added", "Changed", "Fixed", "Removed"],
    "changelog_updated": true,
    "summary": "Changes documented"
  },
  "reference_output": "Changes Detected:\n- Modified: deepagents/cli.py (Added feedback command)\n- Added: deepagents/feedback.py (New module)\n\nCHANGELOG.md Updated:\n### Added\n- Feedback command for user input collection\n- LangSmith feedback API integration\n\nDocumentation Updated:\n- README.md: Added feedback command documentation\n\nSummary: 2 changes documented in CHANGELOG.md"
}
```

**Example 3: "Close" Command**
```json
{
  "input": "close",
  "expected_output": {
    "2do_updated": true,
    "progress_marked": true,
    "mistakes_checked": true,
    "summary": "Session closed with next steps"
  },
  "reference_output": "Session Summary:\n\nProgress Made:\n- ✅ Implemented feedback system\n- ✅ Added LangSmith integration\n- ✅ Updated documentation\n\n2Do.md Updated:\n- Marked 'Add feedback command' as complete\n- Added next steps: 'Test feedback in production'\n\nMistakes Documented:\n- None this session\n\nReady for Next Session:\n- Feedback system ready for testing\n- All code committed\n- Documentation up to date\n\nSession closed successfully."
}
```

**Example 4: "Push" Command**
```json
{
  "input": "push",
  "expected_output": {
    "changelog_verified": true,
    "changes_staged": true,
    "commit_created": true,
    "pushed": true,
    "confirmation": "All changes on GitHub"
  },
  "reference_output": "Pre-push Checks:\n✅ CHANGELOG.md is up to date\n✅ All changes staged\n\nCommit Message (from CHANGELOG):\n\"Add feedback system with LangSmith integration\n\n- Added feedback command for user input\n- Integrated LangSmith feedback API\n- Updated documentation\"\n\nCommitting...\n✅ Committed: abc123f\n\nPushing to origin/master...\n✅ Pushed successfully\n\nAll changes are now on GitHub."
}
```

### From RAN/SESSION_SUMMARY_2025-11-25.md

**Example 5: Git Rebase Conflict Resolution**
```json
{
  "input": "Resolve Y2 rebase conflicts and audit gppu submodule integrity",
  "context": {
    "repo": "/home/alex/RAN/appdaemon/_adev/Y2",
    "branch": "dev",
    "conflicts": ["gppu submodule", "templates/inspector.html", "Y2_debug_ui.py"]
  },
  "expected_output": {
    "conflicts_resolved": true,
    "documentation_created": true,
    "submodule_audited": true,
    "summary": "Complete session summary"
  },
  "reference_output": "Session Summary: Y2 Rebase & gppu Submodule Audit\n\nCompleted Tasks:\n1. ✅ Y2 Development Branch Rebase\n   - gppu submodule conflict resolved\n   - 6 files changed, +107/-660 lines\n   - Net: -553 lines of cruft removed\n\n2. ✅ gppu Submodule Audit\n   - Y2 gppu submodule properly configured\n   - All imports resolve correctly\n   - Documentation created: gppu_submodule_audit.md\n\n3. ✅ RAN Repository Updates\n   - 2 commits ahead of origin/master\n   - Clean working tree\n\nSession completed successfully ✅"
}
```

### From RAN/AGENTS_mistakes.md

**Example 6: Mistake Documentation**
```json
{
  "input": "I accidentally deleted production data in the users table. Document this mistake.",
  "expected_output": {
    "mistake_documented": true,
    "pattern_analyzed": true,
    "prevention_added": true,
    "agents_md_updated": true
  },
  "reference_output": "Mistake Documented:\n\nDate: 2025-01-26\nDescription: Accidentally deleted production data in users table\nImpact: Production data loss\nRoot Cause: Ran DELETE query without WHERE clause on production DB\nPrevention: Always use WHERE clause, test on copy first\n\nPattern Analysis:\n- Similar mistake on 2025-01-15 (different table)\n- Pattern: Direct production DB operations without safeguards\n\nAGENTS.md Updated:\n- Added rule: 'ALWAYS backup before DELETE operations'\n- Added rule: 'Test destructive queries on copy first'\n\n✅ Mistake documented and prevention measures added"
}
```

### From RAN/2Do.md

**Example 7: Task Prioritization**
```json
{
  "input": "What should I work on next?",
  "context": {
    "file": "/repos/RAN/2Do.md",
    "current_focus": "Multi-Subagent Workflow Architecture Project"
  },
  "expected_output": {
    "current_phase": "identified",
    "immediate_tasks": "listed",
    "recommendation": "provided"
  },
  "reference_output": "Current Focus: Multi-Subagent Workflow Architecture Project\n\nPhase 2: Agent Implementation ✅ COMPLETED\n\nImmediate Tasks:\n1. [ ] Setup browser-use-mcp as WSL remote MCP server\n2. [ ] Create PowerShell script templates in knowledge base\n3. [ ] Request/build Git MCP tool for direct git operations\n\nRecommendation: Start with browser-use-mcp setup as it's a prerequisite for other tasks."
}
```

### From RAN/ROADMAP.md

**Example 8: Strategic Planning**
```json
{
  "input": "Show me the roadmap for this quarter",
  "expected_output": {
    "current_epic": "identified",
    "milestones": "listed",
    "timeline": "provided"
  },
  "reference_output": "Q4 2025 Roadmap:\n\nCurrent Epic: Multi-Subagent Workflow Architecture\n\nPhases:\n- Phase 1: Requirements & Design ✅ COMPLETED\n- Phase 2: Agent Implementation ✅ COMPLETED  \n- Phase 3: Testing & Integration (IN PROGRESS)\n- Phase 4: Documentation & Deployment (PLANNED)\n\nMilestones:\n- M1: Core agents functional (✅ Done)\n- M2: Integration with Claude Code (🔄 In Progress)\n- M3: Production deployment (📅 Planned)\n\nTimeline: Complete by end of Q4 2025"
}
```

### From RAN/agents/

**Example 9: Changelog Generation**
```json
{
  "input": "Update CHANGELOG.md with recent changes",
  "context": {
    "git_diff": "deepagents/cli.py, deepagents/feedback.py modified"
  },
  "expected_output": {
    "changelog_updated": true,
    "format": "standard",
    "categories": ["Added", "Changed", "Fixed", "Removed"]
  },
  "reference_output": "## [Unreleased]\n\n### Added\n- Feedback command for user input collection\n- LangSmith feedback API integration\n- Feedback module with structured submission\n\n### Changed\n- CLI now includes feedback subcommand\n- Updated dependencies in pyproject.toml\n\n### Documentation\n- Added feedback command to README.md\n- Updated usage examples"
}
```

**Example 10: Archive Old Code**
```json
{
  "input": "Archive the old authentication module in /repos/RAN/old_auth.py",
  "expected_output": {
    "file_moved": true,
    "timestamp_added": true,
    "inventory_updated": true,
    "summary": "Archive confirmation"
  },
  "reference_output": "Archiving: old_auth.py\n\nArchive Details:\n- Source: /repos/RAN/old_auth.py\n- Destination: /repos/RAN/ARCHIVE/old_auth_20250126.py\n- Size: 2.3 KB\n- Reason: Replaced by new auth system\n\nInventory Updated:\n- Added entry to ARCHIVE/README.md\n- Documented replacement\n\n✅ File archived successfully"
}
```

---

## Implementation Plan

### Phase 1: Create Golden Dataset in LangSmith

**Step 1: Create Dataset**
1. Go to LangSmith UI → Datasets & Experiments
2. Click "+ New Dataset"
3. Name: `deepagents-golden-examples`
4. Description: "Golden task examples from user's real workflows"
5. Create dataset

**Step 2: Add Examples Manually**
1. Click "+ Example" on dataset page
2. For each of the 10 examples above:
   ```json
   {
     "input": "user command",
     "output": "expected agent response",
     "reference": "golden reference output",
     "metadata": {
       "source": "RAN/AGENTS.md",
       "task_type": "session_management",
       "difficulty": "basic",
       "integration_tools": []
     }
   }
   ```
3. Save each example

**Step 3: Add Examples from Traces (Future)**
When DeepAgents is running:
1. Filter traces with good outcomes
2. Click "Add to Dataset" from trace view
3. Edit if needed
4. Add to `deepagents-golden-examples`

### Phase 2: Set Up Annotation Workflow

**Step 1: Create Annotation Queue**
1. Go to LangSmith UI → Annotation Queues
2. Click "+ New Queue"
3. Name: `deepagents-review`
4. Default dataset: `deepagents-golden-examples`
5. Configure schema:
   ```json
   {
     "is_golden": "boolean",
     "quality_score": "number (1-5)",
     "notes": "text",
     "improvements": "text"
   }
   ```

**Step 2: Set Up Automation Rules**
1. Create rule: "Add to review queue if user feedback < 3"
2. Create rule: "Add to review queue if tagged 'review'"
3. Create rule: "Add to review queue if execution time > 30s"

**Step 3: Annotation Workflow**
For you to mark past conversations as golden:
1. Open annotation queue
2. Review trace
3. Edit input/output if needed
4. Mark `is_golden: true`
5. Add quality score and notes
6. Press `D` to add to golden dataset

### Phase 3: Use Prompt Canvas for Optimization

**Step 1: Create Prompt in LangSmith**
1. Go to Prompts section
2. Click "+ Prompt"
3. Name: `deepagents-system-prompt`
4. Add current system prompt from `deepagents/prompts/system_prompt.md`

**Step 2: Optimize with Prompt Canvas**
1. Click glowing wand icon on prompt
2. In chat sidebar, ask:
   - "Make this prompt better for task X"
   - "Adjust tone to be more concise"
   - "Add instructions for handling errors"
3. Use quick actions:
   - Change reading level
   - Adjust length
   - Custom actions (save your own)
4. View diff to see changes
5. Click "Use this Version" to save

**Step 3: Test Against Golden Dataset**
1. In Prompt Playground, select prompt
2. Click "Set up Evaluation"
3. Select `deepagents-golden-examples` dataset
4. Run evaluation
5. Review results
6. Iterate on prompt based on failures

### Phase 4: Replace Integration Tools with Text Files

**Current:** Tasks require `integration:tools` (APIs, databases, etc.)

**Solution:** Provide data as text files instead

**Example Structure:**
```
/repos/test-data/
├── api-responses/
│   ├── github-user-info.json
│   ├── weather-api-response.json
│   └── database-query-result.json
├── database-dumps/
│   ├── users-table.csv
│   └── transactions-table.csv
├── config-files/
│   ├── app-config.yaml
│   └── secrets.env.example
└── logs/
    ├── application.log
    └── error.log
```

**In Golden Examples:**
```json
{
  "input": "Get user info for username 'alex'",
  "context": {
    "data_file": "/repos/test-data/api-responses/github-user-info.json"
  },
  "expected_output": {
    "reads_file": true,
    "extracts_data": true,
    "formats_response": true
  },
  "reference_output": "User: alex\nName: Alex Karelin\nRepos: 42\nFollowers: 123"
}
```

**DeepAgents Behavior:**
- Instead of calling GitHub API
- Reads `/repos/test-data/api-responses/github-user-info.json`
- Processes data
- Returns formatted response

**Benefits:**
- ✅ No API keys needed for testing
- ✅ Deterministic results
- ✅ Faster execution
- ✅ Offline testing
- ✅ Cost-free

### Phase 5: Continuous Improvement

**Workflow:**
1. **You use DeepAgents** → Traces logged to LangSmith
2. **Good outcomes** → Add to annotation queue
3. **You review** → Mark as golden, add to dataset
4. **Prompt optimization** → Use Prompt Canvas with golden examples
5. **Evaluation** → Test new prompts against golden dataset
6. **Deploy** → Update DeepAgents with optimized prompts
7. **Repeat** → Continuous improvement cycle

---

## Golden Dataset Structure

### Dataset Schema

```json
{
  "name": "deepagents-golden-examples",
  "description": "Golden task examples from user's real workflows",
  "schema": {
    "input": {
      "type": "string",
      "description": "User command or task description"
    },
    "output": {
      "type": "object",
      "description": "Expected agent behavior and outputs"
    },
    "reference": {
      "type": "string",
      "description": "Golden reference output"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "source": "string (repo/file)",
        "task_type": "string (session_management, git_operations, etc.)",
        "difficulty": "string (basic, intermediate, advanced)",
        "integration_tools": "array (tools required)",
        "data_files": "array (text files needed)",
        "tags": "array (keywords)"
      }
    }
  }
}
```

### Example Entry

```json
{
  "input": "What's next?",
  "output": {
    "reads": ["/repos/RAN/2Do.md", "/repos/RAN/ROADMAP.md"],
    "git_status": "checked",
    "summary": "Current focus, immediate tasks, work in progress",
    "recommendation": "Next actionable step"
  },
  "reference": "Current Status (from 2Do.md):\n- Focus: Multi-Subagent Workflow Architecture Project\n- Phase 2: Agent Implementation ✅ COMPLETED\n\nImmediate Tasks:\n1. Setup browser-use-mcp as WSL remote MCP server\n2. Create PowerShell script templates in knowledge base\n\nGit Status:\n- Clean working directory\n- On branch: master\n\nRecommended Next: Start with browser-use-mcp setup?",
  "metadata": {
    "source": "RAN/AGENTS.md",
    "task_type": "session_management",
    "difficulty": "basic",
    "integration_tools": [],
    "data_files": [
      "/repos/RAN/2Do.md",
      "/repos/RAN/ROADMAP.md"
    ],
    "tags": ["whats-next", "planning", "session-start"]
  }
}
```

---

## Annotation Workflow

### For You (User)

**Mark Past Conversations as Golden:**

1. **Access LangSmith Dashboard**
   - URL: https://smith.langchain.com
   - Navigate to Annotation Queues

2. **Review Traces**
   - Open `deepagents-review` queue
   - See traces that need review
   - Filter by date, task type, etc.

3. **Annotate**
   - Review trace details
   - Edit input/output if needed
   - Mark fields:
     - `is_golden`: true/false
     - `quality_score`: 1-5
     - `notes`: "Why this is golden"
     - `improvements`: "What could be better"

4. **Add to Dataset**
   - Press `D` hotkey
   - Or click "Add to Dataset"
   - Trace added to `deepagents-golden-examples`

5. **Repeat**
   - Process queue regularly
   - Build golden dataset over time

### For Manus (AI)

**Monitor and Improve:**

1. **Watch for New Golden Examples**
   - Check dataset for new additions
   - Analyze patterns
   - Identify gaps

2. **Optimize Prompts**
   - Use Prompt Canvas
   - Test against golden dataset
   - Iterate on improvements

3. **Create Tickets**
   - When patterns emerge
   - When failures occur
   - When improvements needed

4. **Report Progress**
   - Show optimization results
   - Demonstrate improvements
   - Suggest next steps

---

## Text File Data Replacement

### Strategy

**Instead of API integrations:**
- Provide data as text files
- DeepAgents reads files
- Processes data
- Returns results

**File Organization:**
```
/repos/test-data/
├── README.md                    # Index of all data files
├── api-responses/               # Mock API responses
│   ├── github/
│   │   ├── user-info.json
│   │   ├── repo-list.json
│   │   └── commit-history.json
│   ├── weather/
│   │   └── current-weather.json
│   └── database/
│       ├── users-query.json
│       └── transactions-query.json
├── database-dumps/              # Database exports
│   ├── users.csv
│   ├── transactions.csv
│   └── logs.csv
├── config-files/                # Configuration examples
│   ├── app-config.yaml
│   ├── database-config.yaml
│   └── secrets.env.example
├── logs/                        # Log file examples
│   ├── application.log
│   ├── error.log
│   └── access.log
└── documents/                   # Document examples
    ├── requirements.md
    ├── architecture.md
    └── api-docs.md
```

### Example: GitHub API Replacement

**Original Task:**
"Get my GitHub user info"

**With API:**
```python
response = requests.get("https://api.github.com/users/akarelin")
data = response.json()
```

**With Text File:**
```python
with open("/repos/test-data/api-responses/github/user-info.json") as f:
    data = json.load(f)
```

**File Content:**
```json
{
  "login": "akarelin",
  "name": "Alex Karelin",
  "public_repos": 42,
  "followers": 123,
  "following": 56,
  "created_at": "2015-03-15T12:00:00Z"
}
```

### Example: Database Query Replacement

**Original Task:**
"Show me users who signed up this month"

**With Database:**
```python
cursor.execute("SELECT * FROM users WHERE signup_date >= '2025-11-01'")
results = cursor.fetchall()
```

**With Text File:**
```python
df = pd.read_csv("/repos/test-data/database-dumps/users-november.csv")
```

**File Content:**
```csv
id,username,email,signup_date
1001,alex,alex@example.com,2025-11-05
1002,maria,maria@example.com,2025-11-12
1003,john,john@example.com,2025-11-18
```

---

## Benefits of This Approach

### Using LangSmith Native Features

**Datasets:**
- ✅ No custom code to maintain
- ✅ Built-in versioning
- ✅ Evaluation framework included
- ✅ UI for management
- ✅ API for programmatic access

**Prompt Canvas:**
- ✅ AI-assisted optimization
- ✅ Version control
- ✅ Diff viewer
- ✅ Quick actions
- ✅ Team collaboration

**Annotation Queues:**
- ✅ Streamlined review workflow
- ✅ Hotkey support
- ✅ Automatic rules
- ✅ Edit before adding
- ✅ Metadata preservation

### Text File Data Replacement

**For Testing:**
- ✅ No API keys needed
- ✅ Deterministic results
- ✅ Faster execution
- ✅ Offline testing
- ✅ Cost-free
- ✅ Version control friendly

**For Development:**
- ✅ Easy to create test cases
- ✅ Easy to modify data
- ✅ Easy to share
- ✅ Easy to debug
- ✅ Easy to understand

---

## Next Steps

### Immediate (This Week)

1. **Create golden dataset in LangSmith**
   - Add 10 examples from repos
   - Set up schema
   - Configure metadata

2. **Create annotation queue**
   - Set up review workflow
   - Configure automation rules
   - Test annotation process

3. **Create system prompt in LangSmith**
   - Import current prompt
   - Set up versioning
   - Test Prompt Canvas

### Short Term (Next 2 Weeks)

1. **Populate test-data directory**
   - Create mock API responses
   - Export database dumps
   - Add config examples
   - Document file structure

2. **Deploy DeepAgents to LangChain Cloud**
   - Configure with golden dataset
   - Enable tracing
   - Test with text file data

3. **Run initial evaluation**
   - Test against golden examples
   - Identify failures
   - Optimize prompts

### Medium Term (Next Month)

1. **Continuous annotation**
   - Review traces regularly
   - Add golden examples
   - Refine dataset

2. **Prompt optimization**
   - Use Prompt Canvas
   - Test variations
   - Deploy improvements

3. **Expand dataset**
   - Add more examples
   - Cover edge cases
   - Increase difficulty

---

## Summary

**What we're doing:**
- Using LangSmith's **native Datasets** feature for golden examples
- Using LangSmith's **Prompt Canvas** for AI-assisted optimization
- Using LangSmith's **Annotation Queues** for marking conversations
- Replacing API integrations with **text file data**

**What we're NOT doing:**
- ❌ Building custom golden dataset system
- ❌ Building custom annotation UI
- ❌ Building custom prompt optimizer
- ❌ Requiring live API access for testing

**Benefits:**
- ✅ Leverage LangSmith's professional tools
- ✅ No custom code to maintain
- ✅ Faster implementation
- ✅ Better UX
- ✅ Team collaboration support

**Ready to start!**
