"""Sessions view — browse DA and Claude sessions.

Menu: [S]essions  |  F2  |  /sessions
"""

import datetime
from pathlib import Path

from prompt_toolkit.formatted_text import HTML

from da.config import Config
from da.session import SessionStore
from da.rich_render import (
    console,
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

MENU_KEY = "S"
MENU_LABEL = "Sessions"


class SessionsView:
    def __init__(self, cfg: Config, store: SessionStore):
        self.cfg = cfg
        self.store = store
        self.claude_data: dict = {}
        self.claude_flat: list[dict] = []

    def get_prompt(self) -> HTML:
        return HTML("<ansicyan><b>sessions</b></ansicyan> <ansigray>\u203a</ansigray> ")

    def show(self) -> None:
        """Show combined DA + Claude sessions overview."""
        self._show_da_sessions()
        self._show_claude_summary()
        console.print(render_tool(
            "/switch <id> \u2014 switch DA session  |  "
            "/detail <#> \u2014 Claude detail  |  "
            "/launch <#> \u2014 open in terminal"
        ))

    def handle_input(self, text: str) -> None:
        """Bare numbers inspect Claude sessions; otherwise hint."""
        if text.isdigit():
            self.show_claude_detail(int(text))
        else:
            console.print(render_tool("Enter a session # or use /switch, /detail, /launch"))

    # ── DA sessions ──────────────────────────────────────────────

    def _show_da_sessions(self, current_sid: str = "") -> None:
        sessions = self.store.list_sessions_detailed(limit=20)
        if not sessions:
            return
        t = sessions_table(
            columns=[("ID", "id"), ("Msgs", "msgs"), ("Updated", "updated"), ("Name", "name")],
            rows=[
                [
                    s["id"][:12],
                    str(s["msg_count"]),
                    datetime.datetime.fromtimestamp(s["updated_at"]).strftime("%Y-%m-%d %H:%M") if s["updated_at"] else "?",
                    (s["name"][:40] or "\u2014") + (" *" if s["id"] == current_sid else ""),
                ]
                for s in sessions
            ],
            title=f"\u0414\u0410 Sessions ({len(sessions)})",
        )
        console.print(t)

    def show_da_sessions_list(self, current_sid: str = "") -> None:
        """Public method for /sessions command from other views."""
        self._show_da_sessions(current_sid)
        console.print(render_tool("Use /switch <id-prefix> to switch"))

    def show_stats(self, session_id: str) -> None:
        stats = self.store.get_session_stats(session_id)
        if not stats:
            console.print(render_tool("No stats yet."))
            return
        created = datetime.datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M") if stats["created_at"] else "?"
        updated = datetime.datetime.fromtimestamp(stats["updated_at"]).strftime("%Y-%m-%d %H:%M") if stats["updated_at"] else "?"
        rows = [
            ("Session", session_id[:12]),
            ("Name", stats["name"] or "\u2014"),
            ("Project", stats.get("project", "\u2014")),
            ("Created", created),
            ("Updated", updated),
            ("Messages", str(stats["total_messages"])),
        ]
        for role, count in sorted(stats["message_counts"].items()):
            rows.append((f"  {role}", str(count)))
        console.print(session_info_table(rows, title="\u0414\u0410 Session", border_style="green"))

    def switch_session(self, prefix: str) -> str | None:
        """Find session by prefix. Returns full ID or None."""
        sessions = self.store.list_sessions_detailed(limit=100)
        matches = [s for s in sessions if s["id"].startswith(prefix)]
        if not matches:
            console.print(render_tool(f"No session matching '{prefix}'"))
            return None
        if len(matches) > 1:
            console.print(render_tool(f"Ambiguous prefix \u2014 {len(matches)} matches."))
            return None
        return matches[0]["id"]

    def delete_session(self, target: str) -> bool:
        """Delete session by prefix. Returns True if deleted."""
        sessions = self.store.list_sessions_detailed(limit=100)
        matches = [s for s in sessions if s["id"].startswith(target)]
        if not matches:
            console.print(render_tool(f"No session matching '{target}'"))
            return False
        if len(matches) > 1:
            console.print(render_tool(f"Ambiguous \u2014 {len(matches)} matches."))
            return False
        sid = matches[0]["id"]
        name = matches[0]["name"] or sid[:12]
        self.store.delete_session(sid)
        console.print(render_tool(f"Deleted: {name}"))
        return True

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

    def _ensure_claude_data(self) -> None:
        if not self.claude_flat:
            self._load_claude_data()

    def _show_claude_summary(self) -> None:
        self._ensure_claude_data()
        if not self.claude_flat:
            return
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

    def show_claude_sessions(self) -> None:
        """Full Claude sessions list."""
        self._ensure_claude_data()
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

    def show_claude_detail(self, idx: int) -> None:
        self._ensure_claude_data()
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

    def launch_claude(self, idx: int) -> None:
        self._ensure_claude_data()
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
