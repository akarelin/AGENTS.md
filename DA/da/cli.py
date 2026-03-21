"""DeepAgents CLI — main entry point.

Commands derived from your Claude Code slash command usage:
  /resume (136 uses) -> da resume
  /model (243 uses)  -> da --model
  /add-dir (139)     -> da --project
  Session commands    -> da ask, da next, da close, da document, da push
"""

import os
import uuid
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Auto-load .env from project root
_env_paths = [
    Path(__file__).parent.parent / ".env",
    Path.home() / ".da" / ".env",
    Path.cwd() / ".env",
]
for _ep in _env_paths:
    if _ep.exists():
        load_dotenv(_ep)
        break

from da.config import load_config
from da.client import get_client, run_agent_loop
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore

console = Console()


def _make_api_tools() -> list[dict]:
    """Convert tool defs to Anthropic API format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in ALL_TOOL_DEFS
    ]


def _tool_executor(name: str, inputs: dict) -> str:
    """Execute a tool call with optional approval gate."""
    return execute_tool(name, inputs)


@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--model", "-m", help="Model override (e.g. claude-opus-4-6)")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx: click.Context, debug: bool, model: Optional[str], config: Optional[str]) -> None:
    """DA — DebilAgent. Personal multi-agent system."""
    ctx.ensure_object(dict)
    cfg = load_config(config)
    if debug:
        cfg.debug = debug
    if model:
        cfg.model = model
    ctx.obj["config"] = cfg
    ctx.obj["session_store"] = SessionStore(cfg.session.db_path)

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.command()
@click.argument("query", nargs=-1, required=True)
@click.option("--session", "-s", help="Resume a session by ID")
@click.pass_context
def ask(ctx: click.Context, query: tuple[str, ...], session: Optional[str]) -> None:
    """Ask the orchestrator agent a question or give it a task."""
    cfg = ctx.obj["config"]
    store = ctx.obj["session_store"]
    query_str = " ".join(query)

    # Session management
    session_id = session or str(uuid.uuid4())
    if not session:
        store.create_session(session_id, name=query_str[:60], project=os.getcwd())

    console.print(Panel(f"[bold cyan]{query_str}[/bold cyan]", title="Query", expand=False))

    try:
        client = get_client(cfg)
        system = get_system_prompt(cfg)
        tools = _make_api_tools()

        # Load prior messages if resuming
        messages_context = ""
        if session:
            prior = store.get_messages(session_id, limit=20)
            if prior:
                messages_context = f"\n\n[Prior conversation context: {len(prior)} messages]"
                # Summarize prior context in system prompt
                system += messages_context

        with console.status("[bold green]Thinking..."):
            result = run_agent_loop(
                client=client,
                config=cfg,
                system=system,
                user_message=query_str,
                tools=tools,
                tool_executor=_tool_executor,
            )

        # Save to session
        store.add_message(session_id, "user", query_str)
        store.add_message(session_id, "assistant", result)

        console.print(Panel(Markdown(result), title="[bold green]Result", expand=False))
        if cfg.debug:
            console.print(f"[dim]Session: {session_id}[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if cfg.debug:
            raise


@cli.command("next")
@click.pass_context
def whats_next(ctx: click.Context) -> None:
    """Show what to work on next (reads 2Do.md, ROADMAP.md, git status)."""
    ctx.invoke(ask, query=("What's next? Read 2Do.md, ROADMAP.md, and check git status. Give me a concise summary.",))


@cli.command()
@click.pass_context
def close(ctx: click.Context) -> None:
    """Close session — update 2Do.md with progress, archive work."""
    ctx.invoke(
        ask,
        query=("Close session: Update 2Do.md with current progress and next steps. "
               "Document any completed work. Provide a summary for the next session.",),
    )


@cli.command()
@click.pass_context
def document(ctx: click.Context) -> None:
    """Document changes — run git diff and update CHANGELOG.md."""
    ctx.invoke(
        ask,
        query=("Document changes: Run git diff to detect all changes. "
               "Update CHANGELOG.md with discovered changes.",),
    )


@cli.command()
@click.argument("message", required=False)
@click.pass_context
def push(ctx: click.Context, message: Optional[str]) -> None:
    """Commit and push changes with changelog check."""
    msg = message or "Update"
    ctx.invoke(
        ask,
        query=(f"Push: Ensure CHANGELOG.md is updated, then commit with message '{msg}' and push.",),
    )


@cli.command()
@click.option("--limit", "-n", default=20, help="Number of sessions to show")
@click.pass_context
def sessions(ctx: click.Context, limit: int) -> None:
    """List recent sessions."""
    store = ctx.obj["session_store"]
    recent = store.list_sessions(limit)

    if not recent:
        console.print("[dim]No sessions yet.[/dim]")
        return

    from rich.table import Table
    import datetime

    table = Table(title="Recent Sessions")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Name", max_width=50)
    table.add_column("Project", max_width=30)
    table.add_column("Updated", max_width=20)

    for s in recent:
        ts = datetime.datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M")
        table.add_row(s["id"][:12], s["name"], s["project"] or "", ts)

    console.print(table)


@cli.command()
@click.argument("session_id")
@click.pass_context
def resume(ctx: click.Context, session_id: str) -> None:
    """Resume a previous session interactively."""
    store = ctx.obj["session_store"]
    messages = store.get_messages(session_id, limit=10)

    if not messages:
        console.print(f"[yellow]No messages found for session {session_id}[/yellow]")
        return

    console.print(f"[bold]Resuming session {session_id[:12]}...[/bold]")
    for m in messages[-5:]:
        role = m["role"]
        content = m["content"][:200] if isinstance(m["content"], str) else str(m["content"])[:200]
        color = "cyan" if role == "user" else "green"
        console.print(f"[{color}]{role}:[/{color}] {content}")


@cli.command()
@click.pass_context
def diag(ctx: click.Context) -> None:
    """Show diagnostic information."""
    cfg = ctx.obj["config"]

    console.print("[bold cyan]DeepAgents Diagnostics[/bold cyan]\n")
    console.print(f"[bold]Model:[/bold] {cfg.model}")
    console.print(f"[bold]API Key:[/bold] {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET'}")
    console.print(f"[bold]Debug:[/bold] {cfg.debug}")

    console.print(f"\n[bold]Hosts:[/bold]")
    for name, h in cfg.hosts.items():
        console.print(f"  {name}: {h.ssh} [{', '.join(h.roles)}]")

    console.print(f"\n[bold]Projects:[/bold]")
    for name, path in cfg.projects.items():
        console.print(f"  {name}: {path}")

    console.print(f"\n[bold]Tools:[/bold] {len(ALL_TOOL_DEFS)} registered")
    for t in ALL_TOOL_DEFS:
        console.print(f"  {t['name']}: {t['description'][:60]}")


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version."""
    from da import __version__
    console.print(f"[bold]DA[/bold] v{__version__}")


