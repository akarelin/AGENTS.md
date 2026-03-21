"""
Debug package exporter for collaborative troubleshooting

Creates comprehensive debug packages that can be shared
for remote inspection and troubleshooting.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import tarfile
import shutil
from datetime import datetime
import os


class DebugPackageExporter:
    """
    Exports debug packages for collaborative troubleshooting.
    
    Collects all relevant information about a failed or problematic
    execution for remote inspection.
    """
    
    def __init__(
        self,
        snapshot_dir: str = './snapshots',
        logs_dir: str = './logs',
        config_file: Optional[str] = None
    ):
        """
        Initialize debug package exporter.
        
        Args:
            snapshot_dir: Directory containing snapshots
            logs_dir: Directory containing logs
            config_file: Optional config file path
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.logs_dir = Path(logs_dir)
        self.config_file = Path(config_file) if config_file else None
    
    def create_debug_package(
        self,
        output_path: Optional[str] = None,
        include_last_n_snapshots: int = 20,
        description: Optional[str] = None
    ) -> str:
        """
        Create a comprehensive debug package.
        
        Args:
            output_path: Where to save the package (default: ./debug_package_TIMESTAMP.tar.gz)
            include_last_n_snapshots: Number of recent snapshots to include
            description: Optional description of the issue
            
        Returns:
            Path to created debug package
        """
        # Generate output path if not provided
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f'./debug_package_{timestamp}.tar.gz'
        
        # Create temporary directory for package contents
        temp_dir = Path(f'.debug_package_temp_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # 1. Create manifest
            manifest = self._create_manifest(description)
            with open(temp_dir / 'MANIFEST.json', 'w') as f:
                json.dump(manifest, indent=2, fp=f)
            
            # 2. Copy recent snapshots
            snapshots_dest = temp_dir / 'snapshots'
            snapshots_dest.mkdir(exist_ok=True)
            self._copy_recent_snapshots(snapshots_dest, include_last_n_snapshots)
            
            # 3. Copy logs
            if self.logs_dir.exists():
                logs_dest = temp_dir / 'logs'
                shutil.copytree(self.logs_dir, logs_dest, dirs_exist_ok=True)
            
            # 4. Copy config
            if self.config_file and self.config_file.exists():
                shutil.copy2(self.config_file, temp_dir / 'config.yaml')
            
            # 5. Collect environment info
            env_info = self._collect_environment_info()
            with open(temp_dir / 'environment.json', 'w') as f:
                json.dump(env_info, indent=2, fp=f)
            
            # 6. Create execution summary
            summary = self._create_execution_summary()
            with open(temp_dir / 'execution_summary.json', 'w') as f:
                json.dump(summary, indent=2, fp=f)
            
            # 7. Create README for the package
            readme = self._create_package_readme(description)
            with open(temp_dir / 'README.md', 'w') as f:
                f.write(readme)
            
            # 8. Create tarball
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(temp_dir, arcname='debug_package')
            
            return str(Path(output_path).absolute())
        
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _create_manifest(self, description: Optional[str]) -> Dict[str, Any]:
        """Create manifest with package metadata."""
        return {
            'created_at': datetime.now().isoformat(),
            'description': description or 'Debug package for troubleshooting',
            'dapy_version': '0.1.0',
            'package_format_version': '1.0',
        }
    
    def _copy_recent_snapshots(self, dest_dir: Path, limit: int) -> None:
        """Copy recent snapshots to package."""
        if not self.snapshot_dir.exists():
            return
        
        snapshots = sorted(
            self.snapshot_dir.glob('snapshot_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        for snapshot in snapshots:
            shutil.copy2(snapshot, dest_dir / snapshot.name)
    
    def _collect_environment_info(self) -> Dict[str, Any]:
        """Collect environment information."""
        import sys
        import platform
        
        return {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.machine(),
            'environment_variables': {
                'LANGCHAIN_TRACING_V2': os.environ.get('LANGCHAIN_TRACING_V2', 'not set'),
                'LANGCHAIN_PROJECT': os.environ.get('LANGCHAIN_PROJECT', 'not set'),
                'DAPY_MODEL': os.environ.get('DAPY_MODEL', 'not set'),
                # Don't include API keys
            },
            'working_directory': os.getcwd(),
        }
    
    def _create_execution_summary(self) -> Dict[str, Any]:
        """Create summary of recent executions."""
        if not self.snapshot_dir.exists():
            return {'snapshots': []}
        
        snapshots = sorted(
            self.snapshot_dir.glob('snapshot_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:20]
        
        summary = []
        for snapshot_file in snapshots:
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)
                
                summary.append({
                    'file': snapshot_file.name,
                    'timestamp': data.get('timestamp'),
                    'type': data.get('type'),
                    'metadata': data.get('metadata', {}),
                })
            except Exception:
                continue
        
        return {'snapshots': summary}
    
    def _create_package_readme(self, description: Optional[str]) -> str:
        """Create README for the debug package."""
        return f"""# DAPY Debug Package

**Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Description

{description or 'Debug package for troubleshooting DAPY execution.'}

## Contents

- `MANIFEST.json` - Package metadata
- `README.md` - This file
- `environment.json` - Environment information
- `execution_summary.json` - Summary of recent executions
- `snapshots/` - Recent execution snapshots
- `logs/` - Application logs (if available)
- `config.yaml` - Configuration file (if available)

## Usage

This package contains all information needed for remote troubleshooting:

1. **Snapshots** contain full execution state at each step
2. **Logs** contain detailed execution traces
3. **Environment info** shows system configuration
4. **Execution summary** provides overview of recent activity

## For Troubleshooter

To inspect this package:

```bash
# Extract
tar -xzf debug_package_*.tar.gz
cd debug_package

# Review execution summary
cat execution_summary.json

# Inspect recent snapshots
ls -lt snapshots/

# View specific snapshot
cat snapshots/snapshot_*.json | jq .

# Check environment
cat environment.json
```

## Next Steps

1. Review execution_summary.json for overview
2. Inspect snapshots/ for detailed state
3. Check logs/ for execution traces
4. Identify issue and suggest fixes
"""


def create_debug_package(
    description: Optional[str] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Quick function to create debug package.
    
    Args:
        description: Description of the issue
        output_path: Where to save the package
        
    Returns:
        Path to created package
    """
    exporter = DebugPackageExporter()
    return exporter.create_debug_package(
        output_path=output_path,
        description=description
    )
