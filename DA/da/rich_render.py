"""Rich rendering helpers for DA TUI, CLI, and session manager.

Centralizes all Rich renderable construction so tui.py, cli.py, and
session_manager.py can import ready-made renderables instead of
building them inline.

Consumers call these functions and write the result to a RichLog (TUI)
or Console (CLI).
"""

from rich.box import ROUNDED, SIMPLE, HEAVY
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

# Shared console for CLI commands
console = Console()


# ── Menu bar ─────────────────────────────────────────────────────────

def render_menu_bar(
    tabs: list[tuple[str, str, str]],
    active: str,
    status: str = "",
) -> Text:
    """Render a menu bar with highlighted shortcut letters.

    tabs: [(key, label, view_name), ...] e.g. [("Д", "ДА", "da"), ("S", "essions", "sessions")]
          key is the highlighted shortcut letter, label is the rest of the text.
    active: which view_name is currently active
    status: right-side status text
    """
    bar = Text()
    for key, label, view_name in tabs:
        is_active = (view_name == active)
        if is_active:
            bar.append(" [", style="bold white on blue")
            bar.append(key, style="bold yellow on blue underline")
            bar.append(f"]{label} ", style="bold white on blue")
        else:
            bar.append(" [", style="dim")
            bar.append(key, style="yellow underline")
            bar.append(f"]{label} ", style="dim")
        bar.append(" ")

    if status:
        bar.append(f" {status}", style="dim")

    return bar


# ── Message rendering ────────────────────────────────────────────────

def render_user(content: str):
    """User message → green-bordered panel."""
    return Panel(
        Text(content, style="green"),
        title="[bold green]you[/bold green]",
        border_style="green",
        box=ROUNDED,
        padding=(0, 1),
    )


def render_assistant(content: str):
    """Assistant message → Markdown in a cyan panel."""
    try:
        body = Markdown(content, code_theme="monokai")
    except Exception:
        body = Text(content)
    return Panel(
        body,
        title="[bold cyan]\u0414\u0410[/bold cyan]",
        border_style="cyan",
        box=ROUNDED,
        padding=(0, 1),
    )


def render_tool(content: str):
    """Tool / system message → dim panel with arrow."""
    return Panel(
        Text(f"\u2192 {content}", style="dim italic"),
        border_style="dim",
        box=SIMPLE,
        padding=(0, 1),
    )


def render_tool_call(name: str, status: str = "running"):
    """Tool call indicator → compact panel with tool name."""
    icon = "\u2699" if status == "running" else "\u2713"  # ⚙ or ✓
    style = "yellow" if status == "running" else "green"
    return Panel(
        Text(f"{icon} {name}", style=style),
        border_style="dim",
        box=SIMPLE,
        padding=(0, 0),
    )


def render_thinking():
    """Live 'thinking' panel."""
    return Panel(
        Text("\u2026 thinking", style="bold green"),
        border_style="green",
        box=ROUNDED,
        padding=(0, 1),
        title="[dim]\u0414\u0410[/dim]",
    )


def render_loading(label: str = "Loading..."):
    """Loading indicator panel with spinner character."""
    return Panel(
        Text(f"\u25e2 {label}", style="bold yellow"),
        border_style="yellow",
        box=ROUNDED,
        padding=(0, 1),
    )


def render_message(role: str, content: str):
    """Dispatch to the correct renderer by role."""
    if role == "user":
        return render_user(content)
    elif role == "tool":
        return render_tool(content)
    else:
        return render_assistant(content)


def render_banner(banner_text: str, version: str, model: str, tool_count: int):
    """Welcome banner → styled panel with subtitle."""
    return Group(
        Panel(
            Text(banner_text, style="bold cyan"),
            subtitle=f"v{version} | {model} | {tool_count} tools",
            border_style="cyan",
        ),
        Text("  type /help or Ctrl+Q to quit\n", style="dim"),
    )


# ── Session info tables ─────────────────────────────────────────────

def session_info_table(
    rows: list[tuple[str, str]],
    title: str = "Session",
    border_style: str = "cyan",
) -> Panel:
    """Key-value info panel for session details."""
    t = Table(show_header=False, box=None, pad_edge=False, show_edge=False)
    t.add_column("key", style="bold cyan", width=14, no_wrap=True)
    t.add_column("val")
    for k, v in rows:
        t.add_row(k, v)
    return Panel(t, title=title, border_style=border_style)


def render_message_preview(messages: list[dict], limit: int = 5):
    """Render a 'Recent:' preview of the last N messages."""
    items = []
    items.append(Text("Recent:", style="bold"))
    for m in messages[-limit:]:
        content = m.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if m["role"] == "user":
            items.append(Text(f"> {content[:100]}", style="green"))
        elif m["role"] == "assistant":
            items.append(Text(content[:200]))
    return Group(*items)


