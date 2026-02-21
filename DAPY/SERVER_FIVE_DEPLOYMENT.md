# DeepAgents CLI - Server Five Deployment Summary

## What's Been Prepared

Complete Docker Compose deployment for server "five" with collaborative debugging capabilities between you and Manus.

## Architecture

**Two Services:**

1. **deepagents** - Your DeepAgents CLI instance
   - Interactive bash shell
   - Access to your repositories at `/repos`
   - Captures snapshots and logs automatically
   - SQLite persistence

2. **manus-inspector** - Remote inspection service for Manus
   - FastAPI service on port 8888
   - Read-only access to your snapshots and logs
   - Can create debug packages
   - Provides API for remote troubleshooting

## Workflow

### Your Side

1. Deploy to server five: `cd deployment/server-five && ./deploy.sh`
2. Use DeepAgents: `docker-compose exec deepagents bash`
3. When issues occur: Snapshots are auto-captured
4. Give Manus access: Provide server IP + port 8888
5. Apply fixes Manus suggests
6. Test again

### Manus Side

1. Access inspector API: `http://your-server:8888`
2. Review recent executions and snapshots
3. Analyze what went wrong
4. Suggest specific fixes (file, line number, change)
5. You apply fixes and test

## Files Created

### Deployment Configuration
- `deployment/server-five/docker-compose.yaml` - Main deployment config
- `deployment/server-five/.env.example` - Environment template
- `deployment/server-five/deploy.sh` - Deployment script
- `deployment/server-five/README.md` - Comprehensive deployment guide
- `deployment/server-five/WORKFLOW_QUICKREF.md` - Quick reference card

### Inspector Service
- `deepagents/inspector_service.py` - FastAPI service for remote inspection
- `Dockerfile.inspector` - Inspector service Docker image

### Debug Tools
- `deepagents/debug_export.py` - Debug package exporter
- `deepagents/inspect.py` - Local inspection utilities
- CLI commands: `deepagents inspect`, `deepagents export-debug`

## Key Features

**Automatic Capture:**
- Every execution creates snapshots
- All tool calls logged
- State captured before/after each step
- No manual intervention needed

**Remote Inspection:**
- Manus can access via HTTP API
- Read-only access to snapshots/logs
- Can create comprehensive debug packages
- No SSH or direct server access needed

**Collaborative Debugging:**
- You use DeepAgents normally
- When issues occur, give Manus access
- Manus analyzes remotely
- Suggests specific fixes
- You apply and test

**Security:**
- API keys in .env (not committed)
- You control firewall (port 8888)
- Manus has read-only access
- Data isolated in containers

## Deployment Steps

```bash
# 1. Extract archive on server five
tar -xzf deepagents-cli-server-five.tar.gz
cd deepagents-cli/deployment/server-five

# 2. Configure environment
cp .env.example .env
nano .env  # Add your API keys

# 3. Deploy
./deploy.sh

# 4. Test
docker-compose exec deepagents bash
deepagents version
deepagents next

# 5. Configure firewall for Manus access
sudo ufw allow from MANUS_IP to any port 8888
```

## Manus Inspector API

**Base URL:** `http://your-server-five:8888`

**Key Endpoints:**
- `GET /api/status` - System status
- `GET /api/executions/recent` - Recent executions
- `GET /api/snapshot/{filename}` - Snapshot details
- `GET /api/logs/list` - Available logs
- `POST /api/debug-package/create` - Create debug package
- `GET /api/analysis/summary` - Execution analysis

**Example Usage:**
```bash
# Check status
curl http://your-server:8888/api/status

# Get recent executions
curl http://your-server:8888/api/executions/recent?limit=20

# Create debug package
curl -X POST http://your-server:8888/api/debug-package/create
```

## Data Locations

All data stored in `/data/deepagents/`:
- `snapshots/` - Execution snapshots (JSON)
- `logs/` - Application logs
- `debug-packages/` - Generated debug packages
- `deepagents.db` - SQLite database

## Example Debugging Session

**Scenario:** Tool creates wrong project structure

1. **You:** Run command
   ```bash
   deepagents ask "Setup new project"
   # Creates wrong structure
   ```

2. **You:** Give Manus access
   - Provide: `http://server-five:8888`

3. **Manus:** Inspect remotely
   ```bash
   curl http://server-five:8888/api/executions/recent
   curl http://server-five:8888/api/snapshot/snapshot_latest.json
   ```

4. **Manus:** Analyze
   - Sees tool used wrong arguments
   - Identifies prompt issue
   - Suggests fix: "Update system_prompt.md line 45"

5. **You:** Apply fix
   ```bash
   nano deepagents/prompts/system_prompt.md
   docker-compose build deepagents
   docker-compose restart deepagents
   ```

6. **You:** Test
   ```bash
   deepagents ask "Setup new project"
   # Now creates correct structure!
   ```

## Integration with Your Infrastructure

Follows same patterns as your other services in `RAN/Services/`:
- Uses `/data/` for persistent storage
- Standard docker-compose structure
- Restart policy: `unless-stopped`
- Environment-based configuration

## Next Steps

1. ✅ Deploy to server five
2. ✅ Test basic operations
3. ✅ Configure firewall for port 8888
4. ✅ Test Manus inspector access
5. ✅ Start using for real workflows
6. ✅ When issues occur, collaborate with Manus

## Documentation

- **Deployment Guide:** `deployment/server-five/README.md`
- **Quick Reference:** `deployment/server-five/WORKFLOW_QUICKREF.md`
- **Main README:** `README.md`
- **Examples:** `EXAMPLES.md`

## Support

**For deployment issues:**
- Check `deployment/server-five/README.md`
- Review logs: `docker-compose logs`

**For DeepAgents behavior issues:**
- Use Manus inspector for collaborative debugging
- Export debug package: `deepagents export-debug "description"`

**For Manus access issues:**
- Verify firewall allows port 8888
- Check service status: `docker-compose ps manus-inspector`

## Archive Contents

```
deepagents-cli/
├── deepagents/                    # Main package
│   ├── inspector_service.py      # NEW: Manus inspector API
│   ├── debug_export.py           # NEW: Debug package exporter
│   ├── inspect.py                # NEW: Inspection utilities
│   └── ... (all other files)
├── deployment/
│   └── server-five/              # NEW: Server five deployment
│       ├── docker-compose.yaml
│       ├── deploy.sh
│       ├── .env.example
│       ├── README.md
│       └── WORKFLOW_QUICKREF.md
├── Dockerfile.inspector          # NEW: Inspector service image
└── ... (all other files)
```

## Ready to Deploy!

Everything is configured and ready. Just extract on server five and run `./deploy.sh`.

The collaborative debugging workflow will enable rapid iteration:
- You test and find issues
- Manus inspects remotely
- Suggests specific fixes
- You apply and test again
- Repeat until working perfectly

This is much more efficient than trying to debug in isolation!