@cli.command()
@click.option("--claude-dir", default=None, help="Path to .claude directory")
@click.pass_context
def analyze(ctx: click.Context, claude_dir: Optional[str]) -> None:
    """Analyze Claude Code history to extract usage patterns."""
    cfg = ctx.obj["config"]
    cdir = claude_dir or cfg.claude_history or "/mnt/d/SD/.claude"

    console.print(f"[bold cyan]Analyzing Claude Code history at {cdir}...[/bold cyan]")

    from da.history_analyzer import analyze_history, format_report

    with console.status("[bold green]Processing..."):
        results = analyze_history(cdir)

    report = format_report(results)
    console.print(Markdown(report))


@cli.command()
@click.option("--model", "-m", help="Model override")
@click.pass_context
def repl(ctx: click.Context, model: Optional[str]) -> None:
    """Interactive REPL — chat with DeepAgents."""
    cfg = ctx.obj["config"]
    if model:
        cfg.model = model
    store = ctx.obj["session_store"]
    session_id = str(uuid.uuid4())
    store.create_session(session_id, name="repl", project=os.getcwd())

    client = get_client(cfg)
    system = get_system_prompt(cfg)
    tools = _make_api_tools()
    messages: list[dict] = []

    from da import __version__

    BANNER = r"""
      ░████             ░██        ░██░██       ░███                                        ░██    
    ░██  ░██            ░██           ░██      ░██░██                                       ░██    
   ░██   ░██  ░███████  ░████████  ░██░██     ░██  ░██   ░████████  ░███████  ░████████  ░████████ 
  ░██    ░██ ░██    ░██ ░██    ░██ ░██░██    ░█████████ ░██    ░██ ░██    ░██ ░██    ░██    ░██    
  ░██    ░██ ░█████████ ░██    ░██ ░██░██    ░██    ░██ ░██    ░██ ░█████████ ░██    ░██    ░██    
  ░██    ░██ ░██        ░███   ░██ ░██░██    ░██    ░██ ░██   ░███ ░██        ░██    ░██    ░██    
  ░█████████  ░███████  ░██░█████  ░██░██    ░██    ░██  ░█████░██  ░███████  ░██    ░██     ░████ 
░██        ░██                                                 ░██                                 
Агент который только говорит ДА                          ░███████                                  
"""
    console.print(f"[bold cyan]{BANNER}[/bold cyan]", highlight=False)
    console.print(f"  v{__version__} | {cfg.model} | {len(tools)} hands | {len(cfg.hosts)} heads", style="dim")
    console.print("  type 'exit' or Ctrl+C to quit\n", style="dim")

    try:
        while True:
            try:
                user_input = console.input("[bold green]da>[/bold green] ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break

            # REPL slash commands
            if user_input.startswith("/"):
                parts = user_input.split(None, 1)
                cmd = parts[0].lower()

                if cmd == "/":
                    console.print("  [cyan]/model[/cyan]   — switch model (opus/sonnet/haiku)")
                    console.print("  [cyan]/tools[/cyan]   — list available tools")
                    console.print("  [cyan]/hosts[/cyan]   — list configured hosts")
                    console.print("  [cyan]/session[/cyan] — show current session ID")
                    console.print("  [cyan]/help[/cyan]    — detailed help")
                    console.print("  [cyan]exit[/cyan]     — quit")
                    continue

                elif cmd == "/model":
                    models = {
                        "opus": "claude-opus-4-6",
                        "sonnet": "claude-sonnet-4-6",
                        "haiku": "claude-haiku-4-5-20251001",
                    }
                    if len(parts) > 1 and parts[1].strip().lower() in models:
                        cfg.model = models[parts[1].strip().lower()]
                        console.print(f"[bold green]Model: {cfg.model}[/bold green]")
                    elif len(parts) > 1:
                        cfg.model = parts[1].strip()
                        console.print(f"[bold green]Model: {cfg.model}[/bold green]")
                    else:
                        console.print(f"[bold]Current:[/bold] {cfg.model}")
                        console.print("[dim]  /model opus   — claude-opus-4-6[/dim]")
                        console.print("[dim]  /model sonnet — claude-sonnet-4-6[/dim]")
                        console.print("[dim]  /model haiku  — claude-haiku-4-5[/dim]")
                    continue

                elif cmd == "/help":
                    console.print("[bold]REPL Commands:[/bold]")
                    console.print("  /model [name]  — switch model (opus/sonnet/haiku)")
                    console.print("  /tools         — list available tools")
                    console.print("  /hosts         — list configured hosts")
                    console.print("  /session       — show current session ID")
                    console.print("  /help          — this help")
                    console.print("  exit           — quit")
                    continue

                elif cmd == "/tools":
                    for t in ALL_TOOL_DEFS:
                        console.print(f"  [cyan]{t['name']}[/cyan] — {t['description'][:60]}")
                    continue

                elif cmd == "/hosts":
                    for name, h in cfg.hosts.items():
                        console.print(f"  [cyan]{name}[/cyan] — {h.ssh} [{', '.join(h.roles)}]")
                    continue

                elif cmd == "/session":
                    console.print(f"  [dim]{session_id}[/dim]")
                    continue

                else:
                    console.print(f"[yellow]Unknown command: {cmd}. Type /help[/yellow]")
                    continue

            messages.append({"role": "user", "content": user_input})
            store.add_message(session_id, "user", user_input)

            try:
                with console.status("[dim]thinking...[/dim]"):
                    response = _repl_turn(client, cfg, system, messages, tools)

                console.print(Panel(Markdown(response), expand=False))
                messages.append({"role": "assistant", "content": response})
                store.add_message(session_id, "assistant", response)

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                if cfg.debug:
                    raise

    except KeyboardInterrupt:
        pass

    console.print("\n[dim]Session saved.[/dim]")


def _repl_turn(client, cfg, system, messages, tools) -> str:
    """Single REPL turn with tool loop."""
    from da.client import call_agent

    working_messages = list(messages)
    max_iter = 20

    for _ in range(max_iter):
        response = call_agent(client, cfg, system, working_messages, tools)

        assistant_content = []
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_uses.append(block)
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        working_messages.append({"role": "assistant", "content": assistant_content})

        if not tool_uses:
            return "\n".join(text_parts)

        tool_results = []
        for tu in tool_uses:
            console.print(f"  [dim]→ {tu.name}[/dim]")
            result = execute_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": str(result),
            })

        working_messages.append({"role": "user", "content": tool_results})

    return "\n".join(text_parts) if text_parts else "(max iterations)"


if __name__ == "__main__":
    cli()