def render_session(
    messages: list[dict],
    stats: dict | None = None,
    title: str = "Session",
) -> list:
    """Render a full session conversation as a list of Rich renderables.

    Returns a list so callers can write each item to RichLog individually.

    Layout:
      ╭─ Session ──────────────────────╮
      │ Name   │  12 msgs  │  date     │
      ╰────────────────────────────────╯
      ╭─ you #1 ───────────────────────╮
      │ What's the status?             │
      ╰────────────────────────────────╯
      ╭─────────────────────────────────╮
      │ ⚙ shell  ⚙ read_file           │
      ╰─────────────────────────────────╯
      ╭─ ДА ───────────────────────────╮
      │ The project has 3 open issues  │
      ╰────────────────────────────────╯
    """
    items = []

    # Stats header panel
    if stats:
        import datetime
        created = ""
        if stats.get("created_at"):
            created = datetime.datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M")

        t = Table(show_header=False, box=None, pad_edge=False, show_edge=False, expand=True)
        t.add_column("key", style="bold cyan", width=12, no_wrap=True)
        t.add_column("val")
        t.add_row("Name", stats.get("name", "") or title)
        t.add_row("Messages", str(stats.get("total_messages", len(messages))))
        if created:
            t.add_row("Created", created)
        if stats.get("project"):
            t.add_row("Project", stats["project"].split("/")[-1])
        for role, count in sorted(stats.get("message_counts", {}).items()):
            t.add_row(f"  {role}", str(count))

        items.append(Panel(t, title="[bold blue]Session[/bold blue]", border_style="blue",
                           box=HEAVY, padding=(0, 1)))

    if not messages:
        items.append(Panel(
            Text("(empty session)", style="dim italic"),
            border_style="dim", box=SIMPLE, padding=(0, 1),
        ))
        return items

    # Message timeline — group consecutive tool calls
    msg_num = 0
    pending_tools: list[str] = []

    def flush_tools():
        nonlocal pending_tools
        if pending_tools:
            tool_text = Text()
            for i, name in enumerate(pending_tools):
                if i > 0:
                    tool_text.append("  ")
                tool_text.append("\u2699 ", style="yellow")
                tool_text.append(name, style="yellow italic")
            items.append(Panel(
                tool_text,
                border_style="yellow dim",
                box=ROUNDED,
                padding=(0, 1),
                title="[dim yellow]tools[/dim yellow]",
            ))
            pending_tools = []

    for m in messages:
        content = m.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        role = m.get("role", "")

        if role == "tool":
            pending_tools.append(content)
            continue

        flush_tools()

        if role == "user":
            msg_num += 1
            items.append(Panel(
                Text(content, style="green"),
                title=f"[bold green]you[/bold green] [dim]#{msg_num}[/dim]",
                border_style="green",
                box=ROUNDED,
                padding=(0, 1),
            ))
        elif role == "assistant":
            try:
                body = Markdown(content, code_theme="monokai")
            except Exception:
                body = Text(content)
            items.append(Panel(
                body,
                title="[bold cyan]\u0414\u0410[/bold cyan]",
                border_style="cyan",
                box=ROUNDED,
                padding=(0, 1),
            ))

    flush_tools()
    return items


# ── CLI panels ───────────────────────────────────────────────────────

def query_panel(query: str) -> Panel:
    """Wrap a user query in a cyan panel (CLI ask command)."""
    return Panel(f"[bold cyan]{query}[/bold cyan]", title="Query", expand=False)


def result_panel(content: str) -> Panel:
    """Wrap an assistant result as Markdown in a green panel (CLI ask command)."""
    return Panel(Markdown(content), title="[bold green]Result", expand=False)


def response_panel(content: str) -> Panel:
    """Generic assistant response panel (CLI REPL)."""
    return Panel(Markdown(content), expand=False)


# ── Help / command list ──────────────────────────────────────────────

def render_help_lines(lines: list[tuple[str, str]], title: str = "Commands") -> Group:
    """Render a list of (label, description) as styled help text."""
    items = [Text(title, style="bold")]
    for label, desc in lines:
        items.append(Text(f"  {label:<18s} {desc}", style="dim"))
    return Group(*items)


# ── Sessions table ───────────────────────────────────────────────────

def sessions_table(
    columns: list[tuple[str, str]],
    rows: list[list[str]],
    title: str = "Sessions",
) -> Table:
    """Build a sessions table. columns = [(label, key), ...]."""
    t = Table(title=title)
    for label, _key in columns:
        t.add_column(label)
    for row in rows:
        t.add_row(*row)
    return t
