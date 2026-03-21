"""DA TUI — Textual-based multi-session REPL with sidebar."""

import os
import uuid
import threading
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
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
)

from da import __version__
from da.config import load_config, Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore


class SessionItem(ListItem):
    """A session entry in the sidebar."""

    def __init__(self, session_id: str, name: str, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.session_name = name

    def compose(self) -> ComposeResult:
        label = self.session_name[:28] or "new session"
        yield Label(f" {label}")


class ChatMessage(Static):
    """A single chat message."""

    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content

    def compose(self) -> ComposeResult:
        if self.role == "user":
            yield Static(f"[bold green]> {self.content}[/bold green]")
        elif self.role == "tool":
            yield Static(f"[dim]  → {self.content}[/dim]")
        else:
            yield Markdown(self.content)


class DAApp(App):
    """DA — DebilAgent TUI."""

    TITLE = "DA"
    SUB_TITLE = f"v{__version__}"

    CSS = """
    #sidebar {
        width: 30;
        dock: left;
        background: $surface;
        border-right: tall $primary;
    }
    #sidebar-title {
        text-style: bold;
        color: $accent;
        padding: 1 1;
    }
    #session-list {
        height: 1fr;
    }
    #new-session-btn {
        margin: 1;
        text-align: center;
        color: $success;
    }
    #chat-area {
        height: 1fr;
    }
    #chat-scroll {
        height: 1fr;
        padding: 0 1;
    }
    #input-bar {
        dock: bottom;
        height: 3;
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
    """

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+up", "prev_session", "Prev Session"),
        Binding("ctrl+down", "next_session", "Next Session"),
    ]

    current_session_id: reactive[str] = reactive("")

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
        # Per-session message history: session_id -> list of dicts
        self.session_messages: dict[str, list[dict]] = {}
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static(" DA Sessions", id="sidebar-title")
                yield ListView(id="session-list")
                yield Static(" [Ctrl+N] New Session", id="new-session-btn")
            with Vertical(id="chat-area"):
                yield VerticalScroll(id="chat-scroll")
                yield Static("", id="model-label")
                yield Input(placeholder="Ask anything... (/ for commands)", id="prompt-input")
        yield Footer()

    def on_mount(self) -> None:
        """Load existing sessions and create one if empty."""
        self._refresh_session_list()
        session_list = self.query_one("#session-list", ListView)
        if session_list.children:
            session_list.index = 0
        else:
            self._create_new_session()
        self._update_model_label()

    def _refresh_session_list(self) -> None:
        """Reload session list from store."""
        session_list = self.query_one("#session-list", ListView)
        session_list.clear()
        sessions = self.store.list_sessions(limit=50)
        for s in sessions:
            item = SessionItem(s["id"], s["name"])
            session_list.append(item)

    def _create_new_session(self) -> None:
        """Create a new session and select it."""
        sid = str(uuid.uuid4())
        self.store.create_session(sid, name="new session", project=os.getcwd())
        self.session_messages[sid] = []
        self._refresh_session_list()
        session_list = self.query_one("#session-list", ListView)
        session_list.index = 0
        self.current_session_id = sid

    def _update_model_label(self) -> None:
        label = self.query_one("#model-label", Static)
        label.update(f" model: {self.cfg.model} | tools: {len(self.api_tools)} | /help for commands")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Switch to selected session."""
        item = event.item
        if isinstance(item, SessionItem):
            self.current_session_id = item.session_id

    def watch_current_session_id(self, session_id: str) -> None:
        """When session changes, reload chat."""
        if not session_id:
            return
        # Load messages from store if not cached
        if session_id not in self.session_messages:
            stored = self.store.get_messages(session_id, limit=100)
            self.session_messages[session_id] = stored
        self._render_chat()

    def _render_chat(self) -> None:
        """Render current session's messages."""
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
        """Add a message to current session and UI."""
        sid = self.current_session_id
        if sid not in self.session_messages:
            self.session_messages[sid] = []
        self.session_messages[sid].append({"role": role, "content": content})
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
        """Handle user input."""
        text = event.value.strip()
        inp = self.query_one("#prompt-input", Input)
        inp.value = ""

        if not text:
            return

        # Slash commands
        if text.startswith("/"):
            self._handle_slash(text)
            return

        if self.busy:
            self._add_chat_msg("assistant", "*Still thinking... please wait.*")
            return

        # Update session name from first message
        msgs = self.session_messages.get(self.current_session_id, [])
        if not any(m["role"] == "user" for m in msgs):
            self.store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], self.current_session_id),
            )
            self.store.conn.commit()
            self._refresh_session_list()

        self._add_chat_msg("user", text)
        self._run_agent(text)

    def _handle_slash(self, text: str) -> None:
        """Handle slash commands."""
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
                self._add_chat_msg("tool", f"Model switched to {self.cfg.model}")
            elif len(parts) > 1:
                self.cfg.model = parts[1].strip()
                self._add_chat_msg("tool", f"Model set to {self.cfg.model}")
            else:
                lines = [f"Current: {self.cfg.model}"]
                for alias, mid in MODELS.items():
                    lines.append(f"  /model {alias} — {mid}")
                self._add_chat_msg("tool", "\n".join(lines))
            self._update_model_label()
        elif cmd == "/help" or cmd == "/":
            self._add_chat_msg("tool",
                "/model [name] — switch model (opus/sonnet/haiku)\n"
                "/tools — list tools\n"
                "/hosts — list hosts\n"
                "/clear — clear chat\n"
                "/help — this help\n"
                "Ctrl+N — new session\n"
                "Ctrl+Q — quit"
            )
        elif cmd == "/tools":
            lines = [f"{t['name']:18s} {t['description'][:50]}" for t in ALL_TOOL_DEFS]
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
        """Run agent loop in background thread."""
        self.busy = True
        sid = self.current_session_id

        # Build API messages from session history
        api_messages: list[dict] = []
        for m in self.session_messages.get(sid, []):
            if m["role"] in ("user", "assistant"):
                api_messages.append({"role": m["role"], "content": m["content"]})

        try:
            max_iter = 20
            for _ in range(max_iter):
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
                    result_text = "\n".join(text_parts)
                    self.call_from_thread(self._add_chat_msg, "assistant", result_text)
                    break

                # Execute tools
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
        sl = self.query_one("#session-list", ListView)
        if sl.index is not None and sl.index > 0:
            sl.index -= 1

    def action_next_session(self) -> None:
        sl = self.query_one("#session-list", ListView)
        if sl.index is not None and sl.index < len(sl.children) - 1:
            sl.index += 1


def run_tui(config: Config | None = None):
    """Launch the TUI app."""
    app = DAApp(config=config)
    app.run()
