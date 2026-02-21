# Unified LLM Interface & Logging Analysis

## Overview

Analysis of how to capture ALL LLM interactions (ChatGPT, Claude, Cursor, Claude Code, iOS apps) and route them through a unified interface with LangSmith logging.

---

## Part 1: CLI Tool Logging

### Chat Log Exports - What's Included?

**ChatGPT Web:**
- ✅ Included in official export
- Format: `conversations.json`
- Export: Settings → Data Controls → Export

**Claude Web:**
- ✅ Included in official export
- Format: JSON
- Export: Settings → Privacy → Export Data

**Cursor IDE:**
- ❌ NOT included in ChatGPT/Claude exports
- Separate application with own database
- Location: `~/.config/Cursor/User/workspaceStorage/` (Mac/Linux)
- Location: `%APPDATA%\Cursor\User\workspaceStorage` (Windows)
- Format: SQLite databases

**Claude Code (Desktop App):**
- ❌ NOT included in Claude web export
- Separate local storage
- Location: `~/.claude/projects/` (Mac/Linux)
- Format: Project-specific logs

**Codex CLI:**
- ❌ NOT included in ChatGPT export
- Separate CLI tool logs
- No official export feature yet
- Community tools available

### How to Export CLI Tool Data

#### Cursor IDE

**Method 1: Built-in Export**
- Navigate to chat
- Click context menu → "Export Chat"
- Saves single chat to file

**Method 2: Database Export (All Chats)**
```bash
# Mac/Linux
cd ~/.config/Cursor/User/workspaceStorage

# Windows
cd %APPDATA%\Cursor\User\workspaceStorage

# Find SQLite databases
find . -name "*.vscdb" -o -name "state.vscdb"

# Use SQLite tool to export
sqlite3 <hash>/state.vscdb ".dump" > cursor_export.sql
```

**Method 3: Community Tools**
- `cursor-export` - Export all chats to Markdown/HTML/JSON
- `Cursor Convo Export` - VSCode extension
- GitHub: Various export scripts

**Method 4: Python Script**
```python
import sqlite3
import json
from pathlib import Path

def export_cursor_chats(workspace_dir):
    """Export all Cursor chats from workspace storage."""
    chats = []
    
    for db_path in Path(workspace_dir).rglob("state.vscdb"):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query chat history
        cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%chat%'")
        
        for key, value in cursor.fetchall():
            chats.append({
                'key': key,
                'data': json.loads(value)
            })
        
        conn.close()
    
    return chats
```

#### Claude Code

**Method 1: Project Logs**
```bash
# Mac/Linux
cd ~/.claude/projects/

# Each project has logs
find . -name "*.log" -o -name "chat_*.json"
```

**Method 2: Community Tool**
- `claude-conversation-extractor` (GitHub: ZeroSumQuant/claude-conversation-extractor)
- Extracts from `~/.claude/projects`
- Exports to JSON/Markdown

**Method 3: Resume Command**
```bash
# Claude Code CLI
claude --resume

# Shows all previous conversations
# Can manually copy/export
```

#### Codex CLI

