"""DA TUI — Textual + Anthropic SDK.

Architecture:
  - Textual: RichLog for streamed output, Input for prompts
  - Anthropic SDK for agent loop in background workers
  - Sidebar: DA sessions (interactive) + Claude sessions (tree by machine/project)
  - Claude sessions copied to local .claude before resume
"""

import json
import os
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path

from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from da import __version__
from da.config import load_config, Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore


# --- Machine icon helper ---

# Windows hostnames (no .WSL suffix, paths start with D:\)
_WIN_MACHINES = {"ALEX-LAPTOP", "Alex-PC"}

def _machine_icon(name: str) -> str:
    """Return icon for machine type: Windows, WSL, or Linux."""
    if name.endswith(".WSL"):
        return "\U0001f427"  # 🐧 penguin (WSL)
    if name in _WIN_MACHINES:
        return "\u229e"      # ⊞ Windows logo approximation
    return "\U0001f5a5"      # 🖥 desktop (Linux server)

def _machine_label(name: str) -> str:
    """Pretty machine name with icon, strip .WSL suffix."""
    icon = _machine_icon(name)
    display = name.replace(".WSL", "")
    return f"{icon} {display}"


# --- Claude session helpers ---

def _decode_project_dir(dirname: str) -> str:
    """Convert encoded project dir back to path. e.g. '-home-alex-CRAP' -> '/home/alex/CRAP'"""
    if dirname.startswith("D--"):
        # Windows: D--Dev-CRAP -> D:\Dev\CRAP
        # First 'D--' is 'D:\', rest use '-' as separator
        rest = dirname[3:]  # after 'D--'
        parts = rest.split("-") if rest else []
        return "D:\\" + "\\".join(parts) if parts else "D:\\"
    # Unix: -home-alex-CRAP -> /home/alex/CRAP
    return dirname.replace("-", "/")


