"""DA Rich TUI — Console-based REPL with Rich rendering.

A lighter alternative to the full Textual TUI. Uses Rich Console for
output and prompt_toolkit for input. No Textual dependency.

Views (each a separate module in da/views/):
  [Д]А        — chat with agent       (F1 / /da)
  [S]essions  — browse sessions        (F2 / /sessions)
  [O]bsidian  — browse Obsidian vault  (F3 / /obsidian)

Launch: da rich
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings

from da import __version__
from da.config import load_config, Config
from da.tools import ALL_TOOL_DEFS
from da.session import SessionStore
from da.rich_render import console, render_banner, render_menu_bar, render_tool
from da.views.da_chat import DAChatView
from da.views.sessions import SessionsView
from da.views.obsidian import ObsidianView

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

# Menu tabs: (shortcut_key, rest_of_label, view_name)
MENU_TABS = [
    ("Д", "А", "da"),
    ("S", "essions", "sessions"),
    ("O", "bsidian", "obsidian"),
]

SLASH_COMMANDS = [
    "/help", "/model", "/tools", "/hosts", "/stats", "/clear", "/quit", "/exit",
    "/new", "/switch", "/delete", "/resume",
    "/claude", "/detail", "/launch",
    "/da", "/sessions", "/obsidian",
]


class RichTUI:
    """Stateful Rich console TUI with pluggable view modules."""

    def __init__(self, config: Config | None = None):
        self.cfg = config or load_config()
        self.store = SessionStore(self.cfg.session.db_path)
        self.tool_count = len(ALL_TOOL_DEFS)

        # Views
        self.da_view = DAChatView(self.cfg, self.store)
        self.sessions_view = SessionsView(self.cfg, self.store)
        self.obsidian_view = ObsidianView(self.cfg)

        self.views = {
            "da": self.da_view,
            "sessions": self.sessions_view,
            "obsidian": self.obsidian_view,
        }
        self.view = "da"

        # Key bindings
        self.kb = KeyBindings()

        @self.kb.add("f1")
        def _f1(event):
            self._switch_view("da")

        @self.kb.add("f2")
        def _f2(event):
            self._switch_view("sessions")

        @self.kb.add("f3")
        def _f3(event):
            self._switch_view("obsidian")

        self.prompt_session = PromptSession(
            history=InMemoryHistory(),
            completer=WordCompleter(SLASH_COMMANDS, sentence=True),
            key_bindings=self.kb,
        )

    # ── View switching ───────────────────────────────────────────

    def _switch_view(self, name: str) -> None:
        self.view = name
        self._print_menu()
        self.views[name].show()

    def _print_menu(self) -> None:
        status = f"{self.cfg.model} | {self.tool_count} tools | /help"
        console.print(render_menu_bar(MENU_TABS, self.view, status))

    def _get_prompt(self):
        return self.views[self.view].get_prompt()

    # ── Slash commands ───────────────────────────────────────────

    def handle_slash(self, cmd: str) -> bool:
        """Handle slash commands. Returns False to signal exit."""
        parts = cmd.split(None, 1)
        verb = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if verb in ("/quit", "/exit", "/q"):
            return False

        # View switches
        if verb == "/da":
            self._switch_view("da")
            return True
        if verb == "/sessions":
            self._switch_view("sessions")
            return True
        if verb == "/obsidian":
            self._switch_view("obsidian")
            return True

        if verb in ("/help", "/"):
            console.print(render_tool(
                "Views:  F1 /da  |  F2 /sessions  |  F3 /obsidian\n"
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
            self.sessions_view.show_stats(self.da_view.session_id)

        elif verb == "/new":
            self.da_view.new_session(name=arg or "rich session")
            self._switch_view("da")

        elif verb in ("/switch", "/resume"):
            if not arg:
                console.print(render_tool("Usage: /switch <session-id-prefix>"))
            else:
                sid = self.sessions_view.switch_session(arg)
                if sid:
                    self.da_view.load_session(sid)
                    self._switch_view("da")

        elif verb == "/delete":
            target = arg or self.da_view.session_id
            deleted_current = (target == self.da_view.session_id)
            if self.sessions_view.delete_session(target):
                self.da_view.session_messages.pop(target, None)
                if deleted_current:
                    self.da_view.new_session()

        elif verb == "/claude":
            self.sessions_view.show_claude_sessions()

        elif verb == "/detail":
            if arg and arg.isdigit():
                self.sessions_view.show_claude_detail(int(arg))
            else:
                console.print(render_tool("Usage: /detail <#> (from /claude list)"))

        elif verb == "/launch":
            if arg and arg.isdigit():
                self.sessions_view.launch_claude(int(arg))
            else:
                console.print(render_tool("Usage: /launch <#> (from /claude list)"))

        elif verb == "/clear":
            console.clear()
            self._print_menu()

        else:
            console.print(render_tool(f"Unknown: {verb}. Type /help"))

        return True

    # ── Main loop ────────────────────────────────────────────────

    def run(self) -> None:
        console.print(render_banner(BANNER, __version__, self.cfg.model, self.tool_count))
        self.da_view.new_session()
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

            # Delegate to active view
            self.views[self.view].handle_input(text)


def run_rich_tui(config: Config | None = None):
    RichTUI(config).run()
