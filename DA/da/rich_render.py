"""Rich rendering helpers for DA TUI.

Converts raw message content into Rich renderables for RichLog output:
  - User messages: green-bordered Panel
  - Assistant messages: Markdown with syntax-highlighted code blocks
  - Tool messages: dim italic arrows
  - Session banners: styled Panel with subtitle
"""

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


def render_user(content: str):
    """Render a user message as a green-bordered panel."""
    return Panel(
        Text(content, style="green"),
        title="[bold green]you[/bold green]",
        border_style="green",
        padding=(0, 1),
    )


def render_assistant(content: str):
    """Render assistant message as Markdown with syntax highlighting."""
    try:
        return Group(
            Markdown(content, code_theme="monokai"),
            Rule(style="dim"),
        )
    except Exception:
        return Group(Text(content), Rule(style="dim"))


def render_tool(content: str):
    """Render tool/system message as dim italic text."""
    return Text(f"  \u2192 {content}", style="dim italic")


def render_banner(banner_text: str, version: str, model: str, tool_count: int):
    """Render the welcome banner as a styled panel."""
    return Group(
        Panel(
            Text(banner_text, style="bold cyan"),
            subtitle=f"v{version} | {model} | {tool_count} tools",
            border_style="cyan",
        ),
        Text("  type /help or Ctrl+Q to quit\n", style="dim"),
    )


def render_message(role: str, content: str):
    """Dispatch to the correct renderer by role."""
    if role == "user":
        return render_user(content)
    elif role == "tool":
        return render_tool(content)
    else:
        return render_assistant(content)


def session_info_table(rows: list[tuple[str, str]], title: str = "Session",
                       border_style: str = "cyan") -> Panel:
    """Build a key-value info panel for session details."""
    t = Table(show_header=False, box=None, pad_edge=False, show_edge=False)
    t.add_column("key", style="bold cyan", width=14, no_wrap=True)
    t.add_column("val")
    for k, v in rows:
        t.add_row(k, v)
    return Panel(t, title=title, border_style=border_style)
