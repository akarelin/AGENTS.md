"""DA Rich TUI — Full-screen Textual app with Rich rendering.

Uses Textual for full-screen layout, Rich renderables from rich_render.py,
and pluggable view modules from da/views/.

Menu bar with highlighted shortcut keys:
  [P]rojects  — Obsidian projects      (F1 / /projects)
  [Д]А        — chat with agent        (F2 / /da)
  [S]essions  — live session browser   (F3 / /sessions)
  [O]bsidian  — browse Obsidian vault  (F4 / /obsidian)
  [C]onfig    — YAML config editor     (F5 / /config)

Launch: da rich
"""

import datetime

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Input, RichLog, Static, TextArea, Tree

from da import __version__
from da.config import load_config, Config
from da.tools import ALL_TOOL_DEFS
from da.session import SessionStore
from da.rich_render import (
    render_banner,
    render_loading,
    render_menu_bar,
    render_session,
    render_tool,
)
from da.views.da_chat import DAChatView
from da.views.sessions import SessionsView
from da.views.obsidian import ObsidianView
from da.views.config_editor import ConfigEditorView
from da.views.projects import ProjectsView
from da.tui import (
    load_claude_sessions,
    load_claude_session_messages,
    _machine_label,
    _decode_project_dir,
)

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

MODELS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

MENU_TABS = [
    ("P", "rojects", "projects"),
    ("Д", "А", "da"),
    ("S", "essions", "sessions"),
    ("O", "bsidian", "obsidian"),
    ("C", "onfig", "config"),
]


