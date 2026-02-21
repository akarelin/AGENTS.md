# DAPY - Quick Start Guide

Get started with DAPY in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- LangChain API key ([get one here](https://smith.langchain.com))
- OpenAI API key ([get one here](https://platform.openai.com))

## Installation

### Option 1: Local Installation (Recommended for First Try)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/dapy.git
cd dapy

# 2. Install
pip install -e .

# 3. Set environment variables
export LANGCHAIN_API_KEY=your_langchain_api_key_here
export OPENAI_API_KEY=your_openai_api_key_here

# 4. Verify installation
dapy version
```

### Option 2: Docker (Recommended for Development)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/dapy.git
cd dapy

# 2. Create .env file
cp .env.example .env
# Edit .env and add your API keys

# 3. Start development container
docker-compose up -d

# 4. Enter container
docker-compose exec dapy-dev bash

# 5. Verify installation
dapy version
```

## First Commands

### 1. Check What's Next

```bash
dapy next
```

This reads your 2Do.md, ROADMAP.md, and git status to show what to work on next.

### 2. Ask a Question

```bash
dapy ask "What files have changed?"
```

### 3. Document Changes

```bash
dapy document
```

This automatically updates CHANGELOG.md based on git diff.

### 4. Close Session

```bash
dapy close
```

This updates 2Do.md, documents mistakes, and prepares for next session.

## Configuration

DAPY works with zero configuration, but you can customize it:

```bash
# Create config file
cat > dapy-config.yaml << EOF
model: openai:gpt-4o
debug: true
snapshot_enabled: true
EOF

# Use custom config
dapy --config dapy-config.yaml ask "What's next?"
```

## Common Workflows

### Daily Development

```bash
# Morning
dapy next                    # Check priorities

# During work
# ... make changes ...
dapy document                # Update changelog

# Evening
dapy push "Implemented X"    # Commit and push
dapy close                   # Close session
```

### With Breakpoints

```bash
# Pause before critical operations
dapy ask "Archive old code" --breakpoint archive_tool
```

### Debug Mode

```bash
# See detailed execution
dapy --debug ask "What's next?"
```

## Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Explore examples**: [EXAMPLES.md](EXAMPLES.md)
3. **Deploy to production**: [deployment/README.md](deployment/README.md)
4. **Customize prompts**: Edit files in `dapy/prompts/`

## Troubleshooting

### "API key not found"

```bash
# Check environment
dapy diag | grep API_KEY

# Set keys
export LANGCHAIN_API_KEY=lsv2_pt_...
export OPENAI_API_KEY=sk-...
```

### "Command not found: dapy"

```bash
# Reinstall
pip install -e .

# Or use python -m
python -m dapy.cli --help
```

### "Git command failed"

```bash
# Ensure you're in a git repository
git status

# Initialize if needed
git init
```

## Getting Help

- Run `dapy --help` for command help
- Run `dapy diag` for diagnostics
- Check [EXAMPLES.md](EXAMPLES.md) for usage patterns
- Review [README.md](README.md) for architecture details

## What's Next?

- Try all commands: ask, next, close, document, push
- Explore breakpoints and debugging features
- Review LangSmith traces at https://smith.langchain.com
- Customize prompts in `dapy/prompts/`
- Deploy to production (see deployment/README.md)

Welcome to DAPY!