def _first_user_message(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "user" and not d.get("isMeta"):
                    msg = d.get("message", {})
                    c = msg.get("content", "")
                    if isinstance(c, str) and len(c) > 3 and not c.startswith("<"):
                        return c[:60]
    except Exception:
        pass
    return path.stem[:12]


def _session_timestamp(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    ts = d.get("timestamp", "")
                    if isinstance(ts, str) and "T" in ts:
                        return ts[:10]
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def load_claude_sessions(claude_dir: str) -> dict[str, dict[str, list[dict]]]:
    """machine -> project_path -> [{id, name, date, file}]"""
    cpath = Path(claude_dir)
    if not cpath.exists():
        return {}

    result: dict[str, dict[str, list[dict]]] = {}
    for mdir in sorted(cpath.iterdir()):
        if not mdir.is_dir():
            continue
        pdir = mdir / "projects"
        if not pdir.is_dir():
            continue

        msessions: dict[str, list[dict]] = {}
        for projd in sorted(pdir.iterdir()):
            if not projd.is_dir():
                continue
            proj_path = _decode_project_dir(projd.name)
            sessions = []
            for sf in sorted(projd.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                if sf.name.startswith("."):
                    continue
                sessions.append({
                    "id": sf.stem,
                    "name": _first_user_message(sf),
                    "date": _session_timestamp(sf),
                    "file": str(sf),
                    "project_dir": projd.name,
                    "machine_dir": mdir.name,
                })
                if len(sessions) >= 15:
                    break
            if sessions:
                msessions[proj_path] = sessions
        if msessions:
            result[mdir.name] = msessions
    return result


def load_claude_session_messages(session_file: str) -> list[dict]:
    """Parse a Claude Code JSONL into [{role, content}]."""
    messages = []
    try:
        with open(session_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                mtype = d.get("type")
                msg = d.get("message", {})
                if mtype == "user" and not d.get("isMeta"):
                    c = msg.get("content", "")
                    if isinstance(c, str) and len(c) > 1 and not c.startswith("<"):
                        messages.append({"role": "user", "content": c[:500]})
                elif mtype == "assistant":
                    c = msg.get("content", "")
                    if isinstance(c, list):
                        parts = []
                        for b in c:
                            if isinstance(b, dict):
                                if b.get("type") == "text":
                                    parts.append(b.get("text", ""))
                                elif b.get("type") == "tool_use":
                                    messages.append({"role": "tool", "content": b.get("name", "")})
                        if parts:
                            messages.append({"role": "assistant", "content": "\n".join(parts)[:2000]})
                    elif isinstance(c, str) and c:
                        messages.append({"role": "assistant", "content": c[:2000]})
    except Exception:
        pass
    return messages


def copy_session_to_local(session_info: dict) -> None:
    """Copy a remote session JSONL + subagents to the local .claude so 'claude --resume' works."""
    src = Path(session_info["file"])
    local_claude = Path.home() / ".claude"
    local_proj = local_claude / "projects" / session_info["project_dir"]
    local_proj.mkdir(parents=True, exist_ok=True)

    dest = local_proj / src.name
    if not dest.exists():
        shutil.copy2(src, dest)

    # Also copy subagents dir if it exists
    subagents_src = src.parent / src.stem / "subagents"
    if subagents_src.is_dir():
        subagents_dest = local_proj / src.stem / "subagents"
        if not subagents_dest.exists():
            shutil.copytree(subagents_src, subagents_dest)


# Machine name -> SSH host mapping
# Local machines don't need SSH, remote ones do
LOCAL_MACHINES = {"ALEX-LAPTOP", "ALEX-LAPTOP.WSL", "Alex-PC", "Alex-PC.WSL"}


def _machine_to_ssh(machine_dir: str, hosts: dict) -> str | None:
    """Map .claude machine directory name to SSH host. Returns None for local."""
    if machine_dir in LOCAL_MACHINES:
        return None
    # Check config hosts
    for name, hcfg in hosts.items():
        if machine_dir.lower() == name.lower():
            return hcfg.ssh
    # Fallback: try alex@machine_dir
    return f"alex@{machine_dir}"


def _get_wsl_distro() -> str:
    """Get current WSL distro name."""
    return os.environ.get("WSL_DISTRO_NAME", "Debian")


def launch_claude_session(session_info: dict, hosts: dict) -> str:
    """Launch claude --resume in a new Windows Terminal window.

    - Local WSL: wt.exe new-window -- wsl.exe -d DISTRO -- bash -lc 'cd DIR && claude --resume ID'
    - Remote:    wt.exe new-window -- wsl.exe -d DISTRO -- ssh -t HOST 'bash -lc "cd DIR && claude --resume ID"'

    Returns status message.
    """
    sid = session_info["id"]
    machine = session_info.get("machine_dir", "")
    project_path = _decode_project_dir(session_info.get("project_dir", ""))
    ssh_host = _machine_to_ssh(machine, hosts)
    distro = _get_wsl_distro()

    resume_cmd = f"cd {shlex.quote(project_path)} && exec claude --resume {shlex.quote(sid)}"

    try:
        if ssh_host:
            # Remote: wt -> wsl -> ssh -> bash -> claude
            subprocess.Popen([
                "wt.exe", "-w", "new",
                "wsl.exe", "-d", distro, "--",
                "ssh", "-t", ssh_host,
                f"bash -lc {shlex.quote(resume_cmd)}",
            ])
            return f"Launched on {ssh_host} in new terminal"
        elif project_path.startswith("/"):
            # Local WSL: wt -> wsl -> bash -> claude
            subprocess.Popen([
                "wt.exe", "-w", "new",
                "wsl.exe", "-d", distro, "--",
                "bash", "-lc", resume_cmd,
            ])
            return "Launched locally (WSL) in new terminal"
        else:
            # Windows local: wt -> cmd -> claude
            win_cmd = f'cd /d {project_path} && claude --resume {sid}'
            subprocess.Popen([
                "wt.exe", "-w", "new",
                "cmd.exe", "/k", win_cmd,
            ])
            return "Launched locally (Windows) in new terminal"
    except FileNotFoundError:
        return "wt.exe not found — not running in WSL with Windows Terminal?"
    except Exception as e:
        return f"Launch failed: {e}"


# --- Drag handle for resizable split ---

class DragHandle(Static):
    """Vertical drag handle between two panels. Drag with mouse or use Ctrl+Left/Right."""

    DEFAULT_CSS = """
    DragHandle {
        width: 1;
        height: 1fr;
        background: $primary;
        color: $text;
        content-align: center middle;
    }
    DragHandle:hover {
        background: $accent;
    }
    DragHandle.-dragging {
        background: $success;
    }
    """

    def __init__(self, target_id: str, min_width: int = 20, max_width: int = 120, **kwargs):
        super().__init__("┃", **kwargs)
        self.target_id = target_id
        self.min_width = min_width
        self.max_width = max_width
        self._dragging = False

    def on_mouse_down(self, event) -> None:
        self._dragging = True
        self.add_class("-dragging")
        self.capture_mouse()
        event.stop()

    def on_mouse_up(self, event) -> None:
        if self._dragging:
            self._dragging = False
            self.remove_class("-dragging")
            self.release_mouse()
            event.stop()

    def on_mouse_move(self, event) -> None:
        if self._dragging:
            # event.screen_x is the mouse X position on screen
            new_width = max(self.min_width, min(self.max_width, event.screen_x))
            try:
                target = self.app.query_one(f"#{self.target_id}")
                target.styles.width = new_width
            except Exception:
                pass
            event.stop()


# --- Menu item ---

class MenuItem(Static):
    """Clickable menu bar item."""

    def __init__(self, label: str, action: str, **kwargs):
        super().__init__(label, **kwargs)
        self.action_name = action

    def on_click(self) -> None:
        self.app.run_action(self.action_name)


# --- Sidebar items ---

class DASessionItem(ListItem):
    def __init__(self, session_id: str, name: str, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.session_name = name

    def compose(self) -> ComposeResult:
        yield Label(f" {self.session_name[:30] or 'new session'}")


# --- Main TUI ---

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


class DAApp(App):
    TITLE = "ДА"
    SUB_TITLE = f"v{__version__}"

    CSS = """
    #menu-bar {
        dock: top;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    .menu-item {
        width: auto;
        padding: 0 2;
        background: $accent;
        color: $text;
    }
    .menu-item:hover {
        background: $accent-lighten-2;
        text-style: bold;
    }
    #sidebar {
        width: 34;
        dock: left;
        background: $surface;
        border-right: tall $primary;
    }
    #da-session-list { height: 1fr; }
    #claude-tree {
        height: 1fr;
        overflow-x: auto;
    }
    #claude-table { height: 1fr; }
    #new-session-btn {
        margin: 0 1; text-align: center; color: $success; height: 1;
    }
    #chat-log {
        height: 1fr;
        padding: 0 1;
    }
    #prompt-input { width: 1fr; }
    #status-bar {
        dock: bottom; height: 1; padding: 0 1; color: $text-muted;
    }
    TabPane { padding: 0; }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+up", "prev_session", "Prev"),
        Binding("ctrl+down", "next_session", "Next"),
        Binding("ctrl+t", "toggle_tab", "Tab"),
        Binding("ctrl+d", "delete_session", "Del"),
        Binding("ctrl+o", "open_session", "Open"),
        Binding("ctrl+left", "shrink_sidebar", "◄", show=False),
        Binding("ctrl+right", "grow_sidebar", "►", show=False),
    ]

    current_session_id: reactive[str] = reactive("")
    viewing_claude: reactive[bool] = reactive(False)

    def __init__(self, config: Config | None = None):
        super().__init__()
        self.cfg = config or load_config()
        self.store = SessionStore(self.cfg.session.db_path)
        self.client = get_client(self.cfg)
        self.system_prompt = get_system_prompt(self.cfg)
        self.api_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in ALL_TOOL_DEFS
        ]
        self.session_messages: dict[str, list[dict]] = {}
        self.claude_session_info: dict[str, dict] = {}
        self.busy = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="menu-bar"):
            yield Static(" ДА ", classes="menu-item")
            yield MenuItem(" REPLs ", "open_session", classes="menu-item")
            yield MenuItem(" Manage Sessions ", "open_manager", classes="menu-item")
        with Horizontal():
            with Vertical(id="sidebar"):
                with TabbedContent(id="sidebar-tabs"):
                    with TabPane("ДА", id="tab-da"):
                        yield ListView(id="da-session-list")
                        yield Static(" [Ctrl+N] New", id="new-session-btn")
                    with TabPane("Tree", id="tab-claude"):
                        yield Tree("Sessions", id="claude-tree")
                    with TabPane("Table", id="tab-claude-table"):
                        yield DataTable(id="claude-table", cursor_type="row")
            yield DragHandle("sidebar")
            with Vertical():
                yield RichLog(id="chat-log", wrap=True, markup=True)
                yield Static("", id="status-bar")
                yield Input(placeholder="Ask anything... (/ for commands)", id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_da_sessions()
        self._load_claude_tree()
        da_list = self.query_one("#da-session-list", ListView)
        if da_list.children:
            da_list.index = 0
        else:
            self._create_new_session()
        self._update_status()

    # --- Session management ---

    def _refresh_da_sessions(self) -> None:
        da_list = self.query_one("#da-session-list", ListView)
        da_list.clear()
        for s in self.store.list_sessions(limit=50):
            da_list.append(DASessionItem(s["id"], s["name"]))

    def _create_new_session(self) -> None:
        sid = str(uuid.uuid4())
        self.store.create_session(sid, name="new session", project=os.getcwd())
        self.session_messages[sid] = []
        self._refresh_da_sessions()
        da_list = self.query_one("#da-session-list", ListView)
        da_list.index = 0
        self.viewing_claude = False
        self.current_session_id = sid

    def _update_status(self) -> None:
        bar = self.query_one("#status-bar", Static)
        if self.viewing_claude:
            bar.update(" [dim]Claude session (read-only) | Ctrl+N for new DA session[/dim]")
        else:
            bar.update(f" {self.cfg.model} | {len(self.api_tools)} tools | /help")

    @work(thread=True)
    def _load_claude_tree(self) -> None:
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"
        data = load_claude_sessions(claude_dir)
        self.call_from_thread(self._populate_tree, data)
        self.call_from_thread(self._populate_claude_table, data)

    def _populate_tree(self, data: dict) -> None:
        tree = self.query_one("#claude-tree", Tree)
        tree.clear()
        tree.root.expand()
        for machine, projects in sorted(data.items()):
            mnode = tree.root.add(f"[bold]{_machine_label(machine)}[/bold]", expand=False)
            for proj, sessions in sorted(projects.items()):
                short = proj.split("/")[-1] or proj.split("\\")[-1] or proj
                pnode = mnode.add(f"[cyan]{short}[/cyan] ({len(sessions)})", expand=False)
                for s in sessions:
                    label = f"{s['date']} {s['name']}" if s["date"] else s["name"]
                    leaf = pnode.add_leaf(label)
                    leaf.data = s
                    self.claude_session_info[s["id"]] = s

    def _populate_claude_table(self, data: dict) -> None:
        """Fill the Claude table with session stats. Sortable columns."""
        table = self.query_one("#claude-table", DataTable)
        table.clear(columns=True)
        table.sort_key = None
        table.add_column("Machine", key="machine")
        table.add_column("Project", key="project")
        table.add_column("#", key="count")
        table.add_column("First", key="first")
        table.add_column("Last", key="last")
        table.add_column("Latest session", key="name")

        for machine, projects in sorted(data.items()):
            for proj, sessions in sorted(projects.items()):
                short = proj.split("/")[-1] or proj.split("\\")[-1] or proj
                dates = [s["date"] for s in sessions if s.get("date")]
                first = min(dates) if dates else "—"
                last = max(dates) if dates else "—"
                latest_name = sessions[0]["name"] if sessions else "—"
                table.add_row(
                    _machine_label(machine), short, str(len(sessions)),
                    first, last, latest_name,
                    key=f"{machine}:{proj}",
                )
                for s in sessions:
                    self.claude_session_info[s["id"]] = s

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Sort table by clicked column."""
        table = self.query_one("#claude-table", DataTable)
        table.sort(event.column_key)

    # --- Event handlers ---

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Claude table row selection — show project sessions."""
        key = str(event.row_key.value)
        if ":" in key:
            # Claude table row — show sessions for this project
            machine, proj = key.split(":", 1)
            sessions = [s for s in self.claude_session_info.values()
                        if s.get("machine_dir") == machine
                        and _decode_project_dir(s.get("project_dir", "")) == proj]
            if sessions:
                # Show first session
                s = sessions[0]
                self.viewing_claude = True
                if s["id"] not in self.session_messages:
                    msgs = load_claude_session_messages(s["file"])
                    self.session_messages[s["id"]] = msgs
                self.current_session_id = s["id"]
                self._update_status()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, DASessionItem):
            self.viewing_claude = False
            self.current_session_id = item.session_id
            self._update_status()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data and isinstance(node.data, dict) and "file" in node.data:
            sid = node.data["id"]
            self.viewing_claude = True

            # Copy session to local .claude so 'claude --resume' would work
            try:
                copy_session_to_local(node.data)
            except Exception:
                pass

            if sid not in self.session_messages:
                msgs = load_claude_session_messages(node.data["file"])
                self.session_messages[sid] = msgs
            self.current_session_id = sid
            self._update_status()

    def watch_current_session_id(self, session_id: str) -> None:
        if not session_id:
            return
        if session_id not in self.session_messages:
            stored = self.store.get_messages(session_id, limit=100)
            self.session_messages[session_id] = stored
        self._render_log()

    def _render_log(self) -> None:
        """Render current session into RichLog."""
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        msgs = self.session_messages.get(self.current_session_id, [])
        if not msgs:
            log.write(Text(BANNER, style="bold cyan"))
            log.write(Text(f"  v{__version__} | {self.cfg.model} | {len(self.api_tools)} tools", style="dim"))
            log.write(Text("  type /help or Ctrl+C to quit\n", style="dim"))
        for m in msgs:
            role = m["role"]
            content = m["content"] if isinstance(m["content"], str) else str(m["content"])
            if role == "user":
                log.write(Text(f"> {content}", style="bold green"))
            elif role == "tool":
                log.write(Text(f"  → {content}", style="dim"))
            else:
                log.write(content)
                log.write("")  # blank line after assistant

    def _log_msg(self, role: str, content: str) -> None:
        """Append message to current session and log widget."""
        sid = self.current_session_id
        if sid not in self.session_messages:
            self.session_messages[sid] = []
        self.session_messages[sid].append({"role": role, "content": content})
        if not self.viewing_claude:
            self.store.add_message(sid, role, content)

        log = self.query_one("#chat-log", RichLog)
        if role == "user":
            log.write(Text(f"> {content}", style="bold green"))
        elif role == "tool":
            log.write(Text(f"  → {content}", style="dim"))
        else:
            log.write(content)
            log.write("")

    # --- Input handling ---

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        inp = self.query_one("#prompt-input", Input)
        inp.value = ""

        if not text:
            return

        if text.startswith("/"):
            self._handle_slash(text)
            return

        if self.viewing_claude:
            self._log_msg("tool", "Claude sessions are read-only. Ctrl+N for new DA session.")
            return

        if self.busy:
            self._log_msg("tool", "Still thinking...")
            return

        # Name session from first user message
        msgs = self.session_messages.get(self.current_session_id, [])
        if not any(m["role"] == "user" for m in msgs):
            self.store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], self.current_session_id),
            )
            self.store.conn.commit()
            self._refresh_da_sessions()

        self._log_msg("user", text)
        self._run_agent()

    def _handle_slash(self, text: str) -> None:
        parts = text.split(None, 1)
        cmd = parts[0].lower()
        MODELS = {
            "opus": "claude-opus-4-6",
            "sonnet": "claude-sonnet-4-6",
            "haiku": "claude-haiku-4-5-20251001",
        }
        if cmd == "/model":
            if len(parts) > 1 and parts[1].strip().lower() in MODELS:
                self.cfg.model = MODELS[parts[1].strip().lower()]
                self._log_msg("tool", f"Model: {self.cfg.model}")
            elif len(parts) > 1:
                self.cfg.model = parts[1].strip()
                self._log_msg("tool", f"Model: {self.cfg.model}")
            else:
                lines = [f"Current: {self.cfg.model}"]
                for a, m in MODELS.items():
                    lines.append(f"  /model {a} — {m}")
                self._log_msg("tool", "\n".join(lines))
            self._update_status()
        elif cmd in ("/help", "/"):
            self._log_msg("tool",
                "/model [name] — switch model\n"
                "/tools — list tools\n"
                "/hosts — list hosts\n"
                "/sessions — DA session list with stats\n"
                "/stats — current session stats\n"
                "/detail — detailed view of current Claude session\n"
                "/delete — delete current DA session\n"
                "/launch — open Claude session in new terminal\n"
                "/repl — open current DA session in REPL\n"
                "/manage — open session manager\n"
                "/move [path] — move Claude sessions folder\n"
                "/clear — clear log\n"
                "Ctrl+N — new | Ctrl+D — del | Ctrl+O — repl | Ctrl+L — launch | Ctrl+T — tab | Ctrl+Q — quit"
            )
        elif cmd == "/tools":
            lines = [f"{t['name']:18s} {t['description'][:45]}" for t in ALL_TOOL_DEFS]
            self._log_msg("tool", "\n".join(lines))
        elif cmd == "/hosts":
            lines = [f"{n:15s} {h.ssh} [{', '.join(h.roles)}]" for n, h in self.cfg.hosts.items()]
            self._log_msg("tool", "\n".join(lines))
        elif cmd == "/sessions":
            self._show_sessions_detail()
        elif cmd == "/stats":
            self._show_current_stats()
        elif cmd == "/delete":
            self._do_delete_session()
        elif cmd == "/launch":
            self._do_launch_claude()
        elif cmd == "/repl":
            self._do_open_repl()
        elif cmd == "/detail":
            self._show_session_detail()
        elif cmd == "/manage":
            self._do_open_manager()
        elif cmd == "/move":
            dest = parts[1].strip() if len(parts) > 1 else ""
            self._move_claude_sessions(dest)
        elif cmd == "/clear":
            self.session_messages[self.current_session_id] = []
            self._render_log()
        else:
            self._log_msg("tool", f"Unknown: {cmd}. Type /help")

    # --- Agent loop ---

    @work(thread=True)
    def _run_agent(self) -> None:
        self.busy = True
        sid = self.current_session_id

        api_messages: list[dict] = []
        for m in self.session_messages.get(sid, []):
            if m["role"] in ("user", "assistant"):
                api_messages.append({"role": m["role"], "content": m["content"]})

        try:
            for _ in range(20):
                response = call_agent(
                    self.client, self.cfg, self.system_prompt, api_messages, self.api_tools
                )

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

                api_messages.append({"role": "assistant", "content": assistant_content})

                if not tool_uses:
                    self.call_from_thread(self._log_msg, "assistant", "\n".join(text_parts))
                    break

                tool_results = []
                for tu in tool_uses:
                    self.call_from_thread(self._log_msg, "tool", tu.name)
                    result = execute_tool(tu.name, tu.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": str(result),
                    })

                api_messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            self.call_from_thread(self._log_msg, "assistant", f"**Error:** {e}")
        finally:
            self.busy = False

    # --- Actions ---

    def action_new_session(self) -> None:
        self._create_new_session()

    def action_prev_session(self) -> None:
        sl = self.query_one("#da-session-list", ListView)
        if sl.index is not None and sl.index > 0:
            sl.index -= 1

    def action_next_session(self) -> None:
        sl = self.query_one("#da-session-list", ListView)
        if sl.index is not None and sl.index < len(sl.children) - 1:
            sl.index += 1

    def action_toggle_tab(self) -> None:
        tabs = self.query_one("#sidebar-tabs", TabbedContent)
        if tabs.active == "tab-da":
            tabs.active = "tab-claude"
        elif tabs.active == "tab-claude":
            tabs.active = "tab-claude-table"
        else:
            tabs.active = "tab-da"

    def action_shrink_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Vertical)
        current = sidebar.styles.width
        w = current.value if hasattr(current, "value") else 34
        sidebar.styles.width = max(20, int(w) - 5)

    def action_grow_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Vertical)
        current = sidebar.styles.width
        w = current.value if hasattr(current, "value") else 34
        sidebar.styles.width = min(120, int(w) + 5)

    def action_delete_session(self) -> None:
        self._do_delete_session()

    def action_open_session(self) -> None:
        """Open current session — REPL for DA, new terminal for Claude."""
        if self.viewing_claude:
            self._do_launch_claude()
        else:
            self._do_open_repl()

    def action_open_manager(self) -> None:
        self._do_open_manager()

    def _do_open_repl(self) -> None:
        """Suspend TUI, open current DA session in REPL, then resume."""
        sid = self.current_session_id
        if not sid or self.viewing_claude:
            self._log_msg("tool", "Select a DA session first.")
            return

        import sys

        with self.suspend():
            subprocess.run(
                [sys.executable, "-m", "da", "repl", "--session", sid],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

        # Reload messages that may have been added in the REPL
        stored = self.store.get_messages(sid, limit=100)
        self.session_messages[sid] = stored
        self._render_log()
        self._refresh_da_sessions()

    def _do_open_manager(self) -> None:
        """Suspend TUI, open session manager, then resume."""
        import sys

        with self.suspend():
            subprocess.run(
                [sys.executable, "-m", "da", "manage"],
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

        # Reload after manager may have changed sessions
        self._refresh_da_sessions()
        self._load_claude_tree()
        if self.current_session_id:
            stored = self.store.get_messages(self.current_session_id, limit=100)
            self.session_messages[self.current_session_id] = stored
            self._render_log()

    def _do_launch_claude(self) -> None:
        """Launch current Claude session in a new Windows Terminal window."""
        sid = self.current_session_id
        if not sid or not self.viewing_claude:
            self._log_msg("tool", "Select a Claude session first (Claude tab).")
            return
        info = self.claude_session_info.get(sid)
        if not info:
            self._log_msg("tool", f"No session info for {sid[:12]}")
            return
        # Copy session locally first
        try:
            copy_session_to_local(info)
        except Exception:
            pass
        result = launch_claude_session(info, {n: h for n, h in self.cfg.hosts.items()})
        self._log_msg("tool", result)

    def _do_delete_session(self) -> None:
        """Delete current session — DA or Claude."""
        sid = self.current_session_id
        if not sid:
            self._log_msg("tool", "No session selected.")
            return

        if self.viewing_claude:
            # Delete Claude session files
            info = self.claude_session_info.get(sid)
            if not info:
                self._log_msg("tool", "No session info found.")
                return
            fpath = Path(info["file"])
            session_dir = fpath.parent / fpath.stem
            name = info.get("name", sid[:12])
            try:
                fpath.unlink(missing_ok=True)
                if session_dir.is_dir():
                    import shutil
                    shutil.rmtree(session_dir)
                self.session_messages.pop(sid, None)
                self.claude_session_info.pop(sid, None)
                self._log_msg("tool", f"Deleted Claude session: {name}")
                self._load_claude_tree()
            except Exception as e:
                self._log_msg("tool", f"Delete failed: {e}")
        else:
            # Delete DA session
            name = ""
            for m in self.session_messages.get(sid, []):
                if m["role"] == "user":
                    name = m["content"][:40]
                    break
            self.store.delete_session(sid)
            self.session_messages.pop(sid, None)
            self._refresh_da_sessions()
            self._log_msg("tool", f"Deleted DA session: {name or sid[:12]}")
            da_list = self.query_one("#da-session-list", ListView)
            if da_list.children:
                da_list.index = 0
            else:
                self._create_new_session()

    def _show_sessions_detail(self) -> None:
        """Show detailed session list with stats."""
        import datetime
        sessions = self.store.list_sessions_detailed(limit=30)
        if not sessions:
            self._log_msg("tool", "No sessions.")
            return

        lines = ["Sessions:"]
        lines.append(f"{'ID':>12s}  {'Messages':>4s}  {'Updated':>16s}  {'Name'}")
        lines.append("-" * 70)
        for s in sessions:
            ts = datetime.datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M") if s["updated_at"] else "?"
            sid = s["id"][:12]
            name = s["name"][:35] or "—"
            mc = str(s["msg_count"])
            active = " *" if s["id"] == self.current_session_id else ""
            lines.append(f"{sid}  {mc:>4s}  {ts}  {name}{active}")
        lines.append(f"\nTotal: {len(sessions)} sessions")
        self._log_msg("tool", "\n".join(lines))

    def _show_current_stats(self) -> None:
        """Show stats for current session using Rich Table."""
        import datetime
        from rich.table import Table
        from rich.panel import Panel

        sid = self.current_session_id
        log = self.query_one("#chat-log", RichLog)

        if self.viewing_claude:
            self._show_session_detail()
            return

        stats = self.store.get_session_stats(sid)
        if not stats:
            self._log_msg("tool", "No stats available.")
            return

        created = datetime.datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M") if stats["created_at"] else "?"
        updated = datetime.datetime.fromtimestamp(stats["updated_at"]).strftime("%Y-%m-%d %H:%M") if stats["updated_at"] else "?"

        t = Table(show_header=False, box=None, pad_edge=False, show_edge=False)
        t.add_column("key", style="bold cyan", width=14, no_wrap=True)
        t.add_column("val")
        t.add_row("Name", stats["name"] or "—")
        t.add_row("ID", sid[:12])
        t.add_row("Project", stats.get("project", "—"))
        t.add_row("Created", created)
        t.add_row("Updated", updated)
        t.add_row("Messages", str(stats["total_messages"]))
        for role, count in sorted(stats["message_counts"].items()):
            t.add_row(f"  {role}", str(count))
        log.write(Panel(t, title="DA Session", border_style="green"))

    def _show_session_detail(self) -> None:
        """Show detailed view of current session with Rich Table."""
        from rich.table import Table
        from rich.panel import Panel

        sid = self.current_session_id
        info = self.claude_session_info.get(sid)
        msgs = self.session_messages.get(sid, [])

        log = self.query_one("#chat-log", RichLog)

        if info:
            fpath = Path(info["file"])
            fsize = fpath.stat().st_size if fpath.exists() else 0
            machine = info.get("machine_dir", "?")
            project = _decode_project_dir(info.get("project_dir", "?"))

            subagent_dir = fpath.parent / fpath.stem / "subagents"
            subagent_count = len(list(subagent_dir.glob("*.jsonl"))) if subagent_dir.is_dir() else 0
            tool_results_dir = fpath.parent / fpath.stem / "tool-results"
            tool_result_count = len(list(tool_results_dir.iterdir())) if tool_results_dir.is_dir() else 0

            roles: dict[str, int] = {}
            for m in msgs:
                roles[m["role"]] = roles.get(m["role"], 0) + 1

            local_path = Path.home() / ".claude" / "projects" / info.get("project_dir", "") / fpath.name

            # Info table
            t = Table(show_header=False, box=None, pad_edge=False, show_edge=False)
            t.add_column("key", style="bold cyan", width=14, no_wrap=True)
            t.add_column("val")
            t.add_row("ID", sid[:12])
            t.add_row("Machine", machine)
            t.add_row("Project", project)
            t.add_row("Date", info.get("date", "?"))
            t.add_row("Size", f"{fsize:,} bytes")
            t.add_row("Messages", str(len(msgs)))
            for r, c in sorted(roles.items()):
                t.add_row(f"  {r}", str(c))
            t.add_row("Subagents", str(subagent_count))
            t.add_row("Tool results", str(tool_result_count))
            t.add_row("Local copy", "[green]yes[/green]" if local_path.exists() else "[dim]no[/dim]")

            log.write(Panel(t, title="Claude Session", border_style="cyan"))
            log.write(Text(info.get("name", ""), style="italic"))
        else:
            self._show_current_stats()

    def _move_claude_sessions(self, dest: str) -> None:
        """Move the Claude sessions folder to a new location and update config."""
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"

        if not dest:
            lines = [
                f"Current Claude sessions folder: {claude_dir}",
                "",
                "Usage: /move /new/path/to/.claude",
                "",
                "This will:",
                "  1. Copy all sessions to the new location",
                "  2. Update config to point to new location",
                "  3. Reload the session tree",
            ]
            self._log_msg("tool", "\n".join(lines))
            return

        dest_path = Path(dest).expanduser()
        src_path = Path(claude_dir)

        if not src_path.exists():
            self._log_msg("tool", f"Source not found: {claude_dir}")
            return

        if dest_path.exists() and list(dest_path.iterdir()):
            self._log_msg("tool", f"Destination not empty: {dest}. Merging...")

        self._log_msg("tool", f"Moving {claude_dir} -> {dest}...")
        self._do_move_sessions(str(src_path), str(dest_path))

    @work(thread=True)
    def _do_move_sessions(self, src: str, dest: str) -> None:
        """Move sessions in background thread."""
        try:
            src_path = Path(src)
            dest_path = Path(dest)
            dest_path.mkdir(parents=True, exist_ok=True)

            copied = 0
            for item in src_path.iterdir():
                target = dest_path / item.name
                if item.is_dir() and not target.exists():
                    shutil.copytree(item, target)
                    copied += 1
                elif item.is_file() and not target.exists():
                    shutil.copy2(item, target)
                    copied += 1

            self.cfg.claude_history = dest
            self.call_from_thread(self._log_msg, "tool",
                f"Moved {copied} items to {dest}\nConfig updated. Reloading tree...")
            self.call_from_thread(self._load_claude_tree)

        except Exception as e:
            self.call_from_thread(self._log_msg, "tool", f"Move failed: {e}")


def run_tui(config: Config | None = None):
    app = DAApp(config=config)
    app.run()