class RichTUIApp(App):
    TITLE = "ДА"
    SUB_TITLE = f"v{__version__}"

    CSS = """
    #menu-bar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
    }
    /* Projects view */
    #projects-view { height: 1fr; }
    #projects-view.hidden { display: none; }
    #projects-log { height: 1fr; padding: 0 1; }
    /* ДА view */
    #da-view { height: 1fr; }
    #da-view.hidden { display: none; }
    #da-log { height: 1fr; padding: 0 1; }
    /* Sessions view */
    #sessions-view { height: 1fr; }
    #sessions-view.hidden { display: none; }
    #sessions-table { height: 1fr; }
    #sessions-detail { height: 1fr; padding: 0 1; }
    #sessions-status { height: 1; padding: 0 1; color: $text-muted; }
    /* Obsidian view */
    #obsidian-view { height: 1fr; }
    #obsidian-view.hidden { display: none; }
    #obsidian-log { height: 1fr; padding: 0 1; }
    /* Config editor view */
    #config-view { height: 1fr; }
    #config-view.hidden { display: none; }
    #config-tree { width: 40; border-right: solid $primary; height: 1fr; }
    #config-right { height: 1fr; }
    #config-label {
        dock: top; height: 1; padding: 0 1;
        text-align: center; background: $boost;
    }
    #config-preview { height: 1fr; padding: 0 1; }
    #config-editor { height: 1fr; display: none; }
    #config-editor.visible { display: block; }
    /* Shared */
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    #prompt-input {
        dock: bottom;
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("f1", "switch_projects", "[P]rojects", show=True),
        Binding("f2", "switch_da", "[Д]А", show=True),
        Binding("f3", "switch_sessions", "[S]essions", show=True),
        Binding("f4", "switch_obsidian", "[O]bsidian", show=True),
        Binding("f5", "switch_config", "[C]onfig", show=True),
        Binding("escape", "config_escape", "Back", show=False, priority=True),
        Binding("ctrl+n", "new_session", "New", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(self, config: Config | None = None):
        super().__init__()
        self.cfg = config or load_config()
        self.store = SessionStore(self.cfg.session.db_path)
        self.tool_count = len(ALL_TOOL_DEFS)
        self.view = "da"
        self.busy = False
        self._spinner_frames = "\u25f7\u25f6\u25f5\u25f4\u25f3\u25f2\u25f1\u25f0"
        self._spinner_idx = 0
        self._spinner_timer = None

        # Views
        self.projects_view = ProjectsView(self.cfg)
        self.da_view = DAChatView(self.cfg, self.store)
        self.sessions_view = SessionsView(self.cfg, self.store)
        self.obsidian_view = ObsidianView(self.cfg)
        self.config_view = ConfigEditorView(self.cfg)

        # Claude session info for table selection
        self._table_keys: list[str] = []  # row_key -> "da:sid" or "claude:idx"

    def compose(self) -> ComposeResult:
        yield Static("", id="menu-bar")

        # View 0: Projects
        with Vertical(id="projects-view", classes="hidden"):
            yield RichLog(id="projects-log", wrap=True, markup=True)

        # View 1: ДА chat
        with Vertical(id="da-view"):
            yield RichLog(id="da-log", wrap=True, markup=True)

        # View 2: Sessions — live table + detail panel
        with Horizontal(id="sessions-view", classes="hidden"):
            with Vertical():
                yield DataTable(id="sessions-table", cursor_type="row")
                yield Static("", id="sessions-status")
            yield RichLog(id="sessions-detail", wrap=True, markup=True)

        # View 3: Obsidian
        with Vertical(id="obsidian-view", classes="hidden"):
            yield RichLog(id="obsidian-log", wrap=True, markup=True)

        # View 4: Config Editor
        with Horizontal(id="config-view", classes="hidden"):
            yield Tree("Files", id="config-tree")
            with Vertical(id="config-right"):
                yield Static("Preview", id="config-label", classes="panel-label")
                yield RichLog(id="config-preview", highlight=True, markup=True, wrap=False)
                yield TextArea(id="config-editor", language="yaml", show_line_numbers=True, tab_behavior="indent")

        yield Static("", id="status-bar")
        yield Input(placeholder="Ask anything... (/ for commands)", id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        da_log = self.query_one("#da-log", RichLog)

        # Wire output callbacks
        proj_log = self.query_one("#projects-log", RichLog)
        self.projects_view.output = proj_log.write
        self.projects_view.clear = proj_log.clear

        obs_log = self.query_one("#obsidian-log", RichLog)
        self.da_view.output = da_log.write
        self.sessions_view.output = self.query_one("#sessions-detail", RichLog).write
        self.obsidian_view.output = obs_log.write
        self.obsidian_view.clear = obs_log.clear

        # Wire config editor widgets
        self.config_view.tree = self.query_one("#config-tree", Tree)
        self.config_view.preview = self.query_one("#config-preview", RichLog)
        self.config_view.editor = self.query_one("#config-editor", TextArea)
        self.config_view.status_label = self.query_one("#config-label", Static)

        # Banner + new session
        da_log.write(render_banner(BANNER, __version__, self.cfg.model, self.tool_count))
        self.da_view.new_session()
        self._update_menu()
        self._update_status()

        # Init sessions table columns
        table = self.query_one("#sessions-table", DataTable)
        table.add_column("Type", key="type")
        table.add_column("Machine", key="machine")
        table.add_column("Project", key="project")
        table.add_column("Date", key="date")
        table.add_column("Msgs", key="msgs")
        table.add_column("Name", key="name")

        # Populate DA sessions immediately
        self._populate_da_rows()

        # Load Claude sessions in background
        self._sessions_loading = True
        self._set_sessions_status("\u25f7 Loading Claude sessions\u2026")
        self._spinner_timer = self.set_interval(0.15, self._tick_spinner)
        self._load_claude_sessions_bg()

    # ── Sessions table ───────────────────────────────────────────

    def _populate_da_rows(self) -> None:
        """Add DA sessions to the live table."""
        table = self.query_one("#sessions-table", DataTable)
        for s in self.store.list_sessions_detailed(limit=50):
            name = s["name"] or "\u2014"
            project = (s.get("project") or "").split("/")[-1] or "\u2014"
            date = (
                datetime.datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d")
                if s["updated_at"] else "\u2014"
            )
            key = f"da:{s['id']}"
            active = " \u25c0" if s["id"] == self.da_view.session_id else ""
            table.add_row(
                "\u0414\u0410", "local", project, date, str(s["msg_count"]), name + active,
                key=key,
            )
            self._table_keys.append(key)

    @work(thread=True)
    def _load_claude_sessions_bg(self) -> None:
        """Load Claude sessions in background, populate table rows."""
        self.sessions_view._ensure_claude_data()
        self.call_from_thread(self._populate_claude_rows)

    def _populate_claude_rows(self) -> None:
        """Add Claude sessions to the live table (called from thread)."""
        table = self.query_one("#sessions-table", DataTable)
        for i, s in enumerate(self.sessions_view.claude_flat):
            machine = s.get("_machine", "?")
            project = s.get("_project", "?").split("/")[-1]
            project = project.split("\\")[-1] if "\\" in project else project
            date = s.get("date", "\u2014")
            name = s.get("name", "\u2014")[:50]
            key = f"claude:{i}"
            table.add_row(
                "Claude", _machine_label(machine), project, date, "", name,
                key=key,
            )
            self._table_keys.append(key)

        self._sessions_loading = False
        total = len(self.sessions_view.claude_flat)
        self._set_sessions_status(f"\u2713 {total} Claude sessions loaded")
        self._update_status()

    def _set_sessions_status(self, text: str) -> None:
        try:
            bar = self.query_one("#sessions-status", Static)
            bar.update(f"[dim]{text}[/dim]")
        except Exception:
            pass

    def _refresh_da_rows(self) -> None:
        """Refresh DA rows in the table."""
        table = self.query_one("#sessions-table", DataTable)
        # Remove existing DA rows
        to_remove = [k for k in self._table_keys if k.startswith("da:")]
        for k in to_remove:
            try:
                table.remove_row(k)
            except Exception:
                pass
            self._table_keys.remove(k)
        # Re-add
        self._populate_da_rows()

    # ── Table events ─────────────────────────────────────────────

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not event.row_key:
            return
        key = str(event.row_key.value)
        detail = self.query_one("#sessions-detail", RichLog)
        detail.clear()

        if key.startswith("da:"):
            sid = key[3:]
            stats = self.store.get_session_stats(sid)
            msgs = self.da_view.session_messages.get(sid)
            if msgs is None:
                msgs = self.store.get_messages(sid, limit=100) or []
                self.da_view.session_messages[sid] = msgs
            items = render_session(msgs, stats=stats, title="Session")
            for item in items:
                detail.write(item)

        elif key.startswith("claude:"):
            idx = int(key[7:])
            if idx < len(self.sessions_view.claude_flat):
                self.sessions_view.show_claude_detail(idx + 1)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on a row — switch to that session for DA, launch for Claude."""
        key = str(event.row_key.value)
        if key.startswith("da:"):
            sid = key[3:]
            self.da_view.load_session(sid)
            self._switch_view("da")
            self._show_session_view(sid)
        elif key.startswith("claude:"):
            idx = int(key[7:])
            if idx < len(self.sessions_view.claude_flat):
                self.sessions_view.launch_claude(idx + 1)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        table = self.query_one("#sessions-table", DataTable)
        table.sort(event.column_key)

    # ── Config editor tree events ─────────────────────────────────

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if self.view != "config" or self.config_view.is_editing:
            return
        self.config_view.show_node(event.node.data)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if self.view != "config":
            return
        if self.config_view.is_editing:
            ok, msg = self.config_view.save_and_close()
            self._set_config_status(msg)
            return
        # Only config files are editable (Enter to edit)
        if self.config_view.is_editable_node(event.node.data):
            fp = self.config_view.get_file_for_node(event.node.data)
            if fp:
                self.config_view.start_edit(fp)

    def _set_config_status(self, text: str) -> None:
        try:
            bar = self.query_one("#status-bar", Static)
            bar.update(f"[dim]{text}[/dim]")
        except Exception:
            pass

    # ── Menu bar / status ────────────────────────────────────────

    def _update_menu(self) -> None:
        status = f"{self.cfg.model} | {self.tool_count} tools | /help"
        bar = self.query_one("#menu-bar", Static)
        bar.update(render_menu_bar(MENU_TABS, self.view, status))

    def _tick_spinner(self) -> None:
        loading = self.busy or getattr(self, "_sessions_loading", False)
        if loading:
            self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
            self._update_status()
            if getattr(self, "_sessions_loading", False):
                spin = self._spinner_frames[self._spinner_idx]
                self._set_sessions_status(f"{spin} Loading Claude sessions\u2026")
        elif self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
            self._update_status()

    def _update_status(self) -> None:
        bar = self.query_one("#status-bar", Static)
        spin = self._spinner_frames[self._spinner_idx]
        if self.busy:
            bar.update(f"[bold green]{spin} Thinking...[/bold green]")
        else:
            parts = [self.da_view.session_id[:12], self.view]
            if getattr(self, "_sessions_loading", False):
                parts.append(f"{spin} loading sessions\u2026")
            bar.update(f"[dim]{' | '.join(parts)}[/dim]")

    # ── View switching ───────────────────────────────────────────

    def _switch_view(self, name: str) -> None:
        projects = self.query_one("#projects-view", Vertical)
        da = self.query_one("#da-view", Vertical)
        sessions = self.query_one("#sessions-view", Horizontal)
        obsidian = self.query_one("#obsidian-view", Vertical)
        config = self.query_one("#config-view", Horizontal)
        inp = self.query_one("#prompt-input", Input)

        projects.add_class("hidden")
        da.add_class("hidden")
        sessions.add_class("hidden")
        obsidian.add_class("hidden")
        config.add_class("hidden")

        self.view = name
        if name == "projects":
            projects.remove_class("hidden")
            inp.placeholder = "<#> to view | /filter <text> | /active"
            self.projects_view.show()
            inp.focus()
        elif name == "da":
            da.remove_class("hidden")
            inp.placeholder = "Ask anything... (/ for commands)"
            inp.focus()
        elif name == "sessions":
            sessions.remove_class("hidden")
            inp.placeholder = "/switch <id> | /detail <#> | /launch <#>"
            self.query_one("#sessions-table", DataTable).focus()
        elif name == "obsidian":
            obsidian.remove_class("hidden")
            inp.placeholder = "Search notes..."
            self.obsidian_view.show()
            inp.focus()
        elif name == "config":
            config.remove_class("hidden")
            inp.placeholder = "/validate | /refresh"
            self.config_view.show()
            self.query_one("#config-tree", Tree).focus()

        self._update_menu()
        self._update_status()

    def _show_session_view(self, sid: str | None = None) -> None:
        sid = sid or self.da_view.session_id
        log = self.query_one("#da-log", RichLog)
        log.clear()
        msgs = self.da_view.session_messages.get(sid, [])
        stats = self.store.get_session_stats(sid)
        items = render_session(msgs, stats=stats, title="Session")
        for item in items:
            log.write(item)

    # ── Actions ──────────────────────────────────────────────────

    def action_switch_projects(self) -> None:
        self._switch_view("projects")

    def action_switch_da(self) -> None:
        self._switch_view("da")

    def action_switch_sessions(self) -> None:
        self._switch_view("sessions")

    def action_switch_obsidian(self) -> None:
        self._switch_view("obsidian")

    def action_switch_config(self) -> None:
        self._switch_view("config")

    def action_config_escape(self) -> None:
        if self.view == "config" and self.config_view.is_editing:
            ok, msg = self.config_view.save_and_close()
            self._set_config_status(msg)
            self.query_one("#config-tree", Tree).focus()

    def action_new_session(self) -> None:
        log = self.query_one("#da-log", RichLog)
        log.clear()
        self.da_view.new_session()
        self._switch_view("da")
        self._refresh_da_rows()

    # ── Input handling ───────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        inp = self.query_one("#prompt-input", Input)
        inp.value = ""

        if not text:
            return

        if text.startswith("/"):
            self._handle_slash(text)
            return

        if self.view == "projects":
            self.projects_view.handle_input(text)
        elif self.view == "da":
            if self.busy:
                self.query_one("#da-log", RichLog).write(render_tool("Still thinking..."))
                return
            self.busy = True
            if not self._spinner_timer:
                self._spinner_timer = self.set_interval(0.15, self._tick_spinner)
            self._update_status()
            self._run_da_input(text)
        elif self.view == "obsidian":
            self.obsidian_view.handle_input(text)

    @work(thread=True)
    def _run_da_input(self, text: str) -> None:
        self.da_view.handle_input(text)
        self.busy = False
        self.call_from_thread(self._update_status)

    def _handle_slash(self, text: str) -> None:
        parts = text.split(None, 1)
        verb = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        # Get the right log for current view
        log_id = {
            "projects": "#projects-log",
            "da": "#da-log", "sessions": "#sessions-detail",
            "obsidian": "#obsidian-log", "config": "#config-preview",
        }
        log = self.query_one(log_id.get(self.view, "#da-log"), RichLog)

        if verb == "/projects":
            self._switch_view("projects")
        elif verb == "/da":
            self._switch_view("da")
        elif verb == "/sessions":
            self._switch_view("sessions")
        elif verb == "/obsidian":
            self._switch_view("obsidian")
        elif verb == "/config":
            self._switch_view("config")

        elif verb in ("/help", "/"):
            log.write(render_tool(
                "Views:  F1 /projects  |  F2 /da  |  F3 /sessions  |  F4 /obsidian  |  F5 /config\n"
                "\n"
                "  /model [name] \u2014 switch model (opus/sonnet/haiku)\n"
                "  /tools        \u2014 list tools\n"
                "  /hosts        \u2014 list hosts\n"
                "  /stats        \u2014 current session stats\n"
                "  /view         \u2014 view current session conversation\n"
                "  /new          \u2014 create new session (Ctrl+N)\n"
                "  /switch <id>  \u2014 switch to session by ID prefix\n"
                "  /delete [id]  \u2014 delete session\n"
                "  /claude       \u2014 browse Claude sessions\n"
                "  /detail <#>   \u2014 Claude session detail\n"
                "  /launch <#>   \u2014 open Claude session in terminal\n"
                "  /clear        \u2014 clear log\n"
                "  /quit         \u2014 exit (Ctrl+Q)"
            ))
        elif verb == "/model":
            if arg.lower() in MODELS:
                self.cfg.model = MODELS[arg.lower()]
                log.write(render_tool(f"Model: {self.cfg.model}"))
            elif arg:
                self.cfg.model = arg
                log.write(render_tool(f"Model: {self.cfg.model}"))
            else:
                lines = [f"Current: {self.cfg.model}"]
                for alias, model in MODELS.items():
                    lines.append(f"  /model {alias} \u2014 {model}")
                log.write(render_tool("\n".join(lines)))
            self._update_menu()
        elif verb == "/tools":
            lines = [f"{t['name']:18s} {t['description'][:50]}" for t in ALL_TOOL_DEFS]
            log.write(render_tool("\n".join(lines)))
        elif verb == "/hosts":
            lines = [f"{n:15s} {h.ssh} [{', '.join(h.roles)}]" for n, h in self.cfg.hosts.items()]
            log.write(render_tool("\n".join(lines) if lines else "No hosts configured."))
        elif verb == "/stats":
            self.sessions_view.show_stats(self.da_view.session_id)
        elif verb in ("/view", "/history"):
            self._show_session_view()
        elif verb == "/new":
            self.action_new_session()
        elif verb in ("/switch", "/resume"):
            if not arg:
                log.write(render_tool("Usage: /switch <session-id-prefix>"))
            else:
                sid = self.sessions_view.switch_session(arg)
                if sid:
                    self.da_view.load_session(sid)
                    self._switch_view("da")
                    self._show_session_view(sid)
        elif verb == "/delete":
            target = arg or self.da_view.session_id
            deleted_current = (target == self.da_view.session_id)
            if self.sessions_view.delete_session(target):
                self.da_view.session_messages.pop(target, None)
                if deleted_current:
                    self.da_view.new_session()
                self._refresh_da_rows()
        elif verb == "/claude":
            self.sessions_view.show_claude_sessions()
        elif verb == "/detail":
            if arg and arg.isdigit():
                self.sessions_view.show_claude_detail(int(arg))
            else:
                log.write(render_tool("Usage: /detail <#>"))
        elif verb == "/launch":
            if arg and arg.isdigit():
                self.sessions_view.launch_claude(int(arg))
            else:
                log.write(render_tool("Usage: /launch <#>"))
        elif verb in ("/validate", "/refresh") and self.view == "config":
            self.config_view.handle_input(text)
        elif verb == "/clear":
            log.clear()
        elif verb in ("/quit", "/exit", "/q"):
            self.exit()
        else:
            log.write(render_tool(f"Unknown: {verb}. Type /help"))


def run_rich_tui(config: Config | None = None):
    app = RichTUIApp(config=config)
    app.run()
