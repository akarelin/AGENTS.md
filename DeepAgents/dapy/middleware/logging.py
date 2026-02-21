"""
Enhanced logging middleware for detailed execution tracking
"""

from typing import Any, Dict
from rich.console import Console
from rich.table import Table
from datetime import datetime
import time

console = Console()


class EnhancedLoggingMiddleware:
    """
    Middleware that provides detailed logging of agent execution.
    
    Logs tool calls, model invocations, and state transitions
    with timing information.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize logging middleware.
        
        Args:
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self.call_stack: list[Dict[str, Any]] = []
        self.start_time = time.time()
    
    async def before_tool_call(self, tool_call: Any, state: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
        """
        Log before tool execution.
        
        Args:
            tool_call: Tool call object
            state: Current agent state
            
        Returns:
            Unmodified tool_call and state
        """
        tool_name = tool_call.name if hasattr(tool_call, 'name') else str(tool_call)
        
        call_info = {
            'type': 'tool_call',
            'name': tool_name,
            'start_time': time.time(),
            'timestamp': datetime.now().isoformat(),
        }
        self.call_stack.append(call_info)
        
        if self.verbose:
            console.print(f"[dim]→ Calling tool:[/dim] [cyan]{tool_name}[/cyan]")
            if hasattr(tool_call, 'args'):
                console.print(f"[dim]  Args: {tool_call.args}[/dim]")
        
        return tool_call, state
    
    async def after_tool_call(
        self,
        tool_call: Any,
        tool_result: Any,
        state: Dict[str, Any]
    ) -> tuple[Any, Dict[str, Any]]:
        """
        Log after tool execution.
        
        Args:
            tool_call: Tool call object
            tool_result: Result from tool execution
            state: Updated agent state
            
        Returns:
            Unmodified tool_result and state
        """
        if self.call_stack:
            call_info = self.call_stack[-1]
            duration = time.time() - call_info['start_time']
            call_info['duration'] = duration
            call_info['end_time'] = time.time()
            
            if self.verbose:
                tool_name = call_info['name']
                console.print(
                    f"[dim]← Completed:[/dim] [cyan]{tool_name}[/cyan] "
                    f"[dim]({duration:.2f}s)[/dim]"
                )
                
                # Show result summary
                result_str = str(tool_result)
                if len(result_str) > 100:
                    result_str = result_str[:100] + '...'
                console.print(f"[dim]  Result: {result_str}[/dim]")
        
        return tool_result, state
    
    async def before_model_call(self, messages: list[Any], state: Dict[str, Any]) -> tuple[list[Any], Dict[str, Any]]:
        """
        Log before model invocation.
        
        Args:
            messages: Messages to send to model
            state: Current agent state
            
        Returns:
            Unmodified messages and state
        """
        call_info = {
            'type': 'model_call',
            'message_count': len(messages),
            'start_time': time.time(),
            'timestamp': datetime.now().isoformat(),
        }
        self.call_stack.append(call_info)
        
        if self.verbose:
            console.print(f"[dim]→ Calling model with {len(messages)} messages[/dim]")
        
        return messages, state
    
    async def after_model_call(
        self,
        messages: list[Any],
        response: Any,
        state: Dict[str, Any]
    ) -> tuple[Any, Dict[str, Any]]:
        """
        Log after model invocation.
        
        Args:
            messages: Messages sent to model
            response: Model response
            state: Updated agent state
            
        Returns:
            Unmodified response and state
        """
        if self.call_stack:
            call_info = self.call_stack[-1]
            duration = time.time() - call_info['start_time']
            call_info['duration'] = duration
            call_info['end_time'] = time.time()
            
            if self.verbose:
                console.print(f"[dim]← Model responded ({duration:.2f}s)[/dim]")
        
        return response, state
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get summary of execution.
        
        Returns:
            Summary with timing and call statistics
        """
        total_duration = time.time() - self.start_time
        
        tool_calls = [c for c in self.call_stack if c['type'] == 'tool_call']
        model_calls = [c for c in self.call_stack if c['type'] == 'model_call']
        
        return {
            'total_duration': total_duration,
            'total_tool_calls': len(tool_calls),
            'total_model_calls': len(model_calls),
            'tool_breakdown': {
                call['name']: call.get('duration', 0)
                for call in tool_calls
            },
        }
    
    def print_execution_summary(self) -> None:
        """Print formatted execution summary."""
        summary = self.get_execution_summary()
        
        table = Table(title="Execution Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Duration", f"{summary['total_duration']:.2f}s")
        table.add_row("Tool Calls", str(summary['total_tool_calls']))
        table.add_row("Model Calls", str(summary['total_model_calls']))
        
        console.print(table)
        
        if summary['tool_breakdown']:
            tool_table = Table(title="Tool Call Breakdown")
            tool_table.add_column("Tool", style="cyan")
            tool_table.add_column("Duration", style="green")
            
            for tool, duration in summary['tool_breakdown'].items():
                tool_table.add_row(tool, f"{duration:.2f}s")
            
            console.print(tool_table)
