"""
Manus Inspector Service

FastAPI service that allows Manus to remotely inspect DAPY executions,
review snapshots, analyze failures, and suggest fixes.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime

from dapy.inspect import ExecutionInspector
from dapy.debug_export import DebugPackageExporter

app = FastAPI(
    title="DAPY Inspector Service",
    description="Remote inspection API for Manus to troubleshoot DAPY executions",
    version="0.1.0"
)

# Configuration from environment
SNAPSHOT_DIR = os.environ.get('DAPY_SNAPSHOT_DIR', '/app/snapshots')
LOGS_DIR = os.environ.get('DAPY_LOGS_DIR', '/app/logs')
DATA_DIR = os.environ.get('DAPY_DATA_DIR', '/app/data')
DEBUG_PACKAGES_DIR = os.environ.get('DAPY_DEBUG_PACKAGES_DIR', '/app/debug-packages')

inspector = ExecutionInspector(snapshot_dir=SNAPSHOT_DIR)
exporter = DebugPackageExporter(
    snapshot_dir=SNAPSHOT_DIR,
    logs_dir=LOGS_DIR
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "manus-inspector"}


@app.get("/api/status")
async def get_status():
    """Get overall system status."""
    snapshot_count = len(list(Path(SNAPSHOT_DIR).glob('snapshot_*.json'))) if Path(SNAPSHOT_DIR).exists() else 0
    
    return {
        "status": "operational",
        "snapshot_dir": SNAPSHOT_DIR,
        "logs_dir": LOGS_DIR,
        "data_dir": DATA_DIR,
        "snapshot_count": snapshot_count,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/executions/recent")
async def get_recent_executions(limit: int = 20):
    """
    Get recent executions summary.
    
    Args:
        limit: Number of recent executions to return
    """
    snapshot_dir = Path(SNAPSHOT_DIR)
    
    if not snapshot_dir.exists():
        return {"executions": []}
    
    snapshots = sorted(
        snapshot_dir.glob('snapshot_*.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:limit]
    
    executions = []
    for snapshot_file in snapshots:
        try:
            with open(snapshot_file) as f:
                data = json.load(f)
            
            executions.append({
                'file': snapshot_file.name,
                'timestamp': data.get('timestamp'),
                'type': data.get('type'),
                'metadata': data.get('metadata', {}),
                'size': snapshot_file.stat().st_size,
            })
        except Exception as e:
            continue
    
    return {"executions": executions, "count": len(executions)}


@app.get("/api/snapshot/{filename}")
async def get_snapshot(filename: str):
    """
    Get specific snapshot details.
    
    Args:
        filename: Snapshot filename
    """
    snapshot_path = Path(SNAPSHOT_DIR) / filename
    
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    try:
        with open(snapshot_path) as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading snapshot: {e}")


@app.get("/api/snapshot/{filename}/download")
async def download_snapshot(filename: str):
    """
    Download snapshot file.
    
    Args:
        filename: Snapshot filename
    """
    snapshot_path = Path(SNAPSHOT_DIR) / filename
    
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return FileResponse(
        path=snapshot_path,
        media_type='application/json',
        filename=filename
    )


@app.get("/api/logs/list")
async def list_logs():
    """List available log files."""
    logs_dir = Path(LOGS_DIR)
    
    if not logs_dir.exists():
        return {"logs": []}
    
    log_files = []
    for log_file in logs_dir.glob('*.log'):
        log_files.append({
            'filename': log_file.name,
            'size': log_file.stat().st_size,
            'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        })
    
    return {"logs": sorted(log_files, key=lambda x: x['modified'], reverse=True)}


@app.get("/api/logs/{filename}")
async def get_log(filename: str, lines: Optional[int] = None):
    """
    Get log file content.
    
    Args:
        filename: Log filename
        lines: Optional number of last lines to return
    """
    log_path = Path(LOGS_DIR) / filename
    
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    try:
        with open(log_path) as f:
            if lines:
                # Read last N lines
                content = f.readlines()
                content = content[-lines:]
                return {"content": ''.join(content), "lines": len(content)}
            else:
                content = f.read()
                return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log: {e}")


@app.post("/api/debug-package/create")
async def create_debug_package(description: Optional[str] = None):
    """
    Create a debug package for comprehensive troubleshooting.
    
    Args:
        description: Optional description of the issue
    """
    try:
        # Ensure debug packages directory exists
        Path(DEBUG_PACKAGES_DIR).mkdir(parents=True, exist_ok=True)
        
        # Create package
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"{DEBUG_PACKAGES_DIR}/debug_package_{timestamp}.tar.gz"
        
        package_path = exporter.create_debug_package(
            output_path=output_path,
            description=description
        )
        
        return {
            "success": True,
            "package_path": package_path,
            "filename": Path(package_path).name,
            "download_url": f"/api/debug-package/download/{Path(package_path).name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating debug package: {e}")


@app.get("/api/debug-package/download/{filename}")
async def download_debug_package(filename: str):
    """
    Download debug package.
    
    Args:
        filename: Debug package filename
    """
    package_path = Path(DEBUG_PACKAGES_DIR) / filename
    
    if not package_path.exists():
        raise HTTPException(status_code=404, detail="Debug package not found")
    
    return FileResponse(
        path=package_path,
        media_type='application/gzip',
        filename=filename
    )


@app.get("/api/analysis/summary")
async def get_analysis_summary():
    """
    Get analysis summary of recent executions.
    
    Provides overview of:
    - Recent tool calls
    - Error patterns
    - Execution statistics
    """
    snapshot_dir = Path(SNAPSHOT_DIR)
    
    if not snapshot_dir.exists():
        return {"error": "No snapshots available"}
    
    snapshots = sorted(
        snapshot_dir.glob('snapshot_*.json'),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:50]  # Analyze last 50
    
    tool_calls = {}
    errors = []
    
    for snapshot_file in snapshots:
        try:
            with open(snapshot_file) as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            tool = metadata.get('tool')
            
            if tool:
                tool_calls[tool] = tool_calls.get(tool, 0) + 1
            
            # Check for errors
            state = data.get('state', {})
            if 'error' in str(state).lower():
                errors.append({
                    'file': snapshot_file.name,
                    'timestamp': data.get('timestamp'),
                    'tool': tool
                })
        
        except Exception:
            continue
    
    return {
        "total_snapshots_analyzed": len(snapshots),
        "tool_call_frequency": tool_calls,
        "recent_errors": errors[:5],
        "error_count": len(errors)
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "DAPY Inspector Service",
        "version": "0.1.0",
        "description": "Remote inspection API for Manus",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "recent_executions": "/api/executions/recent",
            "snapshot": "/api/snapshot/{filename}",
            "logs": "/api/logs/list",
            "create_debug_package": "/api/debug-package/create",
            "analysis_summary": "/api/analysis/summary"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
