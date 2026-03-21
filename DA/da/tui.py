"""DA TUI — Textual-based multi-session REPL with sidebar.

Sidebar has two tabs:
  - DA Sessions: sessions from DA's SQLite store
  - Claude Sessions: sessions from .claude directory, grouped as tree by working dir
"""

import json
import os
import uuid
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)
from textual.widgets.tree import TreeNode

from da import __version__
from da.config import load_config, Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore


# --- Claude session reader ---

def _decode_project_dir(dirname: str) -> str:
    """Convert encoded project dir name back to path. e.g. '-home-alex-CRAP' -> '/home/alex/CRAP'"""
    if dirname.startswith("D--"):
        # Windows path: D--Dev-CRAP -> D:\Dev\CRAP
        return dirname.replace("-", "\\", 1).replace("-", "\\")
    return "/" + dirname.replace("-", "/")


def _first_user_message(session_path: Path) -> str:
    """Extract first non-meta user message from a session JSONL as the name."""
    try:
        with open(session_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") == "user" and not d.get("isMeta"):
                    msg = d.get("message", {})
                    content = msg.get("content", "")
                    if isinstance(content, str) and len(content) > 3 and not content.startswith("<"):
                        return content[:60]
    except Exception:
        pass
    return session_path.stem[:12]


def _session_timestamp(session_path: Path) -> str:
    """Get timestamp from first entry."""
    try:
        with open(session_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    ts = d.get("timestamp", "")
                    if isinstance(ts, str) and "T" in ts:
                        return ts[:10]
                except (json.JSONDecodeError, Exception):
                    continue
    except Exception:
        pass
    return ""


def load_claude_sessions(claude_dir: str) -> dict[str, dict[str, list[dict]]]:
    """Load Claude Code sessions grouped by machine -> project -> sessions.

    Returns: {machine: {project_path: [{id, name, date, file}]}}
    """
    claude_path = Path(claude_dir)
    if not claude_path.exists():
        return {}

    result: dict[str, dict[str, list[dict]]] = {}

    for machine_dir in sorted(claude_path.iterdir()):
        if not machine_dir.is_dir():
            continue
        machine = machine_dir.name
        projects_dir = machine_dir / "projects"
        if not projects_dir.is_dir():
            continue

        machine_sessions: dict[str, list[dict]] = {}

        for proj_dir in sorted(projects_dir.iterdir()):
            if not proj_dir.is_dir():
                continue
            project_path = _decode_project_dir(proj_dir.name)

            sessions = []
            for sf in sorted(proj_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                if sf.name.startswith("."):
                    continue
                sessions.append({
                    "id": sf.stem,
                    "name": _first_user_message(sf),
                    "date": _session_timestamp(sf),
                    "file": str(sf),
                })
                if len(sessions) >= 20:  # cap per project
                    break

            if sessions:
                machine_sessions[project_path] = sessions

        if machine_sessions:
            result[machine] = machine_sessions

    return result


def load_claude_session_messages(session_file: str) -> list[dict]:
    """Load messages from a Claude Code session JSONL file."""
    messages = []
    try:
        with open(session_file, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                msg_type = d.get("type")
                msg = d.get("message", {})

                if msg_type == "user" and not d.get("isMeta"):
                    content = msg.get("content", "")
                    if isinstance(content, str) and len(content) > 1 and not content.startswith("<"):
                        messages.append({"role": "user", "content": content[:500]})

                elif msg_type == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block.get("type") == "tool_use":
                                    messages.append({"role": "tool", "content": block.get("name", "tool")})
                        if text_parts:
                            messages.append({"role": "assistant", "content": "\n".join(text_parts)[:2000]})
                    elif isinstance(content, str) and content:
                        messages.append({"role": "assistant", "content": content[:2000]})
    except Exception:
        pass
    return messages


# --- Session sidebar items ---

class DASessionItem(ListItem):
    """DA session entry."""

    def __init__(self, session_id: str, name: str, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.session_name = name

    def compose(self) -> ComposeResult:
        yield Label(f" {self.session_name[:30] or 'new session'}")


# --- Main App ---

class DAApp(App):
    """DA — DebilAgent TUI."""

    TITLE = "DA"
    SUB_TITLE = f"v{__version__}"

    CSS = """
    #sidebar {
        width: 34;
        dock: left;
        background: $surface;
        border-right: tall $primary;
    }
    #da-session-list {
        height: 1fr;
    }
    #claude-tree {
        height: 1fr;
    }
    #new-session-btn {
        margin: 0 1;
        text-align: center;
        color: $success;
        height: 1;
    }
    #chat-area {
        height: 1fr;
    }
    #chat-scroll {
        height: 1fr;
        padding: 0 1;
    }
    #prompt-input {
        width: 1fr;
    }
    #model-label {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    .user-msg {
        margin: 1 0 0 0;
        color: $success;
    }
    .assistant-msg {
        margin: 0 0 1 0;
    }
    .tool-msg {
        color: $text-muted;
    }
    TabPane {
        padding: 0;
    }
    #claude-panel {
        width: 1fr;
        display: none;
        border-left: tall $accent;
    }
    #claude-panel.visible {
        display: block;
    }
    #claude-panel-title {
        height: 1;
        padding: 0 1;
        text-style: bold;
        color: $accent;
        background: $surface;
    }
    #claude-output {
        height: 1fr;
        padding: 0 1;
    }
    #claude-panel-status {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+up", "prev_session", "Prev"),
        Binding("ctrl+down", "next_session", "Next"),
        Binding("ctrl+t", "toggle_tab", "Tab"),
    ]

    current_session_id: reactive[str] = reactive("")
    viewing_claude_session: reactive[bool] = reactive(False)

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
        self.claude_session_files: dict[str, str] = {}  # session_id -> file path
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                with TabbedContent(id="sidebar-tabs"):
                    with TabPane("DA", id="tab-da"):
                        yield ListView(id="da-session-list")
                        yield Static(" [Ctrl+N] New", id="new-session-btn")
                    with TabPane("Claude", id="tab-claude"):
                        yield Tree("Sessions", id="claude-tree")
            with Vertical(id="chat-area"):
                yield VerticalScroll(id="chat-scroll")
                yield Static("", id="model-label")
                yield Input(placeholder="Ask anything... (/ for commands)", id="prompt-input")
            with Vertical(id="claude-panel"):
                yield Static("[bold]Claude Code[/bold]", id="claude-panel-title")
                yield VerticalScroll(id="claude-output")
                yield Static("", id="claude-panel-status")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_da_sessions()
        self._load_claude_tree()
        da_list = self.query_one("#da-session-list", ListView)
        if da_list.children:
            da_list.index = 0
        else:
            self._create_new_session()
        self._update_model_label()

    def _refresh_da_sessions(self) -> None:
        da_list = self.query_one("#da-session-list", ListView)
        da_list.clear()
        for s in self.store.list_sessions(limit=50):
            da_list.append(DASessionItem(s["id"], s["name"]))

    @work(thread=True)
    def _load_claude_tree(self) -> None:
        """Load Claude sessions into tree (bg thread — can be slow)."""
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"
        data = load_claude_sessions(claude_dir)
        self.call_from_thread(self._populate_claude_tree, data)

    def _populate_claude_tree(self, data: dict) -> None:
        tree = self.query_one("#claude-tree", Tree)
        tree.clear()
        tree.root.expand()

        for machine, projects in sorted(data.items()):
            machine_node = tree.root.add(f"[bold]{machine}[/bold]", expand=False)
            for project_path, sessions in sorted(projects.items()):
                # Shorten project path for display
                short = project_path.split("/")[-1] or project_path.split("\\")[-1] or project_path
                proj_node = machine_node.add(f"[cyan]{short}[/cyan] ({len(sessions)})", expand=False)
                for s in sessions:
                    label = f"{s['date']} {s['name'][:35]}" if s['date'] else s['name'][:40]
                    leaf = proj_node.add_leaf(label)
                    leaf.data = s  # store session info
                    self.claude_session_files[s["id"]] = s["file"]

    def _create_new_session(self) -> None:
        sid = str(uuid.uuid4())
        self.store.create_session(sid, name="new session", project=os.getcwd())
        self.session_messages[sid] = []
        self._refresh_da_sessions()
        da_list = self.query_one("#da-session-list", ListView)
        da_list.index = 0
        self.viewing_claude_session = False
        self.current_session_id = sid

    def _update_model_label(self) -> None:
        label = self.query_one("#model-label", Static)
        mode = "read-only" if self.viewing_claude_session else self.cfg.model
        label.update(f" {mode} | {len(self.api_tools)} tools | /help")

    # --- Event handlers ---

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, DASessionItem):
            self.viewing_claude_session = False
            self.current_session_id = item.session_id
            self._update_model_label()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        if node.data and isinstance(node.data, dict) and "file" in node.data:
            sid = node.data["id"]
            self.viewing_claude_session = True
            # Load claude session messages if not cached
            if sid not in self.session_messages:
                msgs = load_claude_session_messages(node.data["file"])
                self.session_messages[sid] = msgs
            self.current_session_id = sid
            self._update_model_label()

    def watch_current_session_id(self, session_id: str) -> None:
        if not session_id:
            return
        if session_id not in self.session_messages:
            stored = self.store.get_messages(session_id, limit=100)
            self.session_messages[session_id] = stored
        self._render_chat()

    def _render_chat(self) -> None:
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.remove_children()
        msgs = self.session_messages.get(self.current_session_id, [])
        for m in msgs:
            role = m["role"]
            content = m["content"] if isinstance(m["content"], str) else str(m["content"])
            if role == "user":
                scroll.mount(Static(f"[bold green]> {content}[/bold green]", classes="user-msg"))
            elif role == "tool":
                scroll.mount(Static(f"[dim]  → {content}[/dim]", classes="tool-msg"))
            else:
                scroll.mount(Markdown(content, classes="assistant-msg"))
        scroll.scroll_end(animate=False)

    def _add_chat_msg(self, role: str, content: str) -> None:
        sid = self.current_session_id
        if sid not in self.session_messages:
            self.session_messages[sid] = []
        self.session_messages[sid].append({"role": role, "content": content})
        if not self.viewing_claude_session:
            self.store.add_message(sid, role, content)

        scroll = self.query_one("#chat-scroll", VerticalScroll)
        if role == "user":
            scroll.mount(Static(f"[bold green]> {content}[/bold green]", classes="user-msg"))
        elif role == "tool":
            scroll.mount(Static(f"[dim]  → {content}[/dim]", classes="tool-msg"))
        else:
            scroll.mount(Markdown(content, classes="assistant-msg"))
        scroll.scroll_end(animate=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        inp = self.query_one("#prompt-input", Input)
        inp.value = ""

        if not text:
            return

        if text.startswith("/"):
            self._handle_slash(text)
            return

        if self.viewing_claude_session:
            self._add_chat_msg("tool", "Claude sessions are read-only. Use Ctrl+N for a new DA session.")
            return

        if self.busy:
            self._add_chat_msg("tool", "Still thinking...")
            return

        # Update session name from first message
        msgs = self.session_messages.get(self.current_session_id, [])
        if not any(m["role"] == "user" for m in msgs):
            self.store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], self.current_session_id),
            )
            self.store.conn.commit()
            self._refresh_da_sessions()

        self._add_chat_msg("user", text)
        self._run_agent(text)

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
                self._add_chat_msg("tool", f"Model: {self.cfg.model}")
            elif len(parts) > 1:
                self.cfg.model = parts[1].strip()
                self._add_chat_msg("tool", f"Model: {self.cfg.model}")
            else:
                lines = [f"Current: {self.cfg.model}"]
                for a, m in MODELS.items():
                    lines.append(f"  /model {a} — {m}")
                self._add_chat_msg("tool", "\n".join(lines))
            self._update_model_label()
        elif cmd in ("/help", "/"):
            self._add_chat_msg("tool",
                "/model [name] — switch model\n"
                "/tools — list tools\n"
                "/hosts — list hosts\n"
                "/clear — clear chat\n"
                "Ctrl+N — new session\n"
                "Ctrl+T — toggle DA/Claude tab\n"
                "Ctrl+Q — quit"
            )
        elif cmd == "/tools":
            lines = [f"{t['name']:18s} {t['description'][:45]}" for t in ALL_TOOL_DEFS]
            self._add_chat_msg("tool", "\n".join(lines))
        elif cmd == "/hosts":
            lines = [f"{n:15s} {h.ssh} [{', '.join(h.roles)}]" for n, h in self.cfg.hosts.items()]
            self._add_chat_msg("tool", "\n".join(lines))
        elif cmd == "/clear":
            self.session_messages[self.current_session_id] = []
            self._render_chat()
        else:
            self._add_chat_msg("tool", f"Unknown: {cmd}. Type /help")

    @work(thread=True)
    def _run_agent(self, user_text: str) -> None:
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
                    self.call_from_thread(self._add_chat_msg, "assistant", "\n".join(text_parts))
                    break

                tool_results = []
                for tu in tool_uses:
                    self.call_from_thread(self._add_chat_msg, "tool", tu.name)
                    result = execute_tool(tu.name, tu.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": str(result),
                    })

                api_messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            self.call_from_thread(self._add_chat_msg, "assistant", f"**Error:** {e}")
        finally:
            self.busy = False

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
        else:
            tabs.active = "tab-da"


def run_tui(config: Config | None = None):
    """Launch the TUI app."""
    app = DAApp(config=config)
    app.run()
