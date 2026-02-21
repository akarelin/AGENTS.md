# DAPY - Server Five Deployment

This deployment configuration sets up DAPY on server "five" with Manus remote inspection capabilities for collaborative debugging.

## Architecture

```
Server Five
├── dapy (container)                # Your DAPY instance
│   ├── Interactive shell
│   ├── Snapshots → /data/dapy/snapshots
│   ├── Logs → /data/dapy/logs
│   └── Working directory → /repos
│
└── manus-inspector (container)     # Manus inspection service
    ├── API on port 8888
    ├── Read-only access to snapshots/logs
    └── Debug package generation
```

## Quick Start

### 1. Initial Setup

```bash
# Navigate to deployment directory
cd deployment/server-five

# Create .env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Deploy

```bash
# Run deployment script
./deploy.sh
```

### 3. Use DAPY

```bash
# Enter DAPY container
docker-compose exec dapy bash

# Inside container
cd /repos/your-project
dapy next
dapy ask "What should I work on?"
```

## Collaborative Debugging Workflow

### Your Workflow

1. **Use DAPY normally**
   ```bash
   docker-compose exec dapy bash
   cd /repos/your-project
   dapy ask "Setup new project"
   ```

2. **When something goes wrong**
   - Note the issue (invalid tool use, unexpected behavior, etc.)
   - Execution state is automatically captured in snapshots

3. **Give Manus access**
   - Ensure port 8888 is accessible (you handle firewall)
   - Provide Manus with server IP and port
   - Example: `http://your-server-five-ip:8888`

4. **Manus inspects remotely**
   - Reviews recent executions
   - Analyzes snapshots
   - Identifies root cause
   - Suggests fixes

5. **Apply fixes**
   - Update prompts in `dapy/prompts/`
   - Modify tool implementations if needed
   - Rebuild: `docker-compose build dapy`
   - Restart: `docker-compose restart dapy`

6. **Continue testing**
   - Test the fix
   - Repeat if needed

### Manus Workflow

When you provide access, Manus can:

1. **Check system status**
   ```bash
   curl http://your-server:8888/api/status
   ```

2. **Review recent executions**
   ```bash
   curl http://your-server:8888/api/executions/recent?limit=20
   ```

3. **Inspect specific snapshot**
   ```bash
   curl http://your-server:8888/api/snapshot/snapshot_20251126_143022.json
   ```

4. **Get analysis summary**
   ```bash
   curl http://your-server:8888/api/analysis/summary
   ```

5. **Create debug package**
   ```bash
   curl -X POST http://your-server:8888/api/debug-package/create \
     -H "Content-Type: application/json" \
     -d '{"description": "Tool X failed with error Y"}'
   ```

6. **Download debug package**
   ```bash
   curl -O http://your-server:8888/api/debug-package/download/debug_package_20251126.tar.gz
   ```

## Manus Inspector API Endpoints

### Status and Health

- `GET /health` - Health check
- `GET /api/status` - System status and configuration
- `GET /` - API documentation

### Execution Inspection

- `GET /api/executions/recent?limit=20` - Recent executions summary
- `GET /api/snapshot/{filename}` - Get specific snapshot details
- `GET /api/snapshot/{filename}/download` - Download snapshot file
- `GET /api/analysis/summary` - Analysis of recent executions

### Logs

- `GET /api/logs/list` - List available log files
- `GET /api/logs/{filename}?lines=100` - Get log content (optionally last N lines)

### Debug Packages

- `POST /api/debug-package/create` - Create comprehensive debug package
- `GET /api/debug-package/download/{filename}` - Download debug package

## Data Locations

All data is stored in `/data/dapy/`:

```
/data/dapy/
├── snapshots/              # Execution snapshots (JSON)
├── logs/                   # Application logs
├── debug-packages/         # Generated debug packages
└── dapy.db                 # SQLite database (if using SQLite)
```

## Common Operations

### View Logs

