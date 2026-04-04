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
        ctx.invoke(tui)


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


def _run_tool_shortcut_git(arg: str) -> str:
    """Handle /git shortcuts: /git, /git diff, /git log N, /git commit msg."""
    if not arg:
        return execute_tool("git_status", {"repo_path": "."})
    sub = arg.split(None, 1)
    subcmd = sub[0].lower()
    subarg = sub[1] if len(sub) > 1 else ""
    if subcmd == "status":
        return execute_tool("git_status", {"repo_path": subarg or "."})
    elif subcmd == "diff":
        inputs = {"repo_path": "."}
        if subarg:
            if subarg == "--staged":
                inputs["staged"] = True
            else:
                inputs["ref"] = subarg
        return execute_tool("git_diff", inputs)
    elif subcmd == "log":
        inputs = {"repo_path": ".", "oneline": True}
        if subarg and subarg.isdigit():
            inputs["count"] = int(subarg)
        return execute_tool("git_log", inputs)
    elif subcmd == "commit":
        if subarg:
            return execute_tool("git_commit_push", {"repo_path": ".", "message": subarg})
        return "[yellow]Usage: /git commit <message>[/yellow]"
    elif subcmd == "push":
        return execute_tool("git_commit_push", {"repo_path": ".", "message": subarg or "push", "push": True})
    else:
        # Pass through as shell git command
        return execute_tool("shell_exec", {"command": f"git {arg}"})


def _run_tool_shortcut_docker(arg: str) -> str:
    """Handle /docker shortcuts: /docker, /docker logs <c>, /docker exec <c> <cmd>."""
    if not arg:
        return execute_tool("docker_ps", {})
    sub = arg.split(None, 1)
    subcmd = sub[0].lower()
    subarg = sub[1] if len(sub) > 1 else ""
    if subcmd == "ps":
        return execute_tool("docker_ps", {"all": bool(subarg and "--all" in subarg)})
    elif subcmd == "logs":
        if subarg:
            parts = subarg.split(None, 1)
            return execute_tool("docker_logs", {"container": parts[0], "tail": 50})
        return "[yellow]Usage: /docker logs <container>[/yellow]"
    elif subcmd == "exec":
        parts = subarg.split(None, 1) if subarg else []
        if len(parts) >= 2:
            return execute_tool("docker_exec", {"container": parts[0], "command": parts[1]})
        return "[yellow]Usage: /docker exec <container> <command>[/yellow]"
    elif subcmd in ("up", "down", "restart", "build"):
        return execute_tool("docker_compose", {"command": subcmd, "service": subarg or ""})
    else:
        return execute_tool("shell_exec", {"command": f"docker {arg}"})


