"""
Snapshot middleware for state capture at key execution points
"""

from typing import Any, Dict
from deepagents.observability import SnapshotManager


class SnapshotMiddleware:
    """
    Middleware that captures state snapshots before/after tool calls.
    
    Enables debugging and analysis by preserving full context at each step.
    """
    
    def __init__(self, snapshot_dir: str = './snapshots', enabled: bool = True):
        """
        Initialize snapshot middleware.
        
        Args:
            snapshot_dir: Directory to store snapshots
            enabled: Whether snapshots are enabled
        """
        self.enabled = enabled
        self.manager = SnapshotManager(snapshot_dir) if enabled else None
    
    async def before_tool_call(self, tool_call: Any, state: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
        """
        Capture snapshot before tool execution.
        
        Args:
            tool_call: Tool call object
            state: Current agent state
            
        Returns:
            Unmodified tool_call and state
        """
        if self.enabled and self.manager:
            metadata = {
                'phase': 'before_tool_call',
                'tool': tool_call.name if hasattr(tool_call, 'name') else str(tool_call),
                'args': tool_call.args if hasattr(tool_call, 'args') else {},
            }
            self.manager.capture_snapshot('tool_call', state, metadata)
        
        return tool_call, state
    
    async def after_tool_call(
        self,
        tool_call: Any,
        tool_result: Any,
        state: Dict[str, Any]
    ) -> tuple[Any, Dict[str, Any]]:
        """
        Capture snapshot after tool execution.
        
        Args:
            tool_call: Tool call object
            tool_result: Result from tool execution
            state: Updated agent state
            
        Returns:
            Unmodified tool_result and state
        """
        if self.enabled and self.manager:
            metadata = {
                'phase': 'after_tool_call',
                'tool': tool_call.name if hasattr(tool_call, 'name') else str(tool_call),
                'result': str(tool_result)[:500],  # Truncate long results
            }
            self.manager.capture_snapshot('tool_result', state, metadata)
        
        return tool_result, state
    
    async def before_model_call(self, messages: list[Any], state: Dict[str, Any]) -> tuple[list[Any], Dict[str, Any]]:
        """
        Capture snapshot before model invocation.
        
        Args:
            messages: Messages to send to model
            state: Current agent state
            
        Returns:
            Unmodified messages and state
        """
        if self.enabled and self.manager:
            metadata = {
                'phase': 'before_model_call',
                'message_count': len(messages),
            }
            self.manager.capture_snapshot('model_call', state, metadata)
        
        return messages, state