```bash
# View DAPY logs
docker-compose logs -f dapy

# View Manus inspector logs
docker-compose logs -f manus-inspector
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart dapy
```

### Update Deployment

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d
```

### Backup Data

```bash
# Backup all data
sudo tar -czf dapy-backup-$(date +%Y%m%d).tar.gz /data/dapy/

# Backup just snapshots
sudo tar -czf snapshots-backup-$(date +%Y%m%d).tar.gz /data/dapy/snapshots/
```

### Clean Up Old Snapshots

```bash
# Keep only last 100 snapshots
cd /data/dapy/snapshots
ls -t snapshot_*.json | tail -n +101 | xargs rm -f
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs dapy
docker-compose logs manus-inspector

# Verify environment
docker-compose config

# Check data directory permissions
ls -la /data/dapy
```

### Can't Access Manus Inspector

```bash
# Check if service is running
docker-compose ps manus-inspector

# Test locally
curl http://localhost:8888/health

# Check firewall (you handle this)
# Ensure port 8888 is open for Manus access
```

### Out of Disk Space

```bash
# Check disk usage
df -h /data

# Clean old snapshots
find /data/dapy/snapshots -name "snapshot_*.json" -mtime +7 -delete

# Clean old logs
find /data/dapy/logs -name "*.log" -mtime +30 -delete

# Clean old debug packages
find /data/dapy/debug-packages -name "*.tar.gz" -mtime +7 -delete
```

### DAPY Behaving Incorrectly

1. **Export debug package**
   ```bash
   docker-compose exec dapy dapy export-debug "Description of issue"
   ```

2. **Or use Manus inspector API**
   ```bash
   curl -X POST http://localhost:8888/api/debug-package/create
   ```

3. **Give Manus access to inspect**
   - Provide server IP and port 8888
   - Manus will analyze and suggest fixes

4. **Apply fixes to prompts/tools**
   ```bash
   # Edit files in dapy/prompts/ or dapy/tools/
   nano ../../dapy/prompts/system_prompt.md

   # Rebuild
   docker-compose build dapy

   # Restart
   docker-compose restart dapy
   ```

## Security Considerations

1. **API Keys** - Stored in .env file, not committed to git
2. **Firewall** - You control access to port 8888
3. **Read-only Access** - Manus inspector has read-only access to snapshots/logs
4. **SSH Keys** - Mounted read-only for git operations
5. **Data Isolation** - Each service runs in isolated container

## Integration with Existing Services

This deployment follows the same pattern as other services in `RAN/Services/`:

- Uses `/data/` for persistent storage
- Follows standard docker-compose structure
- Restart policy: `unless-stopped`
- Environment-based configuration

## Next Steps

1. Deploy to server five: `./deploy.sh`
2. Test basic operations: `dapy next`
3. Configure firewall for port 8888
4. Test Manus inspector access
5. Start using DAPY for your workflows

## Support

For issues with:
- **Deployment**: Check logs and this README
- **DAPY behavior**: Use Manus inspector for collaborative debugging
- **Manus access**: Ensure firewall allows port 8888

## Example Session

```bash
# 1. Deploy
cd deployment/server-five
./deploy.sh

# 2. Enter DAPY
docker-compose exec dapy bash

# 3. Use DAPY
cd /repos/my-project
dapy next
dapy ask "Setup new project with README and structure"

# 4. If something goes wrong
dapy export-debug "Setup command created wrong structure"

# 5. Give Manus access (from another terminal)
# Manus can now access: http://your-server-five:8888

# 6. Manus inspects remotely
curl http://your-server-five:8888/api/executions/recent
curl http://your-server-five:8888/api/analysis/summary

# 7. Apply fixes suggested by Manus
exit  # Exit container
nano ../../dapy/prompts/system_prompt.md
docker-compose build dapy
docker-compose restart dapy

# 8. Test again
docker-compose exec dapy bash
cd /repos/my-project
dapy ask "Setup new project with README and structure"
```

This workflow enables rapid iteration and debugging with Manus's help!
