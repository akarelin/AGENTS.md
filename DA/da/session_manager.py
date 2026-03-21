"""Session Manager TUI — browse, rename, copy, move, delete sessions.

Covers both DA sessions (SQLite) and Claude sessions (.claude directory).
Launch via: da manage
"""

import datetime
import json
import shutil
from pathlib import Path

from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from da import __version__
from da.config import load_config, Config
from da.session import SessionStore
from da.tui import (
    _decode_project_dir,
    _first_user_message,
    _session_timestamp,
    load_claude_sessions,
    copy_session_to_local,
)


def _ts(t: float | None) -> str:
    if not t:
        return "—"
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


class SessionManagerApp(App):
    TITLE = "ДА Session Manager"
    SUB_TITLE = f"v{__version__}"

    CSS = """
    #left-panel {
        width: 2fr;
    }
    #right-panel {
        width: 1fr;
        border-left: tall $primary;
    }
    #da-table {
        height: 1fr;
    }
    #claude-tree {
        height: 1fr;
    }
    #detail-log {
        height: 1fr;
        padding: 0 1;
    }
    #cmd-input {
        width: 1fr;
    }
    #status {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    TabPane { padding: 0; }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+r", "rename", "Rename"),
        Binding("ctrl+d", "delete", "Delete"),
        Binding("ctrl+c", "copy_session", "Copy"),
        Binding("ctrl+m", "move_session", "Move"),
        Binding("ctrl+s", "global_stats", "Stats"),
        Binding("ctrl+t", "toggle_tab", "Tab"),
    ]

    selected_da_session: reactive[str] = reactive("")
    selected_claude_session: reactive[dict] = reactive({})

    def __init__(self, config: Config | None = None):
        super().__init__()
        self.cfg = config or load_config()
        self.store = SessionStore(self.cfg.session.db_path)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-panel"):
                with TabbedContent(id="tabs"):
                    with TabPane("ДА Sessions", id="tab-da"):
                        yield DataTable(id="da-table", cursor_type="row")
                    with TabPane("Claude Sessions", id="tab-claude"):
                        yield Tree("Claude", id="claude-tree")
            with Vertical(id="right-panel"):
                yield RichLog(id="detail-log", wrap=True, markup=True)
                yield Input(placeholder="Command: rename <name> | copy <path> | move <path>", id="cmd-input")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_da_table()
        self._load_claude_tree()
        self._update_status()
        self._show_global_stats()

    # --- DA sessions table ---

    def _load_da_table(self) -> None:
        table = self.query_one("#da-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Name", "Project", "Msgs", "Updated")
        sessions = self.store.list_sessions_detailed(limit=100)
        for s in sessions:
            table.add_row(
                s["id"][:12],
                (s["name"] or "—")[:30],
                (s["project"] or "—").split("/")[-1][:15],
                str(s["msg_count"]),
                _ts(s["updated_at"]),
                key=s["id"],
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        sid = str(event.row_key.value)
        self.selected_da_session = sid
        self.selected_claude_session = {}
        self._show_da_detail(sid)

    def _show_da_detail(self, sid: str) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        stats = self.store.get_session_stats(sid)
        if not stats:
            log.write("Session not found.")
            return

        log.write(Text("DA Session Detail", style="bold"))
        log.write(f"{'─' * 40}")
        log.write(f"ID:       {stats['id']}")
        log.write(f"Name:     {stats['name'] or '—'}")
        log.write(f"Project:  {stats['project'] or '—'}")
        log.write(f"Agent:    {stats['agent'] or '—'}")
        log.write(f"Created:  {_ts(stats['created_at'])}")
        log.write(f"Updated:  {_ts(stats['updated_at'])}")
        log.write(f"Messages: {stats['total_messages']}")
        for role, count in sorted(stats["message_counts"].items()):
            log.write(f"  {role}: {count}")
        log.write(f"{'─' * 40}")
        log.write("")
        log.write(Text("Commands:", style="dim"))
        log.write(Text("  rename <name>     — rename session", style="dim"))
        log.write(Text("  delete            — delete session", style="dim"))
        log.write(Text("  Ctrl+R/D          — shortcuts", style="dim"))

    # --- Claude sessions tree ---

    def _load_claude_tree(self) -> None:
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"
        data = load_claude_sessions(claude_dir)
        tree = self.query_one("#claude-tree", Tree)
        tree.clear()
        tree.root.expand()

        total_sessions = 0
        for machine, projects in sorted(data.items()):
            mcount = sum(len(s) for s in projects.values())
            total_sessions += mcount
            mnode = tree.root.add(f"[bold]{machine}[/bold] ({mcount})", expand=False)
            for proj, sessions in sorted(projects.items()):
                short = proj.split("/")[-1] or proj.split("\\")[-1] or proj
                pnode = mnode.add(f"[cyan]{short}[/cyan] ({len(sessions)})", expand=False)
                for s in sessions:
                    label = f"{s['date']} {s['name'][:30]}" if s["date"] else s["name"][:35]
                    leaf = pnode.add_leaf(label)
                    leaf.data = s

        self._update_status(f"Claude: {total_sessions} sessions across {len(data)} machines")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data and isinstance(node.data, dict) and "file" in node.data:
            self.selected_claude_session = node.data
            self.selected_da_session = ""
            self._show_claude_detail(node.data)

    def _show_claude_detail(self, info: dict) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()

        fpath = Path(info["file"])
        fsize = fpath.stat().st_size if fpath.exists() else 0
        machine = info.get("machine_dir", "?")
        project = _decode_project_dir(info.get("project_dir", "?"))

        # Count artifacts
        session_dir = fpath.parent / fpath.stem
        subagent_count = len(list((session_dir / "subagents").glob("*.jsonl"))) if (session_dir / "subagents").is_dir() else 0
        tool_result_count = len(list((session_dir / "tool-results").iterdir())) if (session_dir / "tool-results").is_dir() else 0
        total_dir_size = sum(f.stat().st_size for f in session_dir.rglob("*") if f.is_file()) if session_dir.is_dir() else 0

        # Count messages by type
        roles: dict[str, int] = {}
        total_msgs = 0
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        d = json.loads(line.strip())
                        t = d.get("type", "")
                        if t in ("user", "assistant"):
                            roles[t] = roles.get(t, 0) + 1
                            total_msgs += 1
                    except Exception:
                        pass
        except Exception:
            pass

        # Check local copy
        local_path = Path.home() / ".claude" / "projects" / info.get("project_dir", "") / fpath.name
        has_local = local_path.exists()

        log.write(Text("Claude Session Detail", style="bold"))
        log.write(f"{'─' * 45}")
        log.write(f"ID:            {info['id']}")
        log.write(f"Machine:       {machine}")
        log.write(f"Project:       {project}")
        log.write(f"Date:          {info.get('date', '?')}")
        log.write(f"First message: {info.get('name', '?')}")
        log.write(f"{'─' * 45}")
        log.write(f"File:          {info['file']}")
        log.write(f"JSONL size:    {fsize:,} bytes")
        log.write(f"Total size:    {fsize + total_dir_size:,} bytes")
        log.write(f"Messages:      {total_msgs}")
        for r, c in sorted(roles.items()):
            log.write(f"  {r}: {c}")
        log.write(f"Subagents:     {subagent_count}")
        log.write(f"Tool results:  {tool_result_count}")
        log.write(f"{'─' * 45}")
        log.write(f"Local copy:    {'[green]yes[/green]' if has_local else '[dim]no[/dim]'}")
        if has_local:
            log.write(f"  {local_path}")
        log.write("")
        log.write(Text("Commands:", style="dim"))
        log.write(Text("  copy <path>     — copy session folder to path", style="dim"))
        log.write(Text("  copy local      — copy to local .claude", style="dim"))
        log.write(Text("  move <path>     — move session folder to path", style="dim"))

    # --- Command input ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        inp = self.query_one("#cmd-input", Input)
        inp.value = ""
        if not text:
            return

        parts = text.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "rename":
            self._cmd_rename(arg)
        elif cmd == "delete":
            self._cmd_delete()
        elif cmd == "copy":
            self._cmd_copy(arg)
        elif cmd == "move":
            self._cmd_move(arg)
        elif cmd == "stats":
            self._show_global_stats()
        elif cmd == "help":
            self._show_help()
        else:
            self._log(f"Unknown: {cmd}. Type 'help'")

    def _log(self, msg: str) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.write(msg)

    def _cmd_rename(self, new_name: str) -> None:
        if not self.selected_da_session:
            self._log("Select a DA session to rename.")
            return
        if not new_name:
            self._log("Usage: rename <new name>")
            return
        self.store.rename_session(self.selected_da_session, new_name)
        self._log(f"Renamed to: {new_name}")
        self._load_da_table()

    def _cmd_delete(self) -> None:
        if self.selected_da_session:
            sid = self.selected_da_session
            self.store.delete_session(sid)
            self._log(f"Deleted DA session {sid[:12]}")
            self.selected_da_session = ""
            self._load_da_table()
        elif self.selected_claude_session:
            fpath = Path(self.selected_claude_session["file"])
            session_dir = fpath.parent / fpath.stem
            try:
                fpath.unlink(missing_ok=True)
                if session_dir.is_dir():
                    shutil.rmtree(session_dir)
                self._log(f"Deleted Claude session files")
                self._load_claude_tree()
            except Exception as e:
                self._log(f"Delete failed: {e}")
        else:
            self._log("Select a session first.")

    def _cmd_copy(self, dest: str) -> None:
        if not self.selected_claude_session:
            self._log("Select a Claude session to copy.")
            return

        info = self.selected_claude_session
        if dest.lower() == "local":
            try:
                copy_session_to_local(info)
                self._log("Copied to local .claude")
                # Refresh detail
                self._show_claude_detail(info)
            except Exception as e:
                self._log(f"Copy failed: {e}")
            return

        if not dest:
            self._log("Usage: copy <path> | copy local")
            return

        src = Path(info["file"])
        dest_path = Path(dest).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(src, dest_path / src.name)
            # Copy session dir if exists
            session_dir = src.parent / src.stem
            if session_dir.is_dir():
                dest_session = dest_path / src.stem
                if not dest_session.exists():
                    shutil.copytree(session_dir, dest_session)
            self._log(f"Copied to {dest_path}")
        except Exception as e:
            self._log(f"Copy failed: {e}")

    def _cmd_move(self, dest: str) -> None:
        if not self.selected_claude_session:
            self._log("Select a Claude session to move.")
            return
        if not dest:
            self._log("Usage: move <path>")
            return

        info = self.selected_claude_session
        src = Path(info["file"])
        dest_path = Path(dest).expanduser()
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(src), str(dest_path / src.name))
            session_dir = src.parent / src.stem
            if session_dir.is_dir():
                shutil.move(str(session_dir), str(dest_path / src.stem))
            self._log(f"Moved to {dest_path}")
            self._load_claude_tree()
        except Exception as e:
            self._log(f"Move failed: {e}")

    def _show_global_stats(self) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()

        # DA stats
        da_stats = self.store.get_global_stats()
        log.write(Text("DA Global Stats", style="bold"))
        log.write(f"{'─' * 40}")
        log.write(f"Sessions:  {da_stats['total_sessions']}")
        log.write(f"Messages:  {da_stats['total_messages']}")
        if da_stats["oldest"]:
            log.write(f"Oldest:    {_ts(da_stats['oldest'])}")
            log.write(f"Newest:    {_ts(da_stats['newest'])}")
        if da_stats["roles"]:
            log.write("By role:")
            for r, c in sorted(da_stats["roles"].items()):
                log.write(f"  {r}: {c}")
        if da_stats["projects"]:
            log.write("Top projects:")
            for p, c in da_stats["projects"].items():
                short = p.split("/")[-1] if p else "—"
                log.write(f"  {short}: {c}")

        # Claude stats
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"
        cpath = Path(claude_dir)
        if cpath.exists():
            machines = [d.name for d in cpath.iterdir() if d.is_dir() and (d / "projects").is_dir()]
            total_jsonl = sum(1 for _ in cpath.glob("*/projects/*/*.jsonl"))
            total_size = sum(f.stat().st_size for f in cpath.glob("*/projects/*/*.jsonl"))

            log.write("")
            log.write(Text("Claude Global Stats", style="bold"))
            log.write(f"{'─' * 40}")
            log.write(f"Source:    {claude_dir}")
            log.write(f"Machines:  {len(machines)} ({', '.join(machines[:5])})")
            log.write(f"Sessions:  {total_jsonl}")
            log.write(f"Total size: {total_size:,} bytes ({total_size // 1024 // 1024} MB)")

    def _show_help(self) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        log.write(Text("Session Manager Commands", style="bold"))
        log.write(f"{'─' * 40}")
        log.write("  rename <name>  — rename DA session")
        log.write("  delete         — delete selected session")
        log.write("  copy <path>    — copy Claude session to path")
        log.write("  copy local     — copy to local .claude")
        log.write("  move <path>    — move Claude session to path")
        log.write("  stats          — global statistics")
        log.write("  help           — this help")
        log.write("")
        log.write(Text("Keyboard:", style="bold"))
        log.write("  Ctrl+R — rename")
        log.write("  Ctrl+D — delete")
        log.write("  Ctrl+C — copy")
        log.write("  Ctrl+M — move")
        log.write("  Ctrl+S — stats")
        log.write("  Ctrl+T — toggle DA/Claude tab")
        log.write("  Ctrl+Q — quit")

    def _update_status(self, extra: str = "") -> None:
        bar = self.query_one("#status", Static)
        da_count = self.store.list_sessions_detailed(limit=1000)
        msg = f" DA: {len(da_count)} sessions"
        if extra:
            msg += f" | {extra}"
        bar.update(msg)

    # --- Actions ---

    def action_rename(self) -> None:
        if self.selected_da_session:
            inp = self.query_one("#cmd-input", Input)
            inp.value = "rename "
            inp.focus()

    def action_delete(self) -> None:
        self._cmd_delete()

    def action_copy_session(self) -> None:
        if self.selected_claude_session:
            inp = self.query_one("#cmd-input", Input)
            inp.value = "copy "
            inp.focus()

    def action_move_session(self) -> None:
        if self.selected_claude_session:
            inp = self.query_one("#cmd-input", Input)
            inp.value = "move "
            inp.focus()

    def action_global_stats(self) -> None:
        self._show_global_stats()

    def action_toggle_tab(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        if tabs.active == "tab-da":
            tabs.active = "tab-claude"
        else:
            tabs.active = "tab-da"


def run_manager(config: Config | None = None):
    app = SessionManagerApp(config=config)
    app.run()
