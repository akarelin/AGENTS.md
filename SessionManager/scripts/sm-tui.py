#!/usr/bin/env python3
"""
sm-tui — Session & Project Manager TUI

Interactive TUI for browsing remote/local sessions, depositing, renaming,
archiving, and managing projects. Built on Textual, following gppu patterns.

Usage:
    sm-tui                     # Interactive TUI
    sm-tui --no-tui            # Fall back to gppu.tui selectors
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
import base64
from datetime import datetime
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, RichLog, Static

# --- Config ---
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://langfuse.karelin.ai")
LANGFUSE_PK = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-xsolla-main-2026")
LANGFUSE_SK = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-xsolla-main-2026-secret-changeme")
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"


# --- API ---

def _auth_header():
    creds = base64.b64encode(f"{LANGFUSE_PK}:{LANGFUSE_SK}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def api_get(path, params=None):
    url = f"{LANGFUSE_HOST}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url += f"?{qs}"
    req = urllib.request.Request(url, headers=_auth_header())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"data": [], "error": str(e)}


def format_size(size):
    if size < 1024:
        return f"{size}B"
    elif size < 1048576:
        return f"{size // 1024}K"
    else:
        return f"{size / 1048576:.1f}M"


def fetch_local_sessions():
    sessions = []
    if CLAUDE_PROJECTS_DIR.exists():
        for f in sorted(CLAUDE_PROJECTS_DIR.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
            sessions.append({
                "source": "cc",
                "project": f.parent.name.replace("-Users-alex-", "").replace("-", "/"),
                "session_id": f.stem,
                "file": str(f),
                "size": f.stat().st_size,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime),
            })
    if OPENCLAW_AGENTS_DIR.exists():
        for agent_dir in sorted(d for d in OPENCLAW_AGENTS_DIR.iterdir() if d.is_dir()):
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue
            for f in sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
                if ".reset." in f.name:
                    continue
                sessions.append({
                    "source": "oc",
                    "project": agent_dir.name,
                    "session_id": f.stem,
                    "file": str(f),
                    "size": f.stat().st_size,
                    "mtime": datetime.fromtimestamp(f.stat().st_mtime),
                })
    return sessions


# --- Detail Screen ---

class DetailScreen(Screen):
    """Show session details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back", priority=True),
        Binding("q", "dismiss", "Back", show=False),
    ]

    def __init__(self, trace: dict):
        super().__init__()
        self._trace = trace

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="detail-log", highlight=True, markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#detail-log", RichLog)
        t = self._trace
        meta = t.get("metadata", {}) or {}

        log.write(f"[bold]{t.get('name', 'unnamed')}[/]")
        log.write("")
        log.write(f"  Session ID:  {t.get('sessionId', '?')}")
        log.write(f"  Trace ID:    {t.get('id', '?')}")
        log.write(f"  Source:      {'Claude Code' if 'claude-code' in t.get('tags',[]) else 'OpenClaw' if 'openclaw' in t.get('tags',[]) else '?'}")
        log.write(f"  Project:     {meta.get('project', '?')}")
        log.write(f"  Model:       {meta.get('model', '?')}")
        log.write(f"  CWD:         {meta.get('cwd', '?')}")
        log.write(f"  Git Branch:  {meta.get('git_branch', '?')}")
        log.write(f"  Timestamp:   {t.get('timestamp', '?')}")
        log.write(f"  Tags:        {', '.join(t.get('tags', []))}")
        log.write("")

        tok_in = meta.get("total_input_tokens", 0) or 0
        tok_out = meta.get("total_output_tokens", 0) or 0
        gens = meta.get("total_generations", 0) or 0
        msgs = meta.get("total_messages", 0) or 0
        log.write(f"  Input tokens:   {tok_in:,}")
        log.write(f"  Output tokens:  {tok_out:,}")
        log.write(f"  Generations:    {gens}")
        log.write(f"  Messages:       {msgs}")

        input_text = t.get("input", "")
        if input_text:
            log.write("")
            log.write("[bold]First prompt:[/]")
            log.write(f"  {str(input_text)[:500]}")


