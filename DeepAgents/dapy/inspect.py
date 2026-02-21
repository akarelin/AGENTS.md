"""
Inspection utilities for reviewing and debugging DeepAgents executions

Provides tools to quickly review recent executions, snapshots, and traces
to identify issues and make corrections.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()


class ExecutionInspector:
    """
    Inspector for reviewing recent DeepAgents executions.
    
    Helps with the iterative debugging workflow by providing
    quick access to execution history, snapshots, and traces.
    """
    
    def __init__(self, snapshot_dir: str = './snapshots'):
        """
        Initialize execution inspector.
        
        Args:
            snapshot_dir: Directory containing snapshots
        """
        self.snapshot_dir = Path(snapshot_dir)
    
    def show_recent_executions(self, limit: int = 10) -> None:
        """
        Show recent executions with summary.
        
        Args:
            limit: Number of recent executions to show
        """
        if not self.snapshot_dir.exists():
            console.print("[yellow]No snapshots directory found[/yellow]")
            return
        
        snapshots = sorted(
            self.snapshot_dir.glob('snapshot_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        if not snapshots:
            console.print("[yellow]No snapshots found[/yellow]")
            return
        
        table = Table(title=f"Recent Executions (Last {len(snapshots)})")
        table.add_column("Time", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Tool/Phase", style="yellow")
        table.add_column("File", style="dim")
        
        for snapshot_file in snapshots:
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', 'unknown')
                snap_type = data.get('type', 'unknown')
                metadata = data.get('metadata', {})
                tool_name = metadata.get('tool', metadata.get('phase', 'unknown'))
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp[:8] if len(timestamp) > 8 else timestamp
                
                table.add_row(
                    time_str,
                    snap_type,
                    tool_name,
                    snapshot_file.name
                )
            except Exception as e:
                console.print(f"[red]Error reading {snapshot_file.name}: {e}[/red]")
        
        console.print(table)
        console.print(f"\n[dim]Snapshot directory: {self.snapshot_dir}[/dim]")
    
    def inspect_snapshot(self, snapshot_file: str) -> None:
        """
        Inspect a specific snapshot in detail.
        
        Args:
            snapshot_file: Name or path of snapshot file
        """
        # Find snapshot file
        if '/' in snapshot_file:
            snapshot_path = Path(snapshot_file)
        else:
            snapshot_path = self.snapshot_dir / snapshot_file
        
        if not snapshot_path.exists():
            console.print(f"[red]Snapshot not found: {snapshot_path}[/red]")
            return
        
        # Load snapshot
        with open(snapshot_path) as f:
            data = json.load(f)
        
        # Display header
        console.print(Panel(
            f"[bold]Snapshot Inspection[/bold]\n\n"
            f"File: {snapshot_path.name}\n"
            f"Type: {data.get('type', 'unknown')}\n"
            f"Time: {data.get('timestamp', 'unknown')}",
            border_style="cyan"
        ))
        
        # Display metadata
        metadata = data.get('metadata', {})
        if metadata:
            console.print("\n[bold]Metadata:[/bold]")
            console.print(Syntax(json.dumps(metadata, indent=2), "json", theme="monokai"))
        
        # Display state
        state = data.get('state', {})
        if state:
            console.print("\n[bold]State:[/bold]")
            # Truncate large values for readability
            state_display = {
                k: str(v)[:200] + '...' if len(str(v)) > 200 else v
                for k, v in state.items()
            }
            console.print(Syntax(json.dumps(state_display, indent=2, default=str), "json", theme="monokai"))
    
    def show_last_error(self) -> None:
        """
        Show details of the most recent error or failed execution.
        """
        snapshots = sorted(
            self.snapshot_dir.glob('snapshot_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for snapshot_file in snapshots:
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)
                
                # Check for error indicators
                state = data.get('state', {})
                metadata = data.get('metadata', {})
                
                # Look for error in state or metadata
                error_found = False
                error_msg = None
                
                if 'error' in str(state).lower() or 'exception' in str(state).lower():
                    error_found = True
                    error_msg = str(state)
                
                if error_found:
                    console.print(Panel(
                        f"[bold red]Last Error Found[/bold red]\n\n"
                        f"File: {snapshot_file.name}\n"
                        f"Time: {data.get('timestamp', 'unknown')}\n"
                        f"Type: {data.get('type', 'unknown')}",
                        border_style="red"
                    ))
                    
                    console.print("\n[bold]Error Details:[/bold]")
                    console.print(error_msg[:500])
                    
                    console.print(f"\n[dim]Full snapshot: {snapshot_file}[/dim]")
                    return
            
            except Exception as e:
                continue
        
        console.print("[green]No recent errors found[/green]")
    
    def compare_snapshots(self, file1: str, file2: str) -> None:
        """
        Compare two snapshots to see what changed.
        
        Args:
            file1: First snapshot file
            file2: Second snapshot file
        """
        # Load both snapshots
        path1 = self.snapshot_dir / file1 if '/' not in file1 else Path(file1)
        path2 = self.snapshot_dir / file2 if '/' not in file2 else Path(file2)
        
        if not path1.exists() or not path2.exists():
            console.print("[red]One or both snapshot files not found[/red]")
            return
        
        with open(path1) as f:
            data1 = json.load(f)
        with open(path2) as f:
            data2 = json.load(f)
        
        console.print(Panel(
            f"[bold]Snapshot Comparison[/bold]\n\n"
            f"Before: {path1.name}\n"
            f"After: {path2.name}",
            border_style="cyan"
        ))
        
        # Compare states
        state1 = data1.get('state', {})
        state2 = data2.get('state', {})
        
        # Find differences
        all_keys = set(state1.keys()) | set(state2.keys())
        differences = []
        
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 != val2:
                differences.append({
                    'key': key,
                    'before': str(val1)[:100],
                    'after': str(val2)[:100],
                })
        
        if differences:
            console.print("\n[bold]State Changes:[/bold]")
            for diff in differences[:10]:  # Show first 10
                console.print(f"\n[yellow]{diff['key']}[/yellow]:")
                console.print(f"  Before: {diff['before']}")
                console.print(f"  After:  {diff['after']}")
            
            if len(differences) > 10:
                console.print(f"\n[dim]... and {len(differences) - 10} more changes[/dim]")
        else:
            console.print("\n[green]No state changes detected[/green]")
    
    def get_langsmith_url(self) -> Optional[str]:
        """
        Get LangSmith URL for recent traces.
        
        Returns:
            URL to LangSmith project or None
        """
        import os
        project = os.environ.get('LANGCHAIN_PROJECT', 'deepagents-dev')
        
        if os.environ.get('LANGCHAIN_TRACING_V2') == 'true':
            return f"https://smith.langchain.com/o/default/projects/p/{project}"
        
        return None


def show_recent(limit: int = 10) -> None:
    """Quick function to show recent executions."""
    inspector = ExecutionInspector()
    inspector.show_recent_executions(limit)


def inspect(snapshot_file: str) -> None:
    """Quick function to inspect a snapshot."""
    inspector = ExecutionInspector()
    inspector.inspect_snapshot(snapshot_file)


def show_error() -> None:
    """Quick function to show last error."""
    inspector = ExecutionInspector()
    inspector.show_last_error()


def compare(file1: str, file2: str) -> None:
    """Quick function to compare snapshots."""
    inspector = ExecutionInspector()
    inspector.compare_snapshots(file1, file2)
