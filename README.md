# AGENTS.md

An unfinished, evolving collection of everything agentic — prompt engineering patterns, autonomous agent instructions, multi-agent orchestration experiments, and tooling. This is a working dumping ground, not a polished framework.

## Status
Work in progress. Some parts are battle-tested across multiple repos, others are half-baked experiments. The multi-agent orchestration (`agent-swarm/`, `.claude-code.yaml`) hit limitations with Claude Code's actual agent system and needs a pivot. DeepAgents CLI has working code but is not deployed.

### In development
- **DeepAgents CLI**: A more ambitious attempt to wrap the whole workflow into a LangChain-based CLI tool

### Legacy approaches
- **AGENTS.md as a pattern**: A single markdown file that tells any LLM agent how to behave in a repository — session management, git workflow, mistake tracking, changelog conventions
- **Multi-agent orchestration**: Experiments with specialized subagents (changelog, docs, archive, validation, push) coordinated by a parent knowledge-management agent
- **Mistake-driven improvement**: Agents log their own mistakes; those patterns feed back into better instructions


## What's where

```
.
├── AGENTS.md                  → Master instructions for autonomous agents (Claude, Gemini, etc.)
├── AGENTS_mistakes.md         → Log of agent mistakes and lessons learned
├── INSTRUCTIONS_CORE.md       → Shared core instructions across all projects
├── INSTRUCTIONS_EXPERIMENTAL.md → Experimental workflow ideas (session management, auto-PR)
├── ROADMAP.md                 → Project roadmap and epics
├── 2Do.md                     → Current priorities and task tracking
│
├── agents/                    → Specialized subagent definitions
│   ├── knowledge-management-agent.md
│   ├── changelog-agent.md
│   ├── docs-agent.md
│   ├── archive-agent.md
│   ├── validation-agent.md
│   ├── push-agent.md
│   └── mistake-review-agent.md
│
├── agent-swarm/               → Multi-agent orchestration experiments
│   ├── ORCHESTRATOR.md
│   ├── claude-code-orchestration-plan.md
│   └── agents/                → Alternative agent definitions
│
├── DeepAgents/                → LangChain/LangGraph CLI for agentic workflows
│   ├── deepagents/            → Python package (orchestrator, tools, middleware)
│   └── deployment/            → Docker, GCP, LangChain Cloud configs
│
├── docs/                      → Templates, plans, and guides
│   ├── templates/             → README, AGENTS, archive templates
│   ├── plans/                 → Subagent project plans
│   └── guides/                → Best practices (archiving, etc.)
│
└── archive/                   → Previous iterations of AGENTS.md
```

