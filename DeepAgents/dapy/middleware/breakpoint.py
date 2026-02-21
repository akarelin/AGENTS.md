"""
Breakpoint middleware for interactive debugging
"""

from typing import Any, Dict, Set
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

console = Console()


class BreakpointMiddleware:
    """
    Middleware that pauses execution at specified breakpoints.
    
    Allows inspection of state, modification of arguments, or
    aborting execution at critical points.
    """
    
    def __init__(self, breakpoints: list[str] = None):
        """
        Initialize breakpoint middleware.
        
        Args:
            breakpoints: List of tool names to break on
        """
        self.breakpoints: Set[str] = set(breakpoints or [])
    
    def add_breakpoint(self, tool_name: str) -> None:
        """
        Add a breakpoint for a tool.
        
        Args:
            tool_name: Name of tool to break on
        """
        self.breakpoints.add(tool_name)
    
    def remove_breakpoint(self, tool_name: str) -> None:
        """
        Remove a breakpoint.
        
        Args:
            tool_name: Name of tool to remove breakpoint from
        """
        self.breakpoints.discard(tool_name)
    
    async def before_tool_call(self, tool_call: Any, state: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
        """
        Check if breakpoint should trigger before tool execution.
        
        Args:
            tool_call: Tool call object
            state: Current agent state
            
        Returns:
            Potentially modified tool_call and state
        """
        tool_name = tool_call.name if hasattr(tool_call, 'name') else str(tool_call)
        
        if tool_name in self.breakpoints:
            console.print("\n")
            console.print(Panel(
                f"[bold red]🔴 BREAKPOINT[/bold red]\n\n"
                f"Tool: [cyan]{tool_name}[/cyan]",
                title="Execution Paused",
                border_style="red"
            ))
            
            # Display arguments
            if hasattr(tool_call, 'args'):
                args_json = json.dumps(tool_call.args, indent=2)
                console.print("\n[bold]Arguments:[/bold]")
                console.print(Syntax(args_json, "json", theme="monokai"))
            
            # Display relevant state
            console.print("\n[bold]Current State (summary):[/bold]")
            state_summary = {
                k: str(v)[:100] + '...' if len(str(v)) > 100 else v
                for k, v in state.items()
                if not k.startswith('_')
            }
            state_json = json.dumps(state_summary, indent=2, default=str)
            console.print(Syntax(state_json, "json", theme="monokai"))
            
            # Interactive prompt
            console.print("\n[bold]Options:[/bold]")
            console.print("  [green]c[/green] - Continue execution")
            console.print("  [yellow]s[/yellow] - Skip this tool call")
            console.print("  [red]a[/red] - Abort execution")
            console.print("  [blue]i[/blue] - Inspect with debugger (pdb)")
            console.print("  [magenta]m[/magenta] - Modify arguments")
            
            while True:
                response = console.input("\n[bold]Action:[/bold] ").strip().lower()
                
                if response == 'c':
                    console.print("[green]Continuing...[/green]")
                    break
                
                elif response == 's':
                    console.print("[yellow]Skipping tool call[/yellow]")
                    # Return a no-op result
                    raise SkipToolCallException(f"Skipped {tool_name} at breakpoint")
                
                elif response == 'a':
                    console.print("[red]Aborting execution[/red]")
                    raise InterruptedError(f"User aborted at breakpoint: {tool_name}")
                
                elif response == 'i':
                    console.print("[blue]Entering debugger...[/blue]")
                    import pdb
                    pdb.set_trace()
                    break
                
                elif response == 'm':
                    console.print("[magenta]Argument modification not yet implemented[/magenta]")
                    # Future: allow interactive argument editing
                
                else:
                    console.print("[red]Invalid option. Please choose c/s/a/i/m[/red]")
        
        return tool_call, state


class SkipToolCallException(Exception):
    """Exception raised when user chooses to skip a tool call at breakpoint."""
    pass
