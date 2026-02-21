"""
Observability and tracing for DeepAgents CLI

Integrates with LangSmith for full agent execution visibility.
"""

import os
from typing import Any, Dict, Optional
from langsmith import Client
from langsmith.run_helpers import traceable
from datetime import datetime
import json
from pathlib import Path


def setup_tracing(enabled: bool = True, project: str = "deepagents-cli") -> None:
    """
    Configure LangSmith tracing.
    
    Args:
        enabled: Whether to enable tracing
        project: LangSmith project name
    """
    if enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = project
        
        # Verify API key is set
        if not os.environ.get("LANGCHAIN_API_KEY"):
            print("Warning: LANGCHAIN_API_KEY not set. Tracing will not work.")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


def get_langsmith_client() -> Optional[Client]:
    """
    Get LangSmith client if tracing is enabled.
    
    Returns:
        LangSmith client or None if tracing disabled
    """
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        try:
            return Client()
        except Exception as e:
            print(f"Warning: Could not initialize LangSmith client: {e}")
            return None
    return None


@traceable(name="DeepAgents Session")
def trace_session(
    session_type: str,
    query: str,
    config: Dict[str, Any],
    result: Any
) -> Dict[str, Any]:
    """
    Trace a complete DeepAgents session.
    
    Args:
        session_type: Type of session (ask, close, document, etc.)
        query: User query or command
        config: Configuration used
        result: Session result
        
    Returns:
        Traced result with metadata
    """
    return {
        'session_type': session_type,
        'query': query,
        'timestamp': datetime.now().isoformat(),
        'config': {k: v for k, v in config.items() if k not in ['api_keys']},
        'result': result,
    }


@traceable(name="Tool Execution")
def trace_tool_call(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any
) -> Dict[str, Any]:
    """
    Trace individual tool execution.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to tool
        tool_result: Result from tool execution
        
    Returns:
        Traced tool call with metadata
    """
    return {
        'tool': tool_name,
        'args': tool_args,
        'timestamp': datetime.now().isoformat(),
        'result': tool_result,
    }


class SnapshotManager:
    """
    Manages state snapshots for debugging and analysis.
    """
    
    def __init__(self, snapshot_dir: str = './snapshots'):
        """
        Initialize snapshot manager.
        
        Args:
            snapshot_dir: Directory to store snapshots
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(exist_ok=True, parents=True)
    
    def capture_snapshot(
        self,
        snapshot_type: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Capture a state snapshot.
        
        Args:
            snapshot_type: Type of snapshot (tool_call, workflow_step, etc.)
            state: Current state to snapshot
            metadata: Additional metadata
            
        Returns:
            Path to snapshot file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"snapshot_{snapshot_type}_{timestamp}.json"
        filepath = self.snapshot_dir / filename
        
        snapshot_data = {
            'type': snapshot_type,
            'timestamp': datetime.now().isoformat(),
            'state': state,
            'metadata': metadata or {},
        }
        
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f, indent=2, default=str)
        
        return str(filepath)
    
    def load_snapshot(self, snapshot_path: str) -> Dict[str, Any]:
        """
        Load a snapshot from file.
        
        Args:
            snapshot_path: Path to snapshot file
            
        Returns:
            Snapshot data
        """
        with open(snapshot_path, 'r') as f:
            return json.load(f)
    
    def list_snapshots(self, snapshot_type: Optional[str] = None) -> list[str]:
        """
        List all snapshots, optionally filtered by type.
        
        Args:
            snapshot_type: Optional type filter
            
        Returns:
            List of snapshot file paths
        """
        pattern = f"snapshot_{snapshot_type}_*.json" if snapshot_type else "snapshot_*.json"
        return [str(p) for p in sorted(self.snapshot_dir.glob(pattern))]


class MetricsCollector:
    """
    Collects metrics about agent execution for analysis.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {
            'tool_calls': {},
            'errors': [],
            'execution_times': {},
            'tokens_used': 0,
        }
    
    def record_tool_call(self, tool_name: str, duration: float, success: bool) -> None:
        """
        Record a tool call execution.
        
        Args:
            tool_name: Name of the tool
            duration: Execution duration in seconds
            success: Whether the call succeeded
        """
        if tool_name not in self.metrics['tool_calls']:
            self.metrics['tool_calls'][tool_name] = {
                'count': 0,
                'successes': 0,
                'failures': 0,
                'total_duration': 0.0,
            }
        
        self.metrics['tool_calls'][tool_name]['count'] += 1
        self.metrics['tool_calls'][tool_name]['total_duration'] += duration
        
        if success:
            self.metrics['tool_calls'][tool_name]['successes'] += 1
        else:
            self.metrics['tool_calls'][tool_name]['failures'] += 1
    
    def record_error(self, error_type: str, error_message: str, context: Dict[str, Any]) -> None:
        """
        Record an error occurrence.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Error context
        """
        self.metrics['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context,
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Summary of collected metrics
        """
        return {
            'total_tool_calls': sum(m['count'] for m in self.metrics['tool_calls'].values()),
            'total_errors': len(self.metrics['errors']),
            'tool_breakdown': self.metrics['tool_calls'],
            'recent_errors': self.metrics['errors'][-5:],  # Last 5 errors
        }
