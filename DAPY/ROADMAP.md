# DAPY - Roadmap

## Current Version: 0.1.0

### Completed Features

**Core System**
- Zero-configuration CLI with rich terminal output
- LangChain 1.0 agent orchestration
- LangGraph 1.0 workflows
- Middleware stack (snapshots, breakpoints, logging)
- Human-in-the-loop approval gates
- State persistence (SQLite + PostgreSQL)

**Tools** (10 total)
- Changelog management
- Code archival
- Mistake documentation
- Validation
- Git operations (push, status, diff)
- Knowledge base operations (read, search, update markdown)

**Workflows** (3 total)
- Close Session - Session cleanup and progress tracking
- Document Changes - Auto-generate CHANGELOG.md
- What's Next - Priority analysis

**Observability**
- LangSmith tracing integration
- State snapshots at every step
- Enhanced logging with timing
- Diagnostic command

**Debugging**
- Interactive breakpoints
- Snapshot inspection
- Debug package export
- Remote inspection API for Manus

**Feedback System**
- CLI feedback submission
- LangSmith storage
- Manus monitoring agent
- Feedback dashboard
- Ticket tracking

**Deployment**
- Local Docker Compose
- Server five deployment with Manus inspection
- GCP VM configuration
- LangChain Cloud configuration

---

## Upcoming Features

### Phase 1A: Historical Data Import & Optimization (Q1 2026)

**Goal:** Import ChatGPT/Claude conversation history into LangSmith and use it to optimize DAPY prompts and workflows.

**Features:**
- Export tool for ChatGPT conversations.json
- Export tool for Claude conversation history
- Converter to LangSmith JSONL format
- Automated import to LangSmith datasets
- Pattern analysis from historical data
- Annotation tools (AI-assisted)
- Prompt optimization based on real usage
- Tool gap analysis
- Workflow extraction from patterns

**Components:**
- `dapy import chatgpt` - Import ChatGPT history
- `dapy import claude` - Import Claude history
- `dapy analyze patterns` - Analyze conversation patterns
- `dapy optimize prompts` - Test and optimize prompts
- `dapy evaluate` - Evaluate against historical data

**Use Cases:**
- Understand your actual LLM usage patterns
- Identify most common tasks and workflows
- Optimize prompts based on successful interactions
- Discover missing tools and features
- Personalize DAPY to your workflow

**Technical Approach:**
- Parse ChatGPT conversations.json format
- Parse Claude export JSON format
- Convert to LangSmith JSONL dataset format
- Upload via LangSmith API
- Use LangSmith evaluation tools
- A/B test prompt variations
- Track optimization metrics

**Expected Benefits:**
- Data-driven prompt optimization
- Higher tool selection accuracy
- Better workflow automation
- Personalized to your needs
- Continuous improvement loop

**Deliverables:**
- Conversation import tool
- Pattern analysis reports
- Optimized system prompts
- Tool recommendations
- Workflow templates
- Evaluation framework

**See:** `ROADMAP_HISTORICAL_DATA.md` for detailed plan

---

### Phase 1B: LangChain Chat Proxy (Q1 2026)

**Goal:** Replace ChatGPT/Claude Code with LangChain-based interface that captures all interactions for observability and prompt optimization.

**Features:**
- Chat interface that proxies to OpenAI/Anthropic
- Full LangSmith tracing of all conversations
- Use existing API subscriptions (no additional model costs)
- Conversation history and context management
- Multi-model support (GPT-4, Claude, etc.)
- Prompt template management
- A/B testing for prompt variations
- Analytics dashboard for conversation patterns

**Components:**
- `dapy chat` - CLI chat interface
- Web UI for chat (similar to ChatGPT interface)
- Conversation storage in LangSmith
- Prompt optimization tools
- Usage analytics

**Use Cases:**
- Replace ChatGPT with traced version
- Analyze conversation patterns
- Optimize prompts based on real usage
- Compare model responses
- Track token usage across models

**Technical Approach:**
- FastAPI backend with WebSocket support
- React/Vue frontend for web UI
- LangChain ChatOpenAI/ChatAnthropic wrappers
- LangSmith callbacks for tracing
- Conversation persistence in database
- Prompt template system