@cli.command()
@click.option("--model", "-m", help="Model override")
@click.option("--session", "-s", "session_id_opt", default=None, help="Resume existing session by ID")
@click.pass_context
def repl(ctx: click.Context, model: Optional[str], session_id_opt: Optional[str]) -> None:
    """Interactive REPL — chat with DeepAgents."""
    cfg = ctx.obj["config"]
    if model:
        cfg.model = model
    store = ctx.obj["session_store"]

    if session_id_opt:
        session_id = session_id_opt
        messages = [
            m for m in store.get_messages(session_id, limit=100)
            if m["role"] in ("user", "assistant")
        ]
    else:
        session_id = str(uuid.uuid4())
        store.create_session(session_id, name="repl", project=os.getcwd())
        messages = []

    client = get_client(cfg)
    system = get_system_prompt(cfg)
    tools = _make_api_tools()

    from da import __version__
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.styles import Style

    MODELS = {
        "opus": "claude-opus-4-6",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }

    # Slash command completer — triggers on /
    SLASH_COMMANDS = {
        "/model": "switch model (opus/sonnet/haiku)",
        "/tools": "list available tools",
        "/hosts": "list configured hosts",
        "/session": "show current session ID",
        "/sessions": "list all sessions",
        "/clear": "clear conversation",
        "/compact": "summarize and trim context",
        "/help": "show all commands",
    }

    # Direct tool shortcuts (like Claude Code's ! for shell)
    TOOL_SHORTCUTS = {
        "!": ("shell_exec", "command", "run shell command"),
        "/git": ("git_status", None, "git status (or /git diff, /git log)"),
        "/diff": ("git_diff", None, "git diff"),
        "/log": ("git_log", None, "git log"),
        "/ssh": ("ssh_exec", None, "ssh <host> <command>"),
        "/docker": ("docker_ps", None, "docker ps (or /docker logs, /docker exec)"),
        "/grep": ("grep_search", None, "grep <pattern> [path]"),
        "/find": ("glob_find", None, "find files by glob pattern"),
        "/cat": ("read_file", None, "read a file"),
        "/ls": ("list_dir", None, "list directory"),
        "/gh": ("gh_cli", None, "github cli command"),
    }

    # Context words for natural language — host names, project names, tool names
    context_words = set()
    for h in cfg.hosts:
        context_words.add(h)
    for p in cfg.projects:
        context_words.add(p)
    for t in ALL_TOOL_DEFS:
        # Add tool name fragments: "git_status" -> "git", "status"
        for part in t["name"].split("_"):
            if len(part) > 2:
                context_words.add(part)

    class DACompleter(Completer):
        """Claude Code-style completer: slash commands, tool shortcuts, paths, and context words."""

        def __init__(self):
            self.path_completer = PathCompleter(expanduser=True)

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor

            # Slash commands and tool shortcuts
            if text.startswith("/"):
                parts = text.split(None, 1)
                cmd = parts[0]

                # /model <alias> completion
                if cmd == "/model" and len(parts) > 1:
                    arg = parts[1].lower()
                    for alias, mid in MODELS.items():
                        if alias.startswith(arg):
                            yield Completion(alias, start_position=-len(arg), display_meta=mid)
                    return

                # /git <subcommand> completion
                if cmd == "/git" and len(parts) > 1:
                    arg = parts[1].lower()
                    git_subs = {
                        "status": "show working tree status",
                        "diff": "show changes (--staged for staged)",
                        "log": "show commit log (add N for count)",
                        "commit": "commit with message",
                        "push": "commit and push",
                    }
                    for sub, desc in git_subs.items():
                        if sub.startswith(arg):
                            yield Completion(sub, start_position=-len(arg), display_meta=desc)
                    return

                # /docker <subcommand> completion
                if cmd == "/docker" and len(parts) > 1:
                    arg = parts[1].split(None, 1)[0] if parts[1] else ""
                    if " " not in parts[1]:
                        docker_subs = {
                            "ps": "list containers",
                            "logs": "container logs",
                            "exec": "exec in container",
                            "up": "docker compose up",
                            "down": "docker compose down",
                            "restart": "docker compose restart",
                            "build": "docker compose build",
                        }
                        for sub, desc in docker_subs.items():
                            if sub.startswith(arg):
                                yield Completion(sub, start_position=-len(arg), display_meta=desc)
                    return

                # /ssh <host> completion
                if cmd == "/ssh" and len(parts) > 1:
                    arg = parts[1].split(None, 1)[0] if parts[1] else ""
                    if " " not in parts[1]:
                        for host in cfg.hosts:
                            if host.startswith(arg):
                                yield Completion(host, start_position=-len(arg), display_meta=cfg.hosts[host].ssh)
                    return

                # Top-level: slash commands + tool shortcuts
                for slash_cmd, desc in SLASH_COMMANDS.items():
                    if slash_cmd.startswith(text):
                        yield Completion(slash_cmd, start_position=-len(text), display_meta=desc)
                for shortcut, (_, _, desc) in TOOL_SHORTCUTS.items():
                    if shortcut.startswith("/") and shortcut.startswith(text):
                        yield Completion(shortcut + " ", start_position=-len(text), display_meta=desc)
                return

            # ! shell shortcut completion — complete paths after !
            if text.startswith("!"):
                shell_part = text[1:].lstrip()
                word = document.get_word_before_cursor(WORD=True)
                if word and word.startswith(("/", "./", "../", "~/")):
                    yield from self.path_completer.get_completions(document, complete_event)
                return

            # Path completion — trigger on /, ./, ../, or ~/
            word = document.get_word_before_cursor(WORD=True)
            if word and word.startswith(("./", "../", "~/")):
                yield from self.path_completer.get_completions(document, complete_event)
                return

            # Context word completion — only when typing 3+ chars
            if word and len(word) >= 3:
                lower = word.lower()
                for cw in sorted(context_words):
                    if cw.lower().startswith(lower) and cw.lower() != lower:
                        yield Completion(cw, start_position=-len(word))

    # Key bindings: Enter sends, Escape+Enter / Alt+Enter for newline
    kb = KeyBindings()

    @kb.add(Keys.Enter)
    def _submit(event):
        """Submit on Enter (unless in paste mode or text ends with \\)."""
        buf = event.app.current_buffer
        text = buf.text
        # Allow continuation with trailing backslash
        if text.rstrip().endswith("\\"):
            buf.insert_text("\n")
        else:
            buf.validate_and_handle()

    @kb.add(Keys.Escape, Keys.Enter)
    def _newline_escape(event):
        """Insert newline on Escape+Enter."""
        event.app.current_buffer.insert_text("\n")

    # Style
    style = Style.from_dict({
        "prompt": "bold cyan",
        "bottom-toolbar": "bg:#333333 #aaaaaa",
    })

    def bottom_toolbar():
        model_short = cfg.model.split("-")[-1] if "-" in cfg.model else cfg.model
        return HTML(
            f" <b>{model_short}</b>"
            f" │ {len(tools)} tools │ {len(cfg.hosts)} hosts"
            f" │ session: {session_id[:8]}"
            f" │ {len(messages)} msgs"
            f"  <i>Enter</i>=send <i>Esc+Enter</i>=newline <i>/help</i>"
        )

    # Banner
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
    console.print(f"  v{__version__} | {cfg.model} | {len(tools)} tools | {len(cfg.hosts)} hosts", style="dim")
    console.print("  type /help or Ctrl+C to quit\n", style="dim")

    # prompt_toolkit session with history + completion
    history_path = Path.home() / ".da" / "history.txt"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(
        history=FileHistory(str(history_path)),
        completer=DACompleter(),
        complete_while_typing=True,
        key_bindings=kb,
        style=style,
        bottom_toolbar=bottom_toolbar,
        multiline=True,
    )

    try:
        while True:
            try:
                user_input = session.prompt(HTML("<prompt>da&gt; </prompt>")).strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break

            # ! shell shortcut — like Claude Code
            if user_input.startswith("!"):
                shell_cmd = user_input[1:].strip()
                if shell_cmd:
                    console.print(f"  [dim]→ shell_exec[/dim]")
                    result = execute_tool("shell_exec", {"command": shell_cmd})
                    console.print(result)
                continue

            # Slash commands
            if user_input.startswith("/"):
                parts = user_input.split(None, 1)
                cmd = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""

                if cmd == "/model":
                    if arg and arg.lower() in MODELS:
                        cfg.model = MODELS[arg.lower()]
                        console.print(f"[bold green]Model: {cfg.model}[/bold green]")
                    elif arg:
                        cfg.model = arg
                        console.print(f"[bold green]Model: {cfg.model}[/bold green]")
                    else:
                        console.print(f"[bold]Current:[/bold] {cfg.model}")
                        for alias, mid in MODELS.items():
                            console.print(f"[dim]  /model {alias:7s} — {mid}[/dim]")
                elif cmd == "/help":
                    console.print("[bold]Commands:[/bold]")
                    for c, d in SLASH_COMMANDS.items():
                        console.print(f"  [cyan]{c:12s}[/cyan] — {d}")
                    console.print(f"\n[bold]Tool shortcuts:[/bold]")
                    console.print(f"  [cyan]{'!<cmd>':12s}[/cyan] — run shell command directly")
                    for sc, (_, _, desc) in TOOL_SHORTCUTS.items():
                        if sc != "!":
                            console.print(f"  [cyan]{sc:12s}[/cyan] — {desc}")
                    console.print(f"\n[bold]Models:[/bold]")
                    for alias in MODELS:
                        console.print(f"  [cyan]/model {alias:5s}[/cyan] — {MODELS[alias]}")
                    console.print(f"\n  [cyan]{'exit':12s}[/cyan] — quit")
                    console.print(f"\n[dim]  Enter=send  Esc+Enter=newline  \\\\ at EOL=continue[/dim]")
                elif cmd == "/tools":
                    for t in ALL_TOOL_DEFS:
                        console.print(f"  [cyan]{t['name']:18s}[/cyan] {t['description'][:55]}")
                elif cmd == "/hosts":
                    for name, h in cfg.hosts.items():
                        console.print(f"  [cyan]{name:15s}[/cyan] {h.ssh} [{', '.join(h.roles)}]")
                elif cmd == "/session":
                    console.print(f"  [dim]{session_id}[/dim]")
                elif cmd == "/sessions":
                    all_sessions = store.list_sessions(limit=20)
                    for s in all_sessions:
                        marker = " *" if s["id"] == session_id else ""
                        console.print(f"  [dim]{s['id'][:12]}[/dim]  {s['name'] or '—'}{marker}")
                elif cmd == "/clear":
                    messages.clear()
                    console.clear()
                    console.print("[dim]Conversation cleared.[/dim]")
                elif cmd == "/compact":
                    if len(messages) > 4:
                        kept = messages[-4:]
                        dropped = len(messages) - 4
                        messages.clear()
                        messages.extend(kept)
                        console.print(f"[dim]Compacted: dropped {dropped} older messages, kept last 4.[/dim]")
                    else:
                        console.print("[dim]Nothing to compact.[/dim]")

                # --- Tool shortcuts ---
                elif cmd == "/git":
                    result = _run_tool_shortcut_git(arg)
                    console.print(result)
                elif cmd == "/diff":
                    console.print(execute_tool("git_diff", {"repo_path": arg or "."}))
                elif cmd == "/log":
                    console.print(execute_tool("git_log", {"repo_path": arg or ".", "oneline": True}))
                elif cmd == "/ssh":
                    ssh_parts = arg.split(None, 1)
                    if len(ssh_parts) >= 2:
                        console.print(f"  [dim]→ ssh {ssh_parts[0]}[/dim]")
                        console.print(execute_tool("ssh_exec", {"host": ssh_parts[0], "command": ssh_parts[1]}))
                    elif len(ssh_parts) == 1:
                        console.print(f"  [dim]→ ssh {ssh_parts[0]} uptime[/dim]")
                        console.print(execute_tool("ssh_exec", {"host": ssh_parts[0], "command": "uptime"}))
                    else:
                        for name, h in cfg.hosts.items():
                            console.print(f"  [cyan]{name:15s}[/cyan] {h.ssh}")
                elif cmd == "/docker":
                    result = _run_tool_shortcut_docker(arg)
                    console.print(result)
                elif cmd == "/grep":
                    grep_parts = arg.split(None, 1)
                    if grep_parts:
                        inputs = {"pattern": grep_parts[0]}
                        if len(grep_parts) > 1:
                            inputs["path"] = grep_parts[1]
                        console.print(execute_tool("grep_search", inputs))
                    else:
                        console.print("[yellow]Usage: /grep <pattern> [path][/yellow]")
                elif cmd == "/find":
                    if arg:
                        console.print(execute_tool("glob_find", {"pattern": arg}))
                    else:
                        console.print("[yellow]Usage: /find <glob pattern>[/yellow]")
                elif cmd == "/cat":
                    if arg:
                        console.print(execute_tool("read_file", {"path": arg}))
                    else:
                        console.print("[yellow]Usage: /cat <file path>[/yellow]")
                elif cmd == "/ls":
                    console.print(execute_tool("list_dir", {"path": arg or "."}))
                elif cmd == "/gh":
                    if arg:
                        console.print(execute_tool("gh_cli", {"command": arg}))
                    else:
                        console.print("[yellow]Usage: /gh <command> (e.g. /gh pr list)[/yellow]")
                else:
                    console.print(f"[yellow]Unknown: {cmd}. Type /help[/yellow]")
                continue

            # Agent turn
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


