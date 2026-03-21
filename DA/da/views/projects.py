"""Projects view — browse Obsidian notes with type: Project frontmatter.

Menu: [P]rojects  |  F5  |  /projects

Displays all Project-type notes from the Obsidian vault with status,
priority, category, and description. Supports filtering and note preview.
"""

from pathlib import Path
from typing import Callable

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from da.config import Config
from da.obsidian import (
    vault_path,
    list_projects,
    read_note,
    extract_tags,
    parse_frontmatter,
    ProjectInfo,
)

MENU_KEY = "P"
MENU_LABEL = "rojects"

STATUS_ICONS = {
    "active": "\u25cf",      # ●
    "on-hold": "\u25cb",     # ○
    "archived": "\u2581",    # ▁
}
STATUS_STYLES = {
    "active": "green",
    "on-hold": "yellow",
    "archived": "dim",
}
PRIORITY_STYLES = {
    "high": "red bold",
    "medium": "yellow",
    "low": "dim",
}


def _hint(text: str):
    return Text(f"  \u2192 {text}", style="dim italic")


class ProjectsView:
    """Browse Obsidian Project notes via output callbacks."""

    def __init__(self, cfg: Config, output: Callable | None = None, clear: Callable | None = None):
        self.cfg = cfg
        self.vault = vault_path(cfg)
        self.output = output or (lambda x: None)
        self.clear = clear or (lambda: None)
        self._projects: list[ProjectInfo] = []
        self._filtered: list[ProjectInfo] = []
        self._mode = "list"  # list | detail
        self._filter: str = ""  # current filter text

    # ── List ───────────────────────────────────────────────────────

    def show(self) -> None:
        if not self.vault.exists():
            self.output(_hint(f"Vault not found: {self.vault}"))
            return
        self._projects = list_projects(self.vault)
        self._filtered = self._projects
        self._filter = ""
        self._mode = "list"
        self._render_list()

    def _render_list(self) -> None:
        self.clear()
        projects = self._filtered
        title = f"Projects ({len(projects)})"
        if self._filter:
            title += f' — filter: "{self._filter}"'

        t = Table(title=title, show_edge=False, pad_edge=False)
        t.add_column("#", style="dim", width=3)
        t.add_column("Status", width=6)
        t.add_column("Name", style="cyan bold", max_width=30)
        t.add_column("Category", style="dim", max_width=15)
        t.add_column("Priority", max_width=8)
        t.add_column("Org", style="dim", max_width=15)
        t.add_column("Description", max_width=50)

        for i, p in enumerate(projects, 1):
            icon = STATUS_ICONS.get(p.status, "\u00b7")
            st_style = STATUS_STYLES.get(p.status, "dim")
            status_text = Text(f"{icon} {p.status or '-'}", style=st_style)

            pri_style = PRIORITY_STYLES.get(p.priority, "dim")
            pri_text = Text(p.priority or "-", style=pri_style)

            t.add_row(
                str(i),
                status_text,
                p.name,
                p.category or "-",
                pri_text,
                p.owner_org or "-",
                (p.description[:48] + "\u2026") if len(p.description) > 50 else (p.description or "-"),
            )

        self.output(t)
        self.output(_hint("<#> to view | /filter <text> | /active | /all | /back"))

    # ── Detail ─────────────────────────────────────────────────────

    def _show_detail(self, proj: ProjectInfo) -> None:
        self.clear()
        self._mode = "detail"

        # Metadata panel
        meta = Text()
        meta.append(f"{proj.folder}/{proj.name}" if proj.folder else proj.name, style="bold cyan")
        meta.append(f"\n", style="dim")

        fields = [
            ("Status", proj.status),
            ("Priority", proj.priority),
            ("Category", proj.category),
            ("Org", proj.owner_org),
            ("Created", proj.created),
            ("Updated", proj.updated),
        ]
        for label, val in fields:
            if val:
                meta.append(f"  {label}: ", style="bold")
                style = STATUS_STYLES.get(val, PRIORITY_STYLES.get(val, ""))
                meta.append(f"{val}\n", style=style or "")

        if proj.tags:
            meta.append("  Tags: ", style="bold")
            for tag in proj.tags:
                meta.append(f"#{tag} ", style="cyan")
            meta.append("\n")

        if proj.description:
            meta.append(f"  {proj.description}\n", style="italic")

        self.output(Panel(meta, border_style="cyan", padding=(0, 1)))

        # Note content
        try:
            content = read_note(proj.path)
            # Strip frontmatter for display
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    content = content[end + 3:].strip()
            if content:
                try:
                    md = Markdown(content, code_theme="monokai")
                    self.output(Panel(md, border_style="dim", padding=(0, 1)))
                except Exception:
                    self.output(Panel(Text(content), border_style="dim", padding=(0, 1)))
            else:
                self.output(_hint("(no content beyond frontmatter)"))
        except Exception as e:
            self.output(_hint(f"Error reading note: {e}"))

        self.output(_hint("/back | <#> from list"))

    # ── Filtering ──────────────────────────────────────────────────

    def _apply_filter(self, query: str) -> None:
        self._filter = query
        q = query.lower()
        self._filtered = [
            p for p in self._projects
            if q in p.name.lower()
            or q in p.description.lower()
            or q in p.category.lower()
            or q in p.status.lower()
            or q in p.owner_org.lower()
            or q in p.folder.lower()
            or any(q in t.lower() for t in p.tags)
        ]
        self._mode = "list"
        self._render_list()

    # ── Input dispatch ─────────────────────────────────────────────

    def handle_input(self, text: str) -> None:
        text = text.strip()
        if not text:
            return

        if text.startswith("/"):
            parts = text.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/back":
                if self._mode == "detail":
                    self._mode = "list"
                    self._render_list()
                else:
                    self.show()
            elif cmd == "/filter":
                if arg:
                    self._apply_filter(arg)
                else:
                    self.output(_hint("Usage: /filter <text>"))
            elif cmd == "/active":
                self._filter = "active"
                self._filtered = [p for p in self._projects if p.status == "active"]
                self._mode = "list"
                self._render_list()
            elif cmd == "/all":
                self._filter = ""
                self._filtered = self._projects
                self._mode = "list"
                self._render_list()
            elif cmd in ("/refresh", "/reload"):
                self.show()
            else:
                self.output(_hint(f"Unknown: {cmd}. Try /filter, /active, /all, /back"))
            return

        # Bare number — select project
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(self._filtered):
                self._show_detail(self._filtered[idx])
            else:
                self.output(_hint(f"Invalid index: {text}"))
            return

        # Text input — filter
        if len(text) > 1:
            self._apply_filter(text)
        else:
            self.output(_hint("<#> | /filter <text> | /active | /all"))