**Deliverables:**
- CLI chat command
- Web chat interface
- Conversation analytics dashboard
- Prompt optimization tools
- Documentation and examples

---

### Phase 2: Advanced Workflows (Q2 2026)

**Code Review Workflow**
- Automated code review with LLM
- Style and best practice checking
- Security vulnerability detection
- Integration with git hooks

**Testing Workflow**
- Automated test generation
- Test coverage analysis
- Test failure analysis and suggestions

**Documentation Workflow**
- Auto-generate documentation from code
- Keep docs in sync with code changes
- API documentation generation

**Refactoring Workflow**
- Identify code smells
- Suggest refactoring opportunities
- Automated refactoring with human approval

---

### Phase 3: Team Collaboration (Q3 2026)

**Multi-User Support**
- User authentication and authorization
- Shared knowledge bases
- Team feedback and tickets
- Collaborative debugging

**Shared Workflows**
- Team-wide workflow templates
- Shared tool configurations
- Collaborative prompt engineering

**Analytics**
- Team usage statistics
- Popular tools and workflows
- Efficiency metrics

---

### Phase 4: Advanced Integrations (Q4 2026)

**IDE Integration**
- VSCode extension
- JetBrains plugin
- Vim/Neovim integration

**CI/CD Integration**
- GitHub Actions integration
- GitLab CI integration
- Jenkins plugin

**Project Management**
- Jira integration
- Linear integration
- GitHub Issues integration

**Communication**
- Slack bot
- Discord bot
- Email notifications

---

## Feature Requests

Track feature requests in the feedback system:

```bash
dapy feedback submit "Feature request description" --category feature
```

View feature requests in the dashboard at `http://localhost:8889`

---

## Version History

### v0.1.0 (Current) - November 2025

**Initial Release**
- Core CLI framework
- 10 tools migrated from markdown agents
- 3 LangGraph workflows
- Full observability with LangSmith
- Interactive debugging with breakpoints
- Feedback system with Manus monitoring
- Server five deployment
- Remote inspection API
- Feedback dashboard

---

## Contributing

We welcome contributions! Areas where help is needed:

**Tools**
- Additional git operations
- Database operations
- API integrations
- Cloud service integrations

**Workflows**
- Domain-specific workflows
- Industry-specific workflows
- Custom workflow templates

**Integrations**
- IDE plugins
- CI/CD integrations
- Communication platforms

**Documentation**
- Usage examples
- Best practices
- Video tutorials
- Blog posts

---

## Feedback and Suggestions

Submit feedback using:

```bash
dapy feedback submit
```

Or via the dashboard at `http://localhost:8889`

Manus monitors all feedback and creates tickets for implementation.

---

## Priorities

**High Priority:**
1. LangChain Chat Proxy (Phase 1)
2. Code Review Workflow (Phase 2)
3. VSCode Extension (Phase 4)

**Medium Priority:**
1. Testing Workflow (Phase 2)
2. Multi-User Support (Phase 3)
3. GitHub Actions Integration (Phase 4)

**Low Priority:**
1. Documentation Workflow (Phase 2)
2. Team Analytics (Phase 3)
3. Communication Integrations (Phase 4)

Priorities may change based on user feedback and demand.

---

## Long-Term Vision

**DAPY as a Platform**
- Plugin system for custom tools
- Marketplace for workflows and tools
- Community-contributed integrations
- Enterprise features (SSO, audit logs, compliance)

**AI-Powered Development**
- Autonomous coding agents
- Intelligent code generation
- Predictive debugging
- Automated optimization

**Universal Interface**
- Single interface for all AI models
- Unified observability across providers
- Cost optimization across models
- Automatic model selection

---

## Timeline

| Phase | Features | Target |
|-------|----------|--------|
| Phase 1 | LangChain Chat Proxy | Q1 2026 |
| Phase 2 | Advanced Workflows | Q2 2026 |
| Phase 3 | Team Collaboration | Q3 2026 |
| Phase 4 | Advanced Integrations | Q4 2026 |

Timeline is subject to change based on feedback and priorities.

---

## Stay Updated

- Check this ROADMAP.md for updates
- Monitor feedback dashboard for progress
- Submit feedback for features you want
- Join discussions in GitHub Issues

---

Last Updated: November 26, 2025