@cli.command()
@click.pass_context
def tui(ctx: click.Context) -> None:
    """Full TUI with session sidebar and multi-session support."""
    from da.tui import run_tui
    run_tui(ctx.obj["config"])


@cli.command()
@click.pass_context
def rich(ctx: click.Context) -> None:
    """Rich console REPL — lightweight alternative to full TUI."""
    from da.rich_tui import run_rich_tui
    run_rich_tui(ctx.obj["config"])


@cli.command()
@click.pass_context
def manage(ctx: click.Context) -> None:
    """Session manager — browse, rename, copy, move, delete sessions."""
    from da.session_manager import run_manager
    run_manager(ctx.obj["config"])


# ── Session Manager commands (merged from SM) ───────────────────────────────

@cli.command()
@click.pass_context
def discover(ctx: click.Context) -> None:
    """Discover all LLM session logs across all sources."""
    store = ctx.obj["session_store"]
    found = store.discover_all(mode="quick")
    if not found:
        console.print("[dim]No sessions discovered.[/dim]")
        return

    from rich.table import Table
    from collections import Counter

    by_source = Counter(s["source"] for s in found)
    total_size = sum(s.get("size", 0) for s in found)

    table = Table(title=f"Discovered {len(found)} sessions ({total_size // 1024}K)")
    table.add_column("Source", max_width=25)
    table.add_column("Count", justify="right")
    for src, count in by_source.most_common():
        table.add_row(src, str(count))
    console.print(table)


