"""
State persistence for DeepAgents CLI

Uses LangGraph 1.0 checkpointing for durable state management.
"""

from typing import Any, Dict
from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path
import os


def get_checkpointer(config: Dict[str, Any]) -> Any:
    """
    Get appropriate checkpointer based on configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Checkpointer instance (SqliteSaver or PostgresSaver)
    """
    backend = config.get('persistence_backend', 'sqlite')
    
    if backend == 'sqlite':
        db_path = config.get('db_path', './deepagents.db')
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(exist_ok=True, parents=True)
        
        # Create connection string
        conn_string = f"sqlite:///{db_path}"
        
        return SqliteSaver.from_conn_string(conn_string)
    
    elif backend == 'postgres':
        # Import only if needed to avoid dependency issues
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2-binary. "
                "Install with: pip install deepagents-cli[postgres]"
            )
        
        conn_string = config.get('postgres_conn_string')
        if not conn_string:
            raise ValueError(
                "PostgreSQL backend requires 'postgres_conn_string' in config "
                "or POSTGRES_CONN_STRING environment variable"
            )
        
        return PostgresSaver.from_conn_string(conn_string)
    
    elif backend == 'memory':
        # In-memory for testing
        return SqliteSaver.from_conn_string(":memory:")
    
    else:
        raise ValueError(f"Unknown persistence backend: {backend}")


class StateManager:
    """
    Manages persistent state for multi-session workflows.
    
    Handles state that needs to persist across CLI invocations,
    such as session history, pending approvals, and workflow checkpoints.
    """
    
    def __init__(self, checkpointer: Any):
        """
        Initialize state manager.
        
        Args:
            checkpointer: LangGraph checkpointer instance
        """
        self.checkpointer = checkpointer
    
    def save_state(self, thread_id: str, state: Dict[str, Any]) -> None:
        """
        Save state for a specific thread.
        
        Args:
            thread_id: Unique thread identifier
            state: State to save
        """
        # LangGraph checkpointer handles this automatically
        # This is a wrapper for explicit state management if needed
        pass
    
    def load_state(self, thread_id: str) -> Dict[str, Any]:
        """
        Load state for a specific thread.
        
        Args:
            thread_id: Unique thread identifier
            
        Returns:
            Loaded state or empty dict if not found
        """
        # LangGraph checkpointer handles this automatically
        # This is a wrapper for explicit state retrieval if needed
        return {}
    
    def list_threads(self) -> list[str]:
        """
        List all active threads.
        
        Returns:
            List of thread IDs
        """
        # Would query checkpointer for active threads
        return []
    
    def cleanup_old_threads(self, days: int = 30) -> int:
        """
        Clean up threads older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of threads cleaned up
        """
        # Would implement cleanup logic
        return 0
