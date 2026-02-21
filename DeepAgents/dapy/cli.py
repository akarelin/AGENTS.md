"""
DeepAgents CLI - Main entry point

Zero-configuration CLI for personal knowledge management using LangChain/LangGraph 1.0
"""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import os
from typing import Optional

from deepagents.orchestrator import create_main_agent
from deepagents.config import load_config, DEFAULT_CONFIG
from deepagents.observability import setup_tracing
from deepagents.persistence import get_checkpointer

console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode with verbose output')
@click.option('--trace/--no-trace', default=True, help='Enable/disable LangSmith tracing')
@click.option('--config', type=click.Path(exists=True), help='Path to config YAML file')
@click.option(
    '--breakpoint',
    '-b',
    multiple=True,
    help='Set breakpoint on tool (can be specified multiple times)',
)
@click.pass_context
def cli(
    ctx: click.Context,
    debug: bool,
    trace: bool,
    config: Optional[str],
    breakpoint: tuple[str, ...],
) -> None:
    """
    DeepAgents CLI - Production-ready personal knowledge management system.

    Built with LangChain 1.0 and LangGraph 1.0, featuring observability,
    human-in-the-loop controls, and durable state persistence.

    Examples:
        deepagents ask "What's next?"
        deepagents close
        deepagents document
        deepagents push "Implemented new feature"
        deepagents ask "Archive outdated code" --breakpoint archive_tool
    """
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj['config'] = load_config(config)
    else:
        ctx.obj['config'] = DEFAULT_CONFIG.copy()

    # Apply CLI overrides
    ctx.obj['config']['debug'] = debug
    ctx.obj['config']['trace'] = trace
    ctx.obj['config']['breakpoints'] = list(breakpoint)

    # Setup tracing
    setup_tracing(enabled=trace)

    # Initialize checkpointer
    ctx.obj['checkpointer'] = get_checkpointer(ctx.obj['config'])

    if debug:
        console.print("[yellow]Debug mode enabled[/yellow]")
        console.print(f"[dim]Config: {ctx.obj['config']}[/dim]")


@cli.command()
@click.argument('query', nargs=-1, required=True)
@click.option('--snapshot/--no-snapshot', default=True, help='Enable state snapshots')
@click.option('--approve-all', is_flag=True, help='Auto-approve all tool calls')
@click.pass_context
def ask(ctx: click.Context, query: tuple[str, ...], snapshot: bool, approve_all: bool) -> None:
    """
    Execute a query using the main agent.

    QUERY: The question or command to execute (can be multiple words)

    Examples:
        deepagents ask What is the current status?
        deepagents ask "Archive outdated code"
        deepagents ask Update the changelog --no-snapshot
    """
    query_str = ' '.join(query)

    config = ctx.obj['config'].copy()
    config['snapshot_enabled'] = snapshot
    config['auto_approve'] = approve_all

    console.print(Panel(f"[bold cyan]Query:[/bold cyan] {query_str}", expand=False))

    try:
        agent = create_main_agent(config, ctx.obj['checkpointer'])

        with console.status("[bold green]Thinking..."):
            result = agent.invoke({"messages": [{"role": "user", "content": query_str}]})

        # Display result
        if isinstance(result, dict) and 'messages' in result:
            last_message = result['messages'][-1]
            content = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            content = str(result)

        console.print(Panel(Markdown(content), title="[bold green]Result", expand=False))

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if config['debug']:
            raise


@cli.command()
@click.pass_context
def next(ctx: click.Context) -> None:
    """
    Show what's next based on 2Do.md, ROADMAP.md, and git status.

    This command reads your current priorities and work in progress,
    then presents a concise summary of what to work on next.
    """
    from deepagents.workflows.whats_next import run_whats_next_workflow

    console.print("[bold cyan]Checking what's next...[/bold cyan]")

    try:
        result = run_whats_next_workflow(ctx.obj['config'])
        console.print(Panel(Markdown(result['summary']), title="[bold green]What's Next", expand=False))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj['config']['debug']:
            raise


@cli.command()
@click.pass_context
def close(ctx: click.Context) -> None:
    """
    Close the current session and prepare for next.

    This command:
    - Updates 2Do.md with current progress
    - Documents any mistakes in AGENTS_mistakes.md
    - Archives completed work
    - Provides a summary for the next session
    """
    from deepagents.workflows.close_session import run_close_session_workflow

    console.print("[bold cyan]Closing session...[/bold cyan]")

    try:
        with console.status("[bold green]Processing..."):
            result = run_close_session_workflow(ctx.obj['config'], ctx.obj['checkpointer'])

        console.print(Panel(Markdown(result['summary']), title="[bold green]Session Closed", expand=False))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj['config']['debug']:
            raise