# --- Main App ---

class SessionManagerApp(App):
    """Session & Project Manager TUI."""

    TITLE = "Session Manager"
    CSS = """
    #main-split { height: 1fr; }
    #list-panel {
        border: solid $accent;
        width: 2fr;
        height: 1fr;
    }
    #detail-panel {
        border: solid $success;
        width: 3fr;
        height: 1fr;
    }
    .panel-label {
        dock: top;
        color: $text;
        text-align: center;
        padding: 0 1;
        height: 1;
    }
    #list-label { background: $accent-darken-2; }
    #detail-label { background: $success-darken-2; }
    #session-table { height: 1fr; }
    #detail-log { height: 1fr; max-height: 100%; }
    #status-bar {
        height: 2;
        border: solid $primary;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("1", "show_remote", "Remote"),
        Binding("2", "show_local", "Local"),
        Binding("3", "show_projects", "Projects"),
        Binding("r", "rename_session", "Rename"),
        Binding("a", "archive_session", "Archive"),
        Binding("d", "deposit_session", "Deposit"),
        Binding("D", "deposit_all", "Deposit All"),
        Binding("enter", "view_detail", "Detail"),
        Binding("escape", "back", "Back", show=False),
    ]

    def __init__(self):
        super().__init__()
        self._remote_traces = []
        self._local_sessions = []
        self._view = "remote"  # remote | local | projects

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status-bar")
        with Horizontal(id="main-split"):
            with Vertical(id="list-panel"):
                yield Static("Sessions", id="list-label", classes="panel-label")
                yield DataTable(id="session-table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="detail-panel"):
                yield Static("Detail", id="detail-label", classes="panel-label")
                yield RichLog(id="detail-log", highlight=True, markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._load_all()

    @work(thread=True)
    def _load_all(self) -> None:
        self.call_from_thread(self._update_status, "Loading remote sessions...")
        data = api_get("/api/public/traces", {"limit": "100"})
        self._remote_traces = data.get("data", [])

        self.call_from_thread(self._update_status, "Loading local sessions...")
        self._local_sessions = fetch_local_sessions()

        r = len(self._remote_traces)
        l = len(self._local_sessions)
        self.call_from_thread(self._update_status,
                              f"[1] Remote: {r}  |  [2] Local: {l}  |  [3] Projects  |  [r]ename [a]rchive [d]eposit [D]eposit-all")
        self.call_from_thread(self._render_remote)

    def _update_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    # --- Remote view ---

    def _render_remote(self) -> None:
        self._view = "remote"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Src", "Name", "Tags", "When", "Tokens")

        label = self.query_one("#list-label", Static)
        skip = {"claude-code", "openclaw", "codex", "archived"}
        count = 0
        for t in self._remote_traces:
            tags = t.get("tags", [])
            if "archived" in tags:
                continue
            src = "cc" if "claude-code" in tags else "oc" if "openclaw" in tags else "??"
            tag_str = ", ".join([tg for tg in tags if tg not in skip])[:25]
            ts = t.get("timestamp", "")
            try:
                when = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%b %d %H:%M")
            except:
                when = "?"
            meta = t.get("metadata", {}) or {}
            tok_in = meta.get("total_input_tokens", 0) or 0
            tok_out = meta.get("total_output_tokens", 0) or 0
            tok = f"{tok_in // 1000}k/{tok_out // 1000}k" if tok_in else ""
            table.add_row(src, t.get("name", "unnamed")[:40], tag_str, when, tok, key=t.get("id", ""))
            count += 1
        label.update(f"Remote Sessions ({count})")
        table.focus()

    # --- Local view ---

    def _render_local(self) -> None:
        self._view = "local"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Src", "Project", "Session", "Size", "Modified")

        for i, s in enumerate(self._local_sessions):
            table.add_row(
                s["source"],
                s["project"][:30],
                s["session_id"][:14] + "...",
                format_size(s["size"]),
                s["mtime"].strftime("%b %d %H:%M"),
                key=str(i),
            )
        label = self.query_one("#list-label", Static)
        label.update(f"Local Sessions ({len(self._local_sessions)})")
        table.focus()

    # --- Projects view ---

    def _render_projects(self) -> None:
        self._view = "projects"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Project", "Sessions", "Input Tok", "Output Tok")

        projects = {}
        for t in self._remote_traces:
            if "archived" in t.get("tags", []):
                continue
            meta = t.get("metadata", {}) or {}
            p = meta.get("project", "unknown")
            projects.setdefault(p, []).append(t)

        for p, traces in sorted(projects.items()):
            tok_in = sum((t.get("metadata", {}) or {}).get("total_input_tokens", 0) or 0 for t in traces)
            tok_out = sum((t.get("metadata", {}) or {}).get("total_output_tokens", 0) or 0 for t in traces)
            table.add_row(p, str(len(traces)), f"{tok_in // 1000}k" if tok_in else "—", f"{tok_out // 1000}k" if tok_out else "—", key=p)

        label = self.query_one("#list-label", Static)
        label.update(f"Projects ({len(projects)})")
        table.focus()

    # --- Row highlight → detail ---

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self._view == "remote":
            trace = next((t for t in self._remote_traces if t.get("id") == event.row_key.value), None)
            if trace:
                self._show_trace_detail(trace)
        elif self._view == "local":
            try:
                idx = int(event.row_key.value)
                s = self._local_sessions[idx]
                self._show_local_detail(s)
            except (ValueError, IndexError):
                pass
        elif self._view == "projects":
            self._show_project_detail(event.row_key.value)

    def _show_trace_detail(self, t: dict) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        meta = t.get("metadata", {}) or {}
        log.write(f"[bold]{t.get('name', 'unnamed')}[/]")
        log.write(f"  ID:       {t.get('sessionId', '?')}")
        log.write(f"  Project:  {meta.get('project', '?')}")
        log.write(f"  Model:    {meta.get('model', '?')}")
        log.write(f"  CWD:      {meta.get('cwd', '?')}")
        log.write(f"  Branch:   {meta.get('git_branch', '?')}")
        tok_in = meta.get("total_input_tokens", 0) or 0
        tok_out = meta.get("total_output_tokens", 0) or 0
        log.write(f"  Tokens:   {tok_in:,} in / {tok_out:,} out")
        log.write(f"  Tags:     {', '.join(t.get('tags', []))}")
        inp = t.get("input", "")
        if inp:
            log.write("")
            log.write("[bold]First prompt:[/]")
            log.write(str(inp)[:500])

    def _show_local_detail(self, s: dict) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        log.write(f"[bold]{s['project']}[/]  [{s['source']}]")
        log.write(f"  Session:   {s['session_id']}")
        log.write(f"  File:      {s['file']}")
        log.write(f"  Size:      {format_size(s['size'])}")
        log.write(f"  Modified:  {s['mtime'].strftime('%Y-%m-%d %H:%M')}")

    def _show_project_detail(self, project: str) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        sessions = [t for t in self._remote_traces if (t.get("metadata", {}) or {}).get("project") == project and "archived" not in t.get("tags", [])]
        log.write(f"[bold]Project: {project}[/]  ({len(sessions)} sessions)")
        log.write("")
        for t in sessions:
            ts = t.get("timestamp", "")
            try:
                when = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%b %d %H:%M")
            except:
                when = "?"
            log.write(f"  {when}  {t.get('name', 'unnamed')}")

    # --- Actions ---

    def action_show_remote(self) -> None:
        self._render_remote()

    def action_show_local(self) -> None:
        self._render_local()

    def action_show_projects(self) -> None:
        self._render_projects()

    def action_back(self) -> None:
        self._render_remote()

    def action_view_detail(self) -> None:
        if self._view != "remote":
            return
        table = self.query_one("#session-table", DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        trace = next((t for t in self._remote_traces if t.get("id") == row_key.value), None)
        if trace:
            self.push_screen(DetailScreen(trace))

    def action_rename_session(self) -> None:
        if self._view != "remote":
            return
        table = self.query_one("#session-table", DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        trace = next((t for t in self._remote_traces if t.get("id") == row_key.value), None)
        if not trace:
            return
        # Use input() via suspend
        self.exit(message=f"sm rename {trace['id']} ")

    def action_archive_session(self) -> None:
        if self._view != "remote":
            return
        table = self.query_one("#session-table", DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        self._do_archive(row_key.value)

    @work(thread=True)
    def _do_archive(self, trace_id: str) -> None:
        subprocess.run(["sm", "archive", trace_id], capture_output=True)
        # Reload
        data = api_get("/api/public/traces", {"limit": "100"})
        self._remote_traces = data.get("data", [])
        self.call_from_thread(self._render_remote)
        self.call_from_thread(self._update_status, "Archived ✓")

    def action_deposit_session(self) -> None:
        if self._view != "local":
            return
        table = self.query_one("#session-table", DataTable)
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        try:
            idx = int(row_key.value)
            s = self._local_sessions[idx]
            self._do_deposit(s["file"])
        except (ValueError, IndexError):
            pass

    @work(thread=True)
    def _do_deposit(self, file_path: str) -> None:
        self.call_from_thread(self._update_status, f"Depositing {Path(file_path).stem[:16]}...")
        subprocess.run(["sm", "deposit", file_path], capture_output=True)
        # Reload remote
        data = api_get("/api/public/traces", {"limit": "100"})
        self._remote_traces = data.get("data", [])
        self.call_from_thread(self._render_remote)
        self.call_from_thread(self._update_status, "Deposited ✓")

    def action_deposit_all(self) -> None:
        self._do_deposit_all()

    @work(thread=True)
    def _do_deposit_all(self) -> None:
        log = self.query_one("#detail-log", RichLog)
        self.call_from_thread(log.clear)
        total = len(self._local_sessions)
        self.call_from_thread(self._update_status, f"Depositing {total} sessions...")
        ok = 0
        for i, s in enumerate(self._local_sessions, 1):
            self.call_from_thread(log.write, f"[{i}/{total}] {s['project']} ({s['session_id'][:12]}...)")
            result = subprocess.run(["sm", "deposit", s["file"]], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                ok += 1
        self.call_from_thread(self._update_status, f"Deposited {ok}/{total} ✓")
        data = api_get("/api/public/traces", {"limit": "100"})
        self._remote_traces = data.get("data", [])
        self.call_from_thread(self._render_remote)


# --- Fallback (--no-tui) ---

def run_select_mode():
    from gppu.tui import ui_select, ui_select_rows

    mode = ui_select(["📡 Remote Sessions", "💾 Local Sessions", "📁 Projects"])
    if mode == "📡 Remote Sessions":
        data = api_get("/api/public/traces", {"limit": "100"})
        traces = data.get("data", [])
        rows = []
        skip = {"claude-code", "openclaw", "codex", "archived"}
        for t in traces:
            tags = t.get("tags", [])
            if "archived" in tags:
                continue
            meta = t.get("metadata", {}) or {}
            rows.append({
                "src": "cc" if "claude-code" in tags else "oc",
                "name": t.get("name", "unnamed"),
                "tags": ", ".join(tg for tg in tags if tg not in skip),
                "session_id": t.get("sessionId", ""),
            })
        if rows:
            ui_select_rows(rows, summary_keys=["src", "name", "tags"])
    elif mode == "💾 Local Sessions":
        sessions = fetch_local_sessions()
        rows = [{"src": s["source"], "project": s["project"], "size": format_size(s["size"]), "file": s["file"]} for s in sessions]
        if rows:
            ui_select_rows(rows, summary_keys=["src", "project", "size"], expanded_keys=["file"])


def main():
    parser = argparse.ArgumentParser(description="Session Manager TUI")
    parser.add_argument("--no-tui", action="store_true", help="Use gppu.tui selectors instead of full TUI")
    args = parser.parse_args()

    if args.no_tui:
        return run_select_mode()

    app = SessionManagerApp()
    result = app.run()
    if result:
        print(result)


if __name__ == "__main__":
    main()
