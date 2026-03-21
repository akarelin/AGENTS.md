"""DA Rich TUI — Console-based REPL with Rich rendering.

A lighter alternative to the full Textual TUI. Uses Rich Console for
output and prompt_toolkit for input. No Textual dependency.

Two views with highlighted shortcut keys:
  [Д]А       — chat with agent (default)
  [S]essions — browse DA + Claude sessions

Features (parity with tui.py):
  - Multi-session management: /new, /sessions, /switch, /delete, /resume
  - Claude session browsing: /claude, /detail, /launch
  - Agent loop with tool execution
  - Rich Markdown rendering for assistant messages

Launch: da rich
"""

import datetime
import os
import uuid
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings

from da import __version__
from da.config import load_config, Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore
from da.rich_render import (
    console,
    render_banner,
    render_menu_bar,
    render_message,
    render_tool,
    session_info_table,
    render_message_preview,
    sessions_table,
)
from da.tui import (
    load_claude_sessions,
    load_claude_session_messages,
    copy_session_to_local,
    launch_claude_session,
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

SLASH_COMMANDS = [
    "/help", "/model", "/tools", "/hosts", "/stats", "/clear", "/quit", "/exit",
    "/new", "/sessions", "/switch", "/delete", "/resume",
    "/claude", "/detail", "/launch", "/da",
]


class RichTUI:
    """Stateful Rich console TUI with multi-session and Claude browsing."""

    def __init__(self, config: Config | None = None):
        self.cfg = config or load_config()
        self.store = SessionStore(self.cfg.session.db_path)
        self.client = get_client(self.cfg)
        self.system_prompt = get_system_prompt(self.cfg)
        self.api_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in ALL_TOOL_DEFS
        ]

        # View state: "da" or "sessions"
        self.view = "da"

        # Session state
        self.session_id = ""
        self.api_messages: list[dict] = []
        self.session_messages: dict[str, list[dict]] = {}

        # Claude session cache
        self.claude_data: dict = {}
        self.claude_flat: list[dict] = []

        # Key bindings for view switching
        self.kb = KeyBindings()

        @self.kb.add("f1")
        def _f1(event):
            self.view = "da"
            self._print_menu()

        @self.kb.add("f2")
        def _f2(event):
            self.view = "sessions"
            self._print_menu()
            self._show_sessions_view()

        self.prompt_session = PromptSession(
            history=InMemoryHistory(),
            completer=WordCompleter(SLASH_COMMANDS, sentence=True),
            key_bindings=self.kb,
        )

    # ── Menu ─────────────────────────────────────────────────────

    def _print_menu(self) -> None:
        console.print(render_menu_bar(
            self.view, model=self.cfg.model, tool_count=len(self.api_tools),
        ))

    def _get_prompt(self) -> HTML:
        if self.view == "da":
            return HTML("<ansigreen><b>you</b></ansigreen> <ansigray>\u203a</ansigray> ")
        else:
            return HTML("<ansicyan><b>sessions</b></ansicyan> <ansigray>\u203a</ansigray> ")

    # ── Session management ───────────────────────────────────────

    def _new_session(self, name: str = "rich session") -> None:
        self.session_id = str(uuid.uuid4())
        self.store.create_session(self.session_id, name=name, project=os.getcwd())
        self.api_messages = []
        self.session_messages[self.session_id] = []
        console.print(render_tool(f"New session: {self.session_id[:12]}"))

    def _load_session(self, sid: str) -> bool:
        stored = self.store.get_messages(sid, limit=100)
        if stored is None:
            console.print(render_tool(f"Session {sid} not found."))
            return False
        self.session_id = sid
        self.session_messages[sid] = stored
        self.api_messages = []
        for m in stored:
            if m["role"] in ("user", "assistant"):
                self.api_messages.append({"role": m["role"], "content": m["content"]})
        console.print(render_tool(f"Loaded session: {sid[:12]} ({len(stored)} messages)"))
        return True

    def _name_session(self, text: str) -> None:
        if not any(m.get("role") == "user" for m in self.api_messages):
            self.store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], self.session_id),
            )
            self.store.conn.commit()

    # ── Claude sessions ──────────────────────────────────────────

    def _load_claude_data(self) -> None:
        claude_dir = self.cfg.claude_history or "/mnt/d/SD/.claude"
        self.claude_data = load_claude_sessions(claude_dir)
        self.claude_flat = []
        for machine, projects in self.claude_data.items():
            for proj, sessions in projects.items():
                for s in sessions:
                    s["_machine"] = machine
                    s["_project"] = proj
                    self.claude_flat.append(s)

    def _show_claude_sessions(self) -> None:
        if not self.claude_flat:
            self._load_claude_data()
        if not self.claude_flat:
            console.print(render_tool("No Claude sessions found."))
            return

        t = sessions_table(
            columns=[("#", "idx"), ("Machine", "machine"), ("Project", "project"),
                     ("Date", "date"), ("Name", "name")],
            rows=[
                [str(i + 1), _machine_label(s["_machine"]),
                 s["_project"].split("/")[-1] or s["_project"].split("\\")[-1],
                 s.get("date", "\u2014"), s.get("name", "\u2014")[:50]]
                for i, s in enumerate(self.claude_flat[:30])
            ],
            title="Claude Sessions",
        )
        console.print(t)
        console.print(render_tool("Use /detail <#> to inspect, /launch <#> to open in terminal"))

    def _show_claude_detail(self, idx: int) -> None:
        if not self.claude_flat:
            self._load_claude_data()
        if idx < 1 or idx > len(self.claude_flat):
            console.print(render_tool(f"Invalid index. Use 1-{len(self.claude_flat)}"))
            return

        info = self.claude_flat[idx - 1]
        fpath = Path(info["file"])
        fsize = fpath.stat().st_size if fpath.exists() else 0

        subagent_dir = fpath.parent / fpath.stem / "subagents"
        subagent_count = len(list(subagent_dir.glob("*.jsonl"))) if subagent_dir.is_dir() else 0

        msgs = load_claude_session_messages(info["file"])
        roles: dict[str, int] = {}
        for m in msgs:
            roles[m["role"]] = roles.get(m["role"], 0) + 1

        local_path = Path.home() / ".claude" / "projects" / info.get("project_dir", "") / fpath.name

        rows = [
            ("ID", info["id"][:12]),
            ("Machine", _machine_label(info["_machine"])),
            ("Project", info["_project"]),
            ("Date", info.get("date", "?")),
            ("Size", f"{fsize:,} bytes"),
            ("Messages", str(len(msgs))),
        ]
        for r, c in sorted(roles.items()):
            rows.append((f"  {r}", str(c)))
        rows.append(("Subagents", str(subagent_count)))
        rows.append(("Local copy", "[green]yes[/green]" if local_path.exists() else "[dim]no[/dim]"))

        console.print(session_info_table(rows, title="Claude Session", border_style="cyan"))
        if msgs:
            console.print(render_message_preview(msgs))

    def _launch_claude(self, idx: int) -> None:
        if not self.claude_flat:
            self._load_claude_data()
        if idx < 1 or idx > len(self.claude_flat):
            console.print(render_tool(f"Invalid index. Use 1-{len(self.claude_flat)}"))
            return

        info = self.claude_flat[idx - 1]
        try:
            copy_session_to_local(info)
        except Exception:
            pass
        result = launch_claude_session(info, {n: h for n, h in self.cfg.hosts.items()})
        console.print(render_tool(result))

    # ── Sessions view ────────────────────────────────────────────

    def _show_sessions_view(self) -> None:
        """Show combined DA + Claude sessions overview."""
        # DA sessions
        sessions = self.store.list_sessions_detailed(limit=20)
        if sessions:
            t = sessions_table(
                columns=[("ID", "id"), ("Msgs", "msgs"), ("Updated", "updated"), ("Name", "name")],
                rows=[
                    [
                        s["id"][:12],
                        str(s["msg_count"]),
                        datetime.datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M") if s["updated_at"] else "?",
                        (s["name"][:40] or "\u2014") + (" *" if s["id"] == self.session_id else ""),
                    ]
                    for s in sessions
                ],
                title=f"\u0414\u0410 Sessions ({len(sessions)})",
            )
            console.print(t)

        # Claude sessions summary
        if not self.claude_flat:
            self._load_claude_data()
        if self.claude_flat:
            t = sessions_table(
                columns=[("#", "idx"), ("Machine", "machine"), ("Project", "project"),
                         ("Date", "date"), ("Name", "name")],
                rows=[
                    [str(i + 1), _machine_label(s["_machine"]),
                     s["_project"].split("/")[-1] or s["_project"].split("\\")[-1],
                     s.get("date", "\u2014"), s.get("name", "\u2014")[:50]]
                    for i, s in enumerate(self.claude_flat[:15])
                ],
                title=f"Claude Sessions ({len(self.claude_flat)})",
            )
            console.print(t)

        console.print(render_tool(
            "/switch <id> \u2014 switch DA session  |  "
            "/detail <#> \u2014 Claude detail  |  "
            "/launch <#> \u2014 open in terminal"
        ))

    def _handle_sessions_input(self, text: str) -> None:
        """Handle input in sessions view — numbers select Claude sessions."""
        if text.isdigit():
            self._show_claude_detail(int(text))
        else:
            console.print(render_tool(f"Enter a session # or use /switch, /detail, /launch"))

    # ── Slash commands ───────────────────────────────────────────

    def handle_slash(self, cmd: str) -> bool:
        """Handle slash commands. Returns False to signal exit."""
        parts = cmd.split(None, 1)
        verb = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if verb in ("/quit", "/exit", "/q"):
            return False

        if verb == "/da":
            self.view = "da"
            self._print_menu()
            return True

        if verb == "/sessions":
            self.view = "sessions"
            self._print_menu()
            self._show_sessions_view()
            return True

        if verb in ("/help", "/"):
            console.print(render_tool(
                "Views:  F1 or /da \u2014 chat  |  F2 or /sessions \u2014 browse\n"
                "\n"
                "  /model [name] \u2014 switch model (opus/sonnet/haiku)\n"
                "  /tools        \u2014 list tools\n"
                "  /hosts        \u2014 list hosts\n"
                "  /stats        \u2014 current session stats\n"
                "  /new          \u2014 create new session\n"
                "  /switch <id>  \u2014 switch to session by ID prefix\n"
                "  /resume <id>  \u2014 resume session (alias for /switch)\n"
                "  /delete [id]  \u2014 delete current or specified session\n"
                "  /claude       \u2014 browse Claude sessions\n"
                "  /detail <#>   \u2014 Claude session detail by index\n"
                "  /launch <#>   \u2014 open Claude session in new terminal\n"
                "  /clear        \u2014 clear screen\n"
                "  /quit         \u2014 exit"
            ))

        elif verb == "/model":
            if arg.lower() in MODELS:
                self.cfg.model = MODELS[arg.lower()]
                console.print(render_tool(f"Model: {self.cfg.model}"))
            elif arg:
                self.cfg.model = arg
                console.print(render_tool(f"Model: {self.cfg.model}"))
            else:
                lines = [f"Current: {self.cfg.model}"]
                for alias, model in MODELS.items():
                    lines.append(f"  /model {alias} \u2014 {model}")
                console.print(render_tool("\n".join(lines)))

        elif verb == "/tools":
            lines = [f"{t['name']:18s} {t['description'][:50]}" for t in ALL_TOOL_DEFS]
            console.print(render_tool("\n".join(lines)))

        elif verb == "/hosts":
            lines = [f"{n:15s} {h.ssh} [{', '.join(h.roles)}]" for n, h in self.cfg.hosts.items()]
            console.print(render_tool("\n".join(lines) if lines else "No hosts configured."))

        elif verb == "/stats":
            self._show_stats()

        elif verb == "/new":
            self._new_session(name=arg or "rich session")

        elif verb in ("/switch", "/resume"):
            if not arg:
                console.print(render_tool("Usage: /switch <session-id-prefix>"))
            else:
                self._switch_session(arg)

        elif verb == "/delete":
            self._delete_session(arg)

        elif verb == "/claude":
            self._show_claude_sessions()

        elif verb == "/detail":
            if arg and arg.isdigit():
                self._show_claude_detail(int(arg))
            else:
                console.print(render_tool("Usage: /detail <#> (from /claude list)"))

        elif verb == "/launch":
            if arg and arg.isdigit():
                self._launch_claude(int(arg))
            else:
                console.print(render_tool("Usage: /launch <#> (from /claude list)"))

        elif verb == "/clear":
            console.clear()
            self._print_menu()

        else:
            console.print(render_tool(f"Unknown: {verb}. Type /help"))

        return True

    # ── DA session commands ──────────────────────────────────────

    def _show_stats(self) -> None:
        stats = self.store.get_session_stats(self.session_id)
        if not stats:
            console.print(render_tool("No stats yet."))
            return
        created = datetime.datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M") if stats["created_at"] else "?"
        updated = datetime.datetime.fromtimestamp(stats["updated_at"]).strftime("%Y-%m-%d %H:%M") if stats["updated_at"] else "?"
        rows = [
            ("Session", self.session_id[:12]),
            ("Name", stats["name"] or "\u2014"),
            ("Project", stats.get("project", "\u2014")),
            ("Created", created),
            ("Updated", updated),
            ("Messages", str(stats["total_messages"])),
        ]
        for role, count in sorted(stats["message_counts"].items()):
            rows.append((f"  {role}", str(count)))
        console.print(session_info_table(rows, title="\u0414\u0410 Session", border_style="green"))

    def _switch_session(self, prefix: str) -> None:
        sessions = self.store.list_sessions_detailed(limit=100)
        matches = [s for s in sessions if s["id"].startswith(prefix)]
        if not matches:
            console.print(render_tool(f"No session matching '{prefix}'"))
            return
        if len(matches) > 1:
            console.print(render_tool(f"Ambiguous prefix \u2014 {len(matches)} matches. Be more specific."))
            return
        self._load_session(matches[0]["id"])
        self.view = "da"
        self._print_menu()

    def _delete_session(self, arg: str) -> None:
        target = arg or self.session_id
        sessions = self.store.list_sessions_detailed(limit=100)
        matches = [s for s in sessions if s["id"].startswith(target)]
        if not matches:
            console.print(render_tool(f"No session matching '{target}'"))
            return
        if len(matches) > 1:
            console.print(render_tool(f"Ambiguous \u2014 {len(matches)} matches."))
            return

        sid = matches[0]["id"]
        name = matches[0]["name"] or sid[:12]
        self.store.delete_session(sid)
        self.session_messages.pop(sid, None)
        console.print(render_tool(f"Deleted: {name}"))

        if sid == self.session_id:
            self._new_session()

    # ── Agent loop ───────────────────────────────────────────────

    def run_agent(self) -> None:
        try:
            with console.status("[bold green]Thinking..."):
                result = self._agent_loop()
            self.store.add_message(self.session_id, "assistant", result)
            self.session_messages.setdefault(self.session_id, []).append(
                {"role": "assistant", "content": result}
            )
            console.print(render_message("assistant", result))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    def _agent_loop(self) -> str:
        for _ in range(20):
            response = call_agent(
                self.client, self.cfg, self.system_prompt, self.api_messages, self.api_tools
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

            self.api_messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                return "\n".join(text_parts)

            tool_results = []
            for tu in tool_uses:
                console.print(render_tool(tu.name))
                result = execute_tool(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": str(result),
                })

            self.api_messages.append({"role": "user", "content": tool_results})

        return "[max tool iterations reached]"

    # ── Main loop ────────────────────────────────────────────────

    def run(self) -> None:
        console.print(render_banner(BANNER, __version__, self.cfg.model, len(self.api_tools)))
        self._new_session()
        self._print_menu()

        while True:
            try:
                text = self.prompt_session.prompt(self._get_prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                console.print(render_tool("bye"))
                break

            if not text:
                continue

            if text.startswith("/"):
                if not self.handle_slash(text):
                    console.print(render_tool("bye"))
                    break
                continue

            # View-specific input handling
            if self.view == "sessions":
                self._handle_sessions_input(text)
                continue

            # ДА view — chat
            self._name_session(text)
            console.print(render_message("user", text))
            self.store.add_message(self.session_id, "user", text)
            self.session_messages.setdefault(self.session_id, []).append(
                {"role": "user", "content": text}
            )
            self.api_messages.append({"role": "user", "content": text})
            self.run_agent()


def run_rich_tui(config: Config | None = None):
    RichTUI(config).run()