@cli.command()
@click.pass_context
def document(ctx: click.Context) -> None:
    """
    Detect and document changes using git diff.

    This command:
    - Runs git diff to detect all changes
    - Identifies changes made by humans or other agents
    - Updates CHANGELOG.md with discovered changes
    - Updates relevant documentation as needed
    """
    from deepagents.workflows.document_changes import run_document_changes_workflow

    console.print("[bold cyan]Documenting changes...[/bold cyan]")

    try:
        with console.status("[bold green]Analyzing changes..."):
            result = run_document_changes_workflow(ctx.obj['config'])

        console.print(Panel(Markdown(result['summary']), title="[bold green]Changes Documented", expand=False))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj['config']['debug']:
            raise


@cli.command()
@click.argument('message', required=False)
@click.option('--pr', is_flag=True, help='Create a pull request after push')
@click.pass_context
def push(ctx: click.Context, message: Optional[str], pr: bool) -> None:
    """
    Commit and push changes with changelog verification.

    MESSAGE: Commit message (optional, will be generated if not provided)

    This command:
    - Ensures CHANGELOG.md is updated
    - Commits all changes with appropriate message
    - Pushes to repository
    - Creates PR if requested
    """
    from deepagents.tools.git_operations import git_push_tool

    console.print("[bold cyan]Preparing to push...[/bold cyan]")

    try:
        result = git_push_tool(message=message or "", create_pr=pr)

        if result['success']:
            console.print(f"[bold green]✓[/bold green] Pushed: {result['commit_hash']}")
            if result.get('pr_url'):
                console.print(f"[bold blue]PR created:[/bold blue] {result['pr_url']}")
        else:
            console.print(f"[bold red]✗[/bold red] Push failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if ctx.obj['config']['debug']:
            raise


@cli.command()
@click.option('--port', default=8000, help='Port to run daemon on')
@click.option('--reload', is_flag=True, help='Enable hot reload for development')
@click.pass_context
def daemon(ctx: click.Context, port: int, reload: bool) -> None:
    """
    Run DeepAgents as a background daemon with API interface.

    This is used for deployment scenarios where DeepAgents runs
    as a service accepting requests via HTTP API.
    """
    console.print(f"[bold cyan]Starting DeepAgents daemon on port {port}...[/bold cyan]")

    # This would integrate with FastAPI or similar for HTTP interface
    # For now, placeholder
    console.print("[yellow]Daemon mode not yet implemented[/yellow]")


@cli.command()
@click.option('--limit', '-n', default=10, help='Number of recent executions to show')
@click.pass_context
def inspect(ctx: click.Context, limit: int) -> None:
    """
    Inspect recent executions and snapshots.
    
    Shows recent execution history with snapshots for debugging.
    Useful for reviewing what happened before an error.
    
    Examples:
        deepagents inspect
        deepagents inspect --limit 20
    """
    from deepagents.inspect import ExecutionInspector
    
    inspector = ExecutionInspector()
    inspector.show_recent_executions(limit)
    
    # Show LangSmith link if available
    langsmith_url = inspector.get_langsmith_url()
    if langsmith_url:
        console.print(f"\n[bold]LangSmith Traces:[/bold] {langsmith_url}")


@cli.group()
@click.pass_context
def feedback(ctx: click.Context) -> None:
    """
    Submit and manage feedback.
    
    Report issues, request features, or provide suggestions.
    Feedback is tracked in LangSmith for Manus to review.
    """
    pass


@feedback.command('submit')
@click.argument('description', required=False)
@click.option('--category', type=click.Choice(['bug', 'feature', 'improvement', 'question']), help='Feedback category')
@click.option('--severity', type=click.Choice(['low', 'medium', 'high', 'critical']), help='Issue severity')
@click.pass_context
def feedback_submit(ctx: click.Context, description: Optional[str], category: Optional[str], severity: Optional[str]) -> None:
    """
    Submit feedback about DeepAgents.
    
    If DESCRIPTION is not provided, enters interactive mode.
    
    Examples:
        deepagents feedback submit
        deepagents feedback submit "Tool X failed with error Y" --category bug --severity high
    """
    from deepagents.feedback import FeedbackManager, submit_feedback_interactive
    
    if description:
        # Non-interactive mode
        manager = FeedbackManager()
        feedback_key = manager.submit_feedback(
            description=description,
            category=category,
            severity=severity
        )
        console.print(f"[bold green]✓[/bold green] Feedback submitted: {feedback_key}")
        console.print(f"[dim]Track status with: deepagents feedback status {feedback_key}[/dim]")
    else:
        # Interactive mode
        submit_feedback_interactive()


@feedback.command('list')
@click.option('--limit', '-n', default=10, help='Number of feedback items to show')
@click.pass_context
def feedback_list(ctx: click.Context, limit: int) -> None:
    """
    List your submitted feedback.
    
    Examples:
        deepagents feedback list
        deepagents feedback list --limit 20
    """
    from deepagents.feedback import show_feedback_list
    show_feedback_list(limit)


@feedback.command('status')
@click.argument('feedback_key')
@click.pass_context
def feedback_status(ctx: click.Context, feedback_key: str) -> None:
    """
    Show status of specific feedback.
    
    FEEDBACK_KEY: The feedback identifier
    
    Examples:
        deepagents feedback status feedback_20251126_143022
    """
    from deepagents.feedback import show_feedback_status
    show_feedback_status(feedback_key)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    from importlib.metadata import version as get_version

    try:
        ver = get_version('deepagents-cli')
    except Exception:
        ver = "unknown (development)"

    console.print(f"[bold]DeepAgents CLI[/bold] version {ver}")
    console.print("Built with LangChain 1.0 and LangGraph 1.0")


@cli.command()
@click.argument('description', required=False)
@click.option('--output', '-o', help='Output path for debug package')
@click.option('--snapshots', default=20, help='Number of snapshots to include')
@click.pass_context
def export_debug(ctx: click.Context, description: Optional[str], output: Optional[str], snapshots: int) -> None:
    """
    Export debug package for troubleshooting.
    
    Creates a comprehensive package with snapshots, logs, and environment info
    that can be shared with Manus for remote inspection.
    
    DESCRIPTION: Optional description of the issue
    
    Examples:
        deepagents export-debug "Tool X failed with error Y"
        deepagents export-debug --output my-debug.tar.gz
    """
    from deepagents.debug_export import create_debug_package
    
    console.print("[bold cyan]Creating debug package...[/bold cyan]")
    
    try:
        package_path = create_debug_package(
            description=description,
            output_path=output
        )
        
        console.print(f"\n[bold green]✓[/bold green] Debug package created: {package_path}")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Share this package with Manus for inspection")
        console.print("  2. Or extract and review locally:")
        console.print(f"     tar -xzf {Path(package_path).name}")
        console.print("\n[dim]Package contains: snapshots, logs, environment info, execution summary[/dim]")
    
    except Exception as e:
        console.print(f"[bold red]Error creating debug package:[/bold red] {e}")
        if ctx.obj['config']['debug']:
            raise


@cli.command()
@click.pass_context
def diag(ctx: click.Context) -> None:
    """
    Show diagnostic information for troubleshooting.

    Displays configuration, environment variables, and system status.
    """
    console.print("[bold cyan]DeepAgents Diagnostic Information[/bold cyan]\n")

    # Configuration
    console.print("[bold]Configuration:[/bold]")
    for key, value in ctx.obj['config'].items():
        console.print(f"  {key}: {value}")

    # Environment
    console.print("\n[bold]Environment:[/bold]")
    env_vars = ['LANGCHAIN_TRACING_V2', 'LANGCHAIN_PROJECT', 'OPENAI_API_KEY']
    for var in env_vars:
        value = os.environ.get(var, '[not set]')
        if 'KEY' in var and value != '[not set]':
            value = value[:8] + '...' + value[-4:]  # Mask API keys
        console.print(f"  {var}: {value}")

    # Checkpointer
    console.print(f"\n[bold]Checkpointer:[/bold] {type(ctx.obj['checkpointer']).__name__}")

    # Git status
    console.print("\n[bold]Git Status:[/bold]")
    try:
        import git
        repo = git.Repo(search_parent_directories=True)
        console.print(f"  Branch: {repo.active_branch.name}")
        console.print(f"  Dirty: {repo.is_dirty()}")
        console.print(f"  Untracked files: {len(repo.untracked_files)}")
    except Exception as e:
        console.print(f"  [yellow]Not in a git repository: {e}[/yellow]")


if __name__ == '__main__':
    cli()