**Current Status:**
- No official export feature
- Community requests for export (GitHub issues #2880, #5781)
- Logs exist but not easily accessible

**Workaround:**
```bash
# Codex stores logs, but format varies
# Check for log files in:
~/.openai/codex/logs/  # (hypothetical location)

# Or capture output during execution
codex exec "task" > output.json
```

**Community Tools:**
- Various scripts to parse Codex output
- No standardized export yet

---

## Part 2: Unified LLM Interface Options

### Option 1: Use Existing iOS Apps

**LLMConnect** (Recommended)
- Native iOS app
- Supports multiple providers (OpenAI, Anthropic, OpenRouter, local models)
- Use your own API keys
- Single unified interface
- Available on App Store

**Pros:**
- ✅ Already exists, no development needed
- ✅ Native iOS experience
- ✅ Multiple providers in one app
- ✅ Your API keys (no middleman costs)

**Cons:**
- ❌ No LangSmith integration (no logging to LangSmith)
- ❌ Can't capture interactions for analysis
- ❌ Limited to what the app provides

**Chatbox AI**
- Desktop and mobile (Windows, Mac, Linux, Android, iOS)
- Multiple LLM providers
- Your own API keys
- Cross-platform sync

**Pros:**
- ✅ Cross-platform (use on all devices)
- ✅ Multiple providers
- ✅ Free and open source

**Cons:**
- ❌ No LangSmith integration
- ❌ Recently delisted from iOS App Store (may return)

### Option 2: LLM Proxy with Logging

**Architecture:**
```
Your Apps/Devices
    ↓
LLM Proxy Server (with LangSmith logging)
    ↓
OpenAI/Anthropic/etc APIs
```

**Available Proxies:**

**LiteLLM Proxy**
- Unified interface for 100+ LLM providers
- Built-in logging and observability
- LangSmith integration available
- Self-hosted

**PromptSail**
- Open source LLM proxy
- Transparently logs all interactions
- Multiple provider support
- Self-hosted

**Helicone**
- LLM observability platform
- Proxy mode for logging
- Works with any provider
- Hosted or self-hosted

**Langfuse Proxy**
- LLM observability and tracing
- Proxy mode available
- LangSmith alternative
- Self-hosted

**How It Works:**
1. Deploy proxy server (e.g., on server five)
2. Configure with your API keys
3. Point all apps to proxy instead of direct APIs
4. Proxy logs everything to LangSmith
5. Forwards requests to actual LLM providers

**Pros:**
- ✅ Captures ALL interactions
- ✅ Works with any app/device
- ✅ Full LangSmith logging
- ✅ Centralized observability
- ✅ No app changes needed (just change API endpoint)

**Cons:**
- ❌ Requires running proxy server
- ❌ Single point of failure
- ❌ Adds latency
- ❌ Need to configure each app

### Option 3: Build Custom iOS App

**Architecture:**
```
Custom iOS App
    ↓
Your Backend (with LangSmith)
    ↓
OpenAI/Anthropic/etc APIs
```

**What It Takes:**

**Development Effort:**
- Swift/SwiftUI development
- API integration for multiple providers
- Chat UI implementation
- Message history and sync
- Settings and configuration

**Time Estimate:**
- Basic chat app: 2-4 weeks
- Multi-provider support: +1-2 weeks
- Polish and features: +2-4 weeks
- Total: 1-2 months

**Technologies:**
- Swift 6.0+
- SwiftUI for UI
- langchain-swift (if using LangChain)
- URLSession for API calls
- Core Data for local storage

**Pros:**
- ✅ Full control over features
- ✅ Perfect LangSmith integration
- ✅ Custom UI/UX
- ✅ Can add unique features

**Cons:**
- ❌ Significant development time
- ❌ Ongoing maintenance
- ❌ iOS only (need separate Android)
- ❌ App Store approval process

### Option 4: Progressive Web App (PWA)

**Architecture:**
```
PWA (works on iOS Safari)
    ↓
Your Backend (with LangSmith)
    ↓
OpenAI/Anthropic/etc APIs
```

**What It Takes:**
- React/Vue/Next.js web app
- Responsive mobile design
- Service worker for offline
- Add to Home Screen support

**Time Estimate:**
- Basic PWA: 1-2 weeks
- Multi-provider: +1 week
- Mobile optimization: +1 week
- Total: 3-4 weeks

**Pros:**
- ✅ Works on iOS without App Store
- ✅ Also works on Android, desktop
- ✅ Single codebase
- ✅ Easy updates (no app review)
- ✅ Full LangSmith integration

**Cons:**
- ❌ Not as native feeling
- ❌ Limited iOS features
- ❌ Requires internet connection
- ❌ Less discoverable (no App Store)

---

## Part 3: Recommended Architecture

### For Maximum Coverage

**Phase 1: Proxy Setup (Immediate)**

Deploy LiteLLM Proxy on server five:

```yaml
# litellm-config.yaml
model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: ${OPENAI_API_KEY}
  
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: ${ANTHROPIC_API_KEY}

litellm_settings:
  success_callback: ["langsmith"]
  
langsmith_config:
  api_key: ${LANGCHAIN_API_KEY}
  project: unified-llm-interface
```

**Benefits:**
- Captures all API calls
- Works with existing apps
- Full LangSmith logging
- No app development needed

**Phase 2: Web Interface (Q1 2026)**

Build PWA for mobile access:
- Chat interface
- Model selection
- Conversation history
- Works on iOS/Android/Desktop
- Routes through proxy

**Phase 3: CLI Tool Integration (Q1 2026)**

Export and import CLI tool data:
- Cursor export script
- Claude Code export script
- Codex log parser
- Automated import to LangSmith

---

## Part 4: iOS App Options Summary

### Keep Using Native Apps

**Option A: Use LLMConnect**
- Download from App Store
- Add your API keys
- Use as normal
- ❌ No LangSmith logging

**Option B: Configure to Use Proxy**
- Use LLMConnect or Chatbox
- Change API endpoint to your proxy
- ✅ Gets LangSmith logging
- Requires proxy setup

### Use Third-Party Unified App

**Chatbox AI** (if available)
- Cross-platform
- Multiple providers
- Can configure custom endpoints
- Point to your proxy for logging

### Build Custom iOS App

**Effort:** 1-2 months development
**Cost:** Your time or hire developer
**Result:** Perfect integration with LangSmith

**Recommendation:** Only if you need unique features

### Use PWA

**Effort:** 3-4 weeks development
**Cost:** Less than native app
**Result:** Works on all platforms

**Recommendation:** Best balance of effort vs coverage

---

## Part 5: Implementation Plan

### Immediate: Export Historical Data

```bash
# 1. Export ChatGPT
# Web: Settings → Data Controls → Export

# 2. Export Claude
# Web: Settings → Privacy → Export Data

# 3. Export Cursor
cd ~/.config/Cursor/User/workspaceStorage
# Use export script or tool

# 4. Export Claude Code
cd ~/.claude/projects
# Use claude-conversation-extractor

# 5. Import all to LangSmith
deepagents import chatgpt conversations.json
deepagents import claude claude_export.json
deepagents import cursor cursor_export.json
deepagents import claude-code claude_code_export.json
```

### Phase 1: Proxy Setup (Week 1-2)

```bash
# Deploy LiteLLM Proxy on server five
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e LANGCHAIN_API_KEY=$LANGCHAIN_API_KEY \
  -v $(pwd)/litellm-config.yaml:/app/config.yaml \
  ghcr.io/berriai/litellm:latest \
  --config /app/config.yaml

# Test proxy
curl http://server-five:8000/v1/chat/completions \
  -H "Authorization: Bearer $PROXY_KEY" \
  -d '{"model": "gpt-4", "messages": [...]}'

# Verify LangSmith logging
# Check LangSmith UI for traces
```

### Phase 2: Configure Apps (Week 3)

**iOS Apps:**
- LLMConnect: Settings → API Endpoint → `http://server-five:8000`
- Add proxy auth key

**Desktop Tools:**
- Cursor: Configure custom API endpoint (if possible)
- Claude Code: Configure custom endpoint

### Phase 3: PWA Development (Q1 2026)

```bash
# Create Next.js PWA
npx create-next-app@latest unified-llm-pwa
cd unified-llm-pwa

# Add features:
# - Chat interface
# - Model selection (GPT-4, Claude, etc.)
# - Conversation history
# - PWA manifest
# - Service worker

# Deploy
# Access from iOS: Add to Home Screen
```

### Phase 4: CLI Tool Export Automation (Q1 2026)

```python
# deepagents/tools/cli_exporters.py

class CursorExporter:
    """Export Cursor IDE chat history."""
    
class ClaudeCodeExporter:
    """Export Claude Code conversations."""
    
class CodexExporter:
    """Export Codex CLI logs."""

# CLI commands
deepagents export cursor
deepagents export claude-code
deepagents export codex
```

---

## Part 6: Cost Analysis

### Option 1: Use Existing Apps + Proxy

**Setup Cost:**
- Proxy server: $0 (use server five)
- LiteLLM: Free (open source)
- LLMConnect app: Free

**Ongoing Cost:**
- Server: Already have
- API calls: Same as now (your keys)
- LangSmith: $39-199/month

**Total: $39-199/month** (just LangSmith)

### Option 2: Build Custom iOS App

**Development Cost:**
- Your time: 1-2 months
- Or hire: $5,000-15,000

**Ongoing Cost:**
- Maintenance: Your time
- Apple Developer: $99/year
- Server + LangSmith: $39-199/month

**Total: $5,000-15,000 upfront + $138-298/month**

### Option 3: Build PWA

**Development Cost:**
- Your time: 3-4 weeks
- Or hire: $3,000-8,000

**Ongoing Cost:**
- Hosting: $10-50/month
- LangSmith: $39-199/month

**Total: $3,000-8,000 upfront + $49-249/month**

---

## Recommendations

### For Immediate Use

1. **Export all historical data** (ChatGPT, Claude, Cursor, Claude Code)
2. **Import to LangSmith** using DeepAgents import tools
3. **Deploy LiteLLM Proxy** on server five
4. **Use LLMConnect on iOS** pointed to proxy
5. **Use Cursor/Claude Code** as normal (export periodically)

**Result:** Captures most interactions with minimal effort

### For Long-Term

1. **Build PWA** (Q1 2026) for unified mobile/desktop interface
2. **Automate CLI tool exports** (Q1 2026)
3. **Continuous import** to LangSmith
4. **Optimize based on data** (Phase 1A roadmap)

**Result:** Complete coverage, all interactions logged

### For iOS Specifically

**Short-term:** Use LLMConnect app (free, works now)

**Long-term:** 
- If PWA is good enough: Use PWA (works on iOS)
- If need native app: Build custom (1-2 months)

**Recommendation:** Start with LLMConnect, evaluate PWA, decide on native app later

---

## Next Steps

1. **Decide on approach:**
   - Proxy only?
   - Proxy + PWA?
   - Proxy + native app?

2. **Priority:**
   - High: Deploy proxy this week
   - Medium: Build PWA in Q1
   - Low: Consider native app later

3. **Export historical data:**
   - ChatGPT, Claude (easy)
   - Cursor, Claude Code (need scripts)
   - Codex (if applicable)

4. **Test proxy setup:**
   - Deploy on server five
   - Configure LangSmith logging
   - Test with one app

5. **Scale up:**
   - Configure all apps
   - Monitor in LangSmith
   - Optimize based on data

---

## Questions to Answer

1. **Do you want to deploy proxy now?**
   - Would capture all future interactions
   - Minimal effort to set up

2. **Which iOS app to use?**
   - LLMConnect (recommended)
   - Chatbox (if available)
   - Build custom (later)

3. **PWA vs Native App?**
   - PWA: Faster, works everywhere
   - Native: Better UX, iOS only

4. **CLI tool export priority?**
   - High: Need Cursor/Claude Code data
   - Medium: Export periodically
   - Low: Not critical

Let me know your preferences and I'll create detailed implementation guides!
