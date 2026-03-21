# Collaborative Debugging Workflow - Quick Reference

## Your Side (User)

### 1. Normal Usage
```bash
docker-compose exec dapy bash
cd /repos/your-project
dapy ask "Your query here"
```

### 2. When Something Goes Wrong
```bash
# Note the issue, snapshots are auto-captured
# No action needed - everything is logged
```

### 3. Give Remote Agent Access
```bash
# Ensure firewall allows port 8888
# Provide the remote agent with: http://your-server-five-ip:8888
```

### 4. While the Agent Inspects
```bash
# You can continue working or wait
# All data is read-only for the inspector
```

### 5. Apply Fixes
```bash
# Exit container
exit

# Edit prompts/tools as suggested by the agent
nano ../../dapy/prompts/system_prompt.md
nano ../../dapy/tools/your_tool.py

# Rebuild and restart
docker-compose build dapy
docker-compose restart dapy

# Test again
docker-compose exec dapy bash
dapy ask "Same query to test fix"
```

---

## Inspector Side (Remote Agent)

### 1. Access System
```bash
# Check health
curl http://server-five:8888/health

# Get status
curl http://server-five:8888/api/status
```

### 2. Review Recent Activity
```bash
# Get recent executions
curl http://server-five:8888/api/executions/recent?limit=20 | jq .

# Get analysis summary
curl http://server-five:8888/api/analysis/summary | jq .
```

### 3. Inspect Specific Execution
```bash
# List snapshots from recent executions response
# Then get specific snapshot
curl http://server-five:8888/api/snapshot/snapshot_TIMESTAMP.json | jq .
```

### 4. Review Logs
```bash
# List logs
curl http://server-five:8888/api/logs/list | jq .

# Get recent log entries
curl "http://server-five:8888/api/logs/dapy.log?lines=100"
```

### 5. Create Debug Package
```bash
# Create comprehensive package
curl -X POST http://server-five:8888/api/debug-package/create \
  -H "Content-Type: application/json" \
  -d '{"description": "Tool X failed with error Y"}' | jq .

# Download package
curl -O http://server-five:8888/api/debug-package/download/debug_package_TIMESTAMP.tar.gz
```

### 6. Analyze and Suggest Fixes
```bash
# Extract debug package locally
tar -xzf debug_package_TIMESTAMP.tar.gz
cd debug_package

# Review execution summary
cat execution_summary.json | jq .

# Inspect snapshots
cat snapshots/snapshot_TIMESTAMP.json | jq .

# Identify issue and suggest fixes
# Example: "Tool X is using wrong argument format in prompt"
# Suggest: "Update system_prompt.md line 123 to use correct format"
```

---

## Common Issues and Fixes

### Issue: Tool using wrong arguments
**Agent inspects**: Snapshot shows tool call with incorrect args
**Fix**: Update tool description in `dapy/prompts/system_prompt.md`

### Issue: Unexpected tool selection
**Agent inspects**: Analysis shows wrong tool chosen for task
**Fix**: Clarify tool descriptions and when to use each tool

### Issue: Tool execution failure
**Agent inspects**: Snapshot shows exception in tool result
**Fix**: Update tool implementation in `dapy/tools/tool_name.py`

### Issue: Incorrect workflow state
**Agent inspects**: Workflow state shows unexpected transitions
**Fix**: Update workflow logic in `dapy/workflows/workflow_name.py`

---

## API Endpoints Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/status` | GET | System status |
| `/api/executions/recent` | GET | Recent executions |
| `/api/snapshot/{file}` | GET | Snapshot details |
| `/api/logs/list` | GET | Available logs |
| `/api/logs/{file}` | GET | Log content |
| `/api/debug-package/create` | POST | Create debug package |
| `/api/analysis/summary` | GET | Execution analysis |

---

## Data Locations

| Data Type | Location | Access |
|-----------|----------|--------|
| Snapshots | `/data/dapy/snapshots/` | Read-only for inspector |
| Logs | `/data/dapy/logs/` | Read-only for inspector |
| Debug Packages | `/data/dapy/debug-packages/` | Read-write for inspector |
| Database | `/data/dapy/dapy.db` | Not exposed to inspector |

---

## Example Debugging Session

```bash
# User reports: "dapy ask 'Setup project' created wrong structure"

# Agent: Check recent executions
curl http://server-five:8888/api/executions/recent | jq '.executions[0]'

# Agent: Get that snapshot
curl http://server-five:8888/api/snapshot/snapshot_20251126_143022.json | jq .

# Agent: Sees tool call with args: {"structure": "flat"}
# Should be: {"structure": "nested"}

# Agent: Check prompt
# Finds: system_prompt.md describes structure incorrectly

# Agent suggests:
# "Update dapy/prompts/system_prompt.md line 45"
# "Change: 'Use flat structure by default'"
# "To: 'Use nested structure with src/ and tests/ directories'"

# User applies fix:
nano dapy/prompts/system_prompt.md
docker-compose build dapy
docker-compose restart dapy

# User tests:
dapy ask "Setup project"
# Now creates correct nested structure!
```

---

## Tips

**For User:**
- Don't clean snapshots until issue is resolved
- Provide clear description when exporting debug packages
- Test fixes immediately after applying

**For the Inspector:**
- Start with `/api/analysis/summary` for overview
- Check recent snapshots for immediate context
- Create debug package for complex issues
- Suggest specific file and line number changes
- Verify fix suggestion makes sense in context

---

## Firewall Configuration

User needs to allow remote agent access to port 8888:

```bash
# Example using ufw
sudo ufw allow from REMOTE_IP to any port 8888

# Example using iptables
sudo iptables -A INPUT -p tcp -s REMOTE_IP --dport 8888 -j ACCEPT
```

Replace `REMOTE_IP` with the actual remote agent IP.
