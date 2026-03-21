# Knowledge Management Test Scenarios

## Overview
This document contains test scenarios for the Knowledge Management subagent system to ensure proper orchestration and knowledge preservation.

## Test Scenario 1: Full Documentation Review

### Command
```bash
./claude-orchestrate.sh "perform a comprehensive documentation review"
```

### Expected Behavior
1. **Orchestrator** detects "comprehensive documentation review" trigger
2. **Orchestrator** spawns Knowledge Management agent
3. **Knowledge Management** spawns all sub-agents:
   - docs-agent: inventory and gap_analysis
   - changelog-agent: analyze current state
   - archive-agent: review_candidates
   - validation-agent: knowledge_check
4. **Knowledge Management** consolidates results
5. **Orchestrator** presents unified summary to user

### Success Criteria
- All documentation gaps identified
- Archive candidates reviewed
- Knowledge preservation verified
- Single coherent response to user

## Test Scenario 2: Pull Request Review

### Command
```bash
./claude-orchestrate.sh "review pull request #123"
```

### Expected Behavior
1. **Orchestrator** detects "pull request" trigger
2. **Orchestrator** spawns validation-agent with pr_review task
3. **Validation** checks:
   - Documentation matches code changes
   - CHANGELOG.md updated
   - No docs deleted without archiving
   - Knowledge preserved
4. **Validation** returns review report
5. **Orchestrator** presents PR review to user

### Success Criteria
- PR documentation completeness verified
- Knowledge preservation confirmed
- Clear approve/reject recommendation
- No mention of subagents

## Test Scenario 3: Document and Push

### Command
```bash
./claude-orchestrate.sh "update all documentation and push changes"
```

### Expected Behavior
1. **Orchestrator** detects dual triggers: "documentation" and "push"
2. **Orchestrator** spawns Knowledge Management agent
3. **Knowledge Management** coordinates:
   - docs-agent: update_docs
   - changelog-agent: analyze_and_update
4. **Knowledge Management** returns summary
5. **Orchestrator** spawns push-agent
6. **Push** commits and pushes changes
7. **Orchestrator** presents complete summary

### Success Criteria
- Documentation updated
- Changelog reflects changes
- Changes committed and pushed
- User sees single workflow summary

## Test Scenario 4: Archive with Knowledge Preservation

### Command
```bash
./claude-orchestrate.sh "archive old documentation files"
```

### Expected Behavior
1. **Orchestrator** detects "archive" trigger
2. **Orchestrator** spawns archive-agent
3. **Archive** identifies documentation candidates
4. **Archive** ensures knowledge preservation:
   - Creates detailed inventory
   - Preserves context
   - Updates references
5. **Archive** reports to parent (if Knowledge Management active)
6. **Orchestrator** confirms archival complete

### Success Criteria
- No documentation deleted
- Archive inventory complete
- Context preserved
- References updated

## Test Scenario 5: Knowledge Loss Prevention

### Command
```bash
# Simulate attempt to delete documentation
echo "Delete README.md" > test_changes.txt
./claude-orchestrate.sh "clean up repository"
```

### Expected Behavior
1. **Orchestrator** detects "clean up" trigger
2. **Orchestrator** spawns archive-agent
3. **Archive** detects documentation deletion attempt
4. **Archive** flags knowledge at risk
5. **Orchestrator** receives error status
6. **Orchestrator** alerts user and requests confirmation

### Success Criteria
- Deletion prevented
- User alerted to risk
- Explicit confirmation required
- Knowledge preserved

## Test Scenario 6: Nested Agent Coordination

### Command
```bash
./claude-orchestrate.sh "ensure all knowledge is preserved and validated"
```

### Expected Behavior
1. **Orchestrator** detects "knowledge preserved" trigger
2. **Orchestrator** spawns Knowledge Management
3. **Knowledge Management** spawns:
   - validation-agent: knowledge_check
   - archive-agent: inventory
   - docs-agent: inventory
4. Each sub-agent reports to Knowledge Management
5. **Knowledge Management** consolidates and reports issues
6. **Orchestrator** presents findings

### Success Criteria
- Multi-level coordination works
- Parent receives all sub-reports
- Consolidated summary accurate
- No subagent details exposed

## Test Scenario 7: Error Handling

### Command
```bash
# Simulate missing CHANGELOG.md
rm CHANGELOG.md
./claude-orchestrate.sh "update changelog"
```

### Expected Behavior
1. **Orchestrator** spawns changelog-agent
2. **Changelog** detects missing file
3. **Changelog** creates initial CHANGELOG.md
4. **Changelog** returns success with note
5. **Orchestrator** reports changelog created

### Success Criteria
- Error handled gracefully
- CHANGELOG.md created
- User informed appropriately
- No technical errors exposed

## Test Scenario 8: Compression with Preservation

### Command
```bash
./claude-orchestrate.sh "compress the changelog"
```

### Expected Behavior
1. **Orchestrator** spawns changelog-agent with compress task
2. **Changelog** moves verbose entries to CHANGELOG_VERBOSE.md
3. **Changelog** ensures knowledge preserved:
   - Context maintained
   - References added
   - Searchability preserved
4. **Changelog** reports compression complete
5. **Orchestrator** confirms to user

### Success Criteria
- Verbose entries moved, not deleted
- Knowledge remains searchable
- References point to verbose file
- Main changelog concise

## Validation Checklist

For each test scenario, verify:
- [ ] Correct agent spawned
- [ ] Task completed successfully
- [ ] Knowledge preserved
- [ ] User sees natural response
- [ ] No subagent architecture exposed
- [ ] Errors handled gracefully
- [ ] Parent-child coordination works
- [ ] Summary accurate and complete

## Running Tests

1. Set up test environment:
   ```bash
   cd /tmp/test-orchestrator
   cp -r /home/alex/RAN/agents .
   cp /home/alex/RAN/ORCHESTRATOR.md .
   cp /home/alex/RAN/.claude-code.yaml .
   ```

2. Run each scenario
3. Verify success criteria
4. Document any issues
5. Update agent configurations as needed