@cli.command("deposit")
@click.argument("path")
@click.pass_context
def deposit(ctx: click.Context, path: str) -> None:
    """Deposit a session JSONL to Langfuse."""
    store = ctx.obj["session_store"]
    ok = store.deposit_to_langfuse(path)
    if ok:
        console.print(f"[green]✅ Deposited to Langfuse[/green]")
    else:
        console.print(f"[red]❌ Failed to deposit[/red]")


@cli.command("deposit-all")
@click.pass_context
def deposit_all(ctx: click.Context) -> None:
    """Deposit all discovered sessions to Langfuse."""
    store = ctx.obj["session_store"]
    found = store.discover_all(mode="quick")
    ok = fail = 0
    for s in found:
        if store.deposit_to_langfuse(s["path"]):
            ok += 1
            console.print(f"  [green]✅[/green] {s['source']}: {s['session_id'][:12]}...")
        else:
            fail += 1
    console.print(f"\n[bold]{ok} deposited, {fail} failed[/bold]")


@cli.command("import-chatgpt")
@click.argument("source")
@click.option("--output", default="./imported-chatgpt")
@click.pass_context
def import_chatgpt_cmd(ctx: click.Context, source: str, output: str) -> None:
    """Import ChatGPT data export (ZIP or conversations.json)."""
    store = ctx.obj["session_store"]
    results = store.import_chatgpt(source, output)
    console.print(f"[green]Imported {len(results)} conversations → {output}[/green]")


@cli.command("import-claude")
@click.argument("source")
@click.option("--output", default="./imported-claude")
@click.pass_context
def import_claude_cmd(ctx: click.Context, source: str, output: str) -> None:
    """Import Claude.ai data export (ZIP or JSON)."""
    store = ctx.obj["session_store"]
    results = store.import_claude_export(source, output)
    console.print(f"[green]Imported {len(results)} conversations → {output}[/green]")


if __name__ == "__main__":
    cli()
