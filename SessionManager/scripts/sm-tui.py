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
import re
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
from rich.text import Text

# --- Config ---
# Everything overridable via env var OR sessions.yaml (SessionManager root).
# YAML takes precedence over env; both override the defaults below.

def _load_yaml_config() -> dict:
    """Best-effort load of sessions.yaml from candidate SessionManager dirs."""
    for base in [
        Path("/Users/alex/A/SessionManager"),
        Path("/Users/alex/RAN/AI/SessionManager"),
        Path.home() / "A" / "SessionManager",
        Path.home() / "SessionManager",
    ]:
        f = base / "sessions.yaml"
        if f.is_file():
            try:
                import yaml  # pyyaml
                return yaml.safe_load(f.read_text()) or {}
            except Exception:
                return {}
    return {}


_CFG = _load_yaml_config().get("sm_tui", {}) if isinstance(_load_yaml_config(), dict) else {}

def _cfg(key: str, env: str, default: str) -> str:
    return _CFG.get(key) or os.environ.get(env) or default

LANGFUSE_HOST = _cfg("langfuse_host", "LANGFUSE_HOST", "https://langfuse.karelin.ai")
LANGFUSE_PK = _cfg("langfuse_public_key", "LANGFUSE_PUBLIC_KEY", "pk-lf-xsolla-main-2026")
LANGFUSE_SK = _cfg("langfuse_secret_key", "LANGFUSE_SECRET_KEY", "sk-lf-xsolla-main-2026-secret-changeme")
CLAUDE_PROJECTS_DIR = Path(_cfg("claude_projects_dir", "SM_CLAUDE_PROJECTS_DIR",
                                str(Path.home() / ".claude" / "projects")))
OPENCLAW_AGENTS_DIR = Path(_cfg("openclaw_agents_dir", "SM_OPENCLAW_AGENTS_DIR",
                                str(Path.home() / ".openclaw" / "agents")))


# --- API + cache ---

CACHE_DIR = _cfg("cache_dir", "SM_CACHE_DIR", str(Path.home() / ".cache" / "sm-tui"))
CACHE_TTL = int(_cfg("cache_ttl_seconds", "SM_CACHE_TTL", "600"))  # 10 min default

try:
    from gppu.data import Cache as _GppuCache
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    _CACHE = _GppuCache(CACHE_DIR, ttl=CACHE_TTL, backend="sqlite")
except Exception as _e:  # gppu missing or cache init failed — disable transparently
    _CACHE = None


def _cache_key(method: str, path: str, params: dict | None) -> str:
    qs = ""
    if params:
        qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
    return f"{method}:{LANGFUSE_HOST}{path}?{qs}"


def cache_clear() -> int:
    """Invalidate cached Langfuse responses. Returns 1 if cache present, 0 otherwise."""
    if _CACHE is None:
        return 0
    # gppu Cache has no bulk-clear; close+re-open with cleared dir is ugly.
    # Instead: mark "force_refresh" marker the next fetch consults.
    _CACHE.set("__force_refresh__", 1, expire=1)  # expires in 1s — but still bumps gen
    return 1


def _auth_header():
    creds = base64.b64encode(f"{LANGFUSE_PK}:{LANGFUSE_SK}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


def api_get(path, params=None, *, use_cache: bool = True):
    """GET + JSON-decode a Langfuse endpoint. Caches response for CACHE_TTL
    seconds (gppu.data.Cache, SQLite-backed). Bypass with SKIP_CACHE=1 env
    or use_cache=False."""
    skip = os.environ.get("SKIP_CACHE") or not use_cache or _CACHE is None
    cache_k = _cache_key("GET", path, params)

    if not skip:
        cached = _CACHE.get(cache_k)
        if cached is not None:
            return cached

    url = f"{LANGFUSE_HOST}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url += f"?{qs}"
    req = urllib.request.Request(url, headers=_auth_header())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return {"data": [], "error": str(e)}

    if _CACHE is not None and not skip:
        try:
            _CACHE.set(cache_k, data)
        except Exception:
            pass
    return data


def api_get_paginated(path, max_pages=10, limit=100, *, use_cache: bool = True):
    """Fetch up to max_pages of Langfuse list results. Each page cached
    separately so partial invalidation is possible. Returns (all_data, total)."""
    all_data = []
    total = 0
    for page in range(1, max_pages + 1):
        d = api_get(path, {"limit": str(limit), "page": str(page)}, use_cache=use_cache)
        rows = d.get("data", [])
        if page == 1:
            total = (d.get("meta") or {}).get("totalItems", len(rows))
        if not rows:
            break
        all_data.extend(rows)
        if page * limit >= total:
            break
    return all_data, total


def format_size(size):
    if size < 1024:
        return f"{size}B"
    elif size < 1048576:
        return f"{size // 1024}K"
    else:
        return f"{size / 1048576:.1f}M"


SRC_ICON = {"cc": "🤖", "oc": "🦀", "claude-code": "🤖", "openclaw": "🦀"}


def src_badge(src: str) -> str:
    """Short visual source indicator."""
    return SRC_ICON.get(src, "·")


def age_color(dt) -> str:
    """Rich color string based on age of the timestamp.
    Recent → bright green; weeks → yellow; months+ → dim."""
    from datetime import datetime as _dt, timezone as _tz
    if dt is None:
        return "dim"
    now = _dt.now(_tz.utc) if getattr(dt, "tzinfo", None) else _dt.now()
    try:
        days = (now - dt).total_seconds() / 86400.0
    except Exception:
        return "dim"
    if days < 1:      return "bright_green"
    if days < 7:      return "green"
    if days < 30:     return "yellow"
    if days < 90:     return "orange3"
    if days < 365:    return "red"
    return "bright_black"


def size_weight(size_bytes: int) -> str:
    """Rich style modifier: bold if large, regular otherwise."""
    if size_bytes >= 1024 * 1024:     # ≥1 MB
        return "bold "
    if size_bytes >= 100 * 1024:      # ≥100 KB
        return ""
    return "dim "                      # <100 KB → faded


def tint(text, dt, size_bytes: int = 0):
    """Return a Rich Text colored by age and weighted by size.
    (Textual DataTable cells render Text objects with style; raw markup
    strings would display literally.)"""
    color = age_color(dt)
    weight = size_weight(size_bytes).strip()
    style = f"{weight} {color}".strip()
    return Text(str(text), style=style)


def format_age(dt):
    """Short relative age: 2m, 3h, 5d, 2w, 3mo, 1y."""
    if dt is None:
        return "—"
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc) if dt.tzinfo else _dt.now()
    try:
        secs = (now - dt).total_seconds()
    except Exception:
        return "?"
    if secs < 60:
        return f"{int(secs)}s"
    if secs < 3600:
        return f"{int(secs / 60)}m"
    if secs < 86400:
        return f"{int(secs / 3600)}h"
    if secs < 86400 * 14:
        return f"{int(secs / 86400)}d"
    if secs < 86400 * 60:
        return f"{int(secs / (86400 * 7))}w"
    if secs < 86400 * 365:
        return f"{int(secs / (86400 * 30))}mo"
    return f"{secs / (86400 * 365):.1f}y"


_SLUG_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_(?P<cat>[^_]+)_(?P<slug>.+)__(?P<u8>[0-9a-f]{8})\."
)


def _read_first_user_message(jsonl_path: Path, max_scan: int = 30) -> str:
    """Extract the first user-message content from a session JSONL.
    Handles both Claude Code (`type=user`) and OpenClaw (`type=message` with
    role=user) shapes. Returns empty string on failure."""
    try:
        with open(jsonl_path, "rb") as f:
            for i, line in enumerate(f):
                if i >= max_scan:
                    break
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                t = entry.get("type")
                msg = entry.get("message") or {}
                if t == "user" or (t == "message" and msg.get("role") == "user"):
                    c = msg.get("content") if msg else entry.get("content")
                    if isinstance(c, list):
                        c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
                    if isinstance(c, str) and c.strip():
                        return c.strip()
    except OSError:
        pass
    return ""


def _find_analyzed_md(session_id: str, source: str) -> Path | None:
    """Look up the SessionSkills-analyzed markdown for this session."""
    base = Path("/Users/alex/_/{internals}/session-intel/analyzed")
    tool = "openclaw" if source == "oc" else "claude-code"
    d = base / tool
    if not d.is_dir():
        return None
    id12 = session_id[:12]
    for f in d.glob(f"{tool}-*-{id12}.md"):
        return f
    return None


def _session_description(source_file: Path) -> str:
    """Look for a sessions-named/ symlink matching this file's uuid8 prefix
    and extract the descriptive slug. Checks both conventional layouts:
      claude-code:  ~/.claude/projects/<slug>/sessions-named/       (sibling of jsonl's parent)
      openclaw:     ~/.openclaw/agents/<agent>/sessions-named/     (parent's sibling)
    """
    uuid8 = source_file.stem[:8]
    for candidate in (source_file.parent / "sessions-named",
                      source_file.parent.parent / "sessions-named"):
        if not candidate.is_dir():
            continue
        for link in candidate.iterdir():
            m = _SLUG_RE.match(link.name)
            if m and m.group("u8") == uuid8:
                return m.group("slug")
    return ""


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
                "description": _session_description(f),
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
                    "description": _session_description(f),
                })
    return sessions


# --- Detail Screen ---

class FilterPromptScreen(Screen):
    """Modal-ish prompt for a substring filter. Submits via Enter; Esc cancels."""
    CSS = """
    FilterPromptScreen { align: center middle; }
    #filter-wrap {
        width: 60; height: 5; border: solid $accent;
        padding: 1 1; background: $surface;
    }
    #filter-label { height: 1; color: $text; }
    #filter-input { height: 1; }
    """
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, initial: str = ""):
        super().__init__()
        self._initial = initial

    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        with Vertical(id="filter-wrap"):
            yield Static("Filter (substring, case-insensitive). Enter to apply, Esc to cancel.",
                         id="filter-label")
            yield Input(value=self._initial, placeholder="type to filter…", id="filter-input")

    def on_mount(self) -> None:
        self.query_one("#filter-input").focus()

    def on_input_submitted(self, event) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        self.dismiss(None)


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
        Binding("4", "show_stats", "Stats"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("slash", "filter_prompt", "Filter"),
        Binding("R", "refresh", "Refresh"),
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
        self._remote_total = 0       # real count from Langfuse meta.totalItems
        self._local_sessions = []
        self._view = "remote"        # remote | local | projects | stats
        self._filter = ""            # substring filter applied to current view
        # per-view sort state: (column_index, descending)
        # Remote cols:  0=Src 1=Name 2=Description 3=Tags 4=Age 5=Size 6=Tokens
        # Local  cols:  0=Src 1=Project 2=Description 3=Size 4=Age
        self._sort = {
            "remote": (4, True),     # Age desc
            "local": (4, True),      # Age desc
            "projects": (1, True),   # Session count desc
        }

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
        self.call_from_thread(self._update_status, "Loading remote sessions (paginated)…")
        traces, total = api_get_paginated("/api/public/traces", max_pages=10, limit=100)
        self._remote_traces = traces
        self._remote_total = total

        self.call_from_thread(self._update_status, "Loading local sessions…")
        self._local_sessions = fetch_local_sessions()

        loaded = len(self._remote_traces)
        total_r = self._remote_total or loaded
        total_l = len(self._local_sessions)
        undep = max(0, total_l - total_r)
        self.call_from_thread(
            self._update_status,
            f"[1]Remote {loaded}/{total_r}  [2]Local {total_l}  [3]Projects  [4]Stats  "
            f"(undep≈{undep})  [s]ort [/]filter  [r]en [a]rch [d]ep [D]epAll"
        )
        self.call_from_thread(self._render_remote)

    def _update_status(self, text: str) -> None:
        self.query_one("#status-bar", Static).update(text)

    # --- Remote view ---

    def _filter_match(self, *fields) -> bool:
        if not self._filter:
            return True
        needle = self._filter.lower()
        return any(needle in str(f).lower() for f in fields)

    def _render_remote(self) -> None:
        self._view = "remote"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Src", "Name", "Description", "Tags", "Age", "Size", "Tokens")

        label = self.query_one("#list-label", Static)
        skip = {"claude-code", "openclaw", "codex", "archived"}

        rows = []
        for t in self._remote_traces:
            tags = t.get("tags", [])
            if "archived" in tags:
                continue
            src_kind = "cc" if "claude-code" in tags else "oc" if "openclaw" in tags else ""
            tag_str = ", ".join([tg for tg in tags if tg not in skip])[:25]
            ts = t.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age = format_age(dt)
            except Exception:
                dt = None
                age = "?"
            meta = t.get("metadata", {}) or {}
            tok_in = meta.get("total_input_tokens", 0) or 0
            tok_out = meta.get("total_output_tokens", 0) or 0
            tok = f"{tok_in // 1000}k/{tok_out // 1000}k" if tok_in else ""
            size_bytes = (tok_in + tok_out) * 4
            approx_size = format_size(size_bytes) if size_bytes else "—"

            # Always strip source-matching prefix from Name — the badge already
            # conveys the source. Covers both tagged traces and ones with a
            # prefixed name but missing tag.
            raw_name = t.get("name", "unnamed")
            for prefix, kind in (("claude-code", "cc"), ("openclaw", "oc")):
                nl = raw_name.lower()
                if nl.startswith(prefix):
                    raw_name = raw_name[len(prefix):].lstrip(" -:")
                    if not src_kind:
                        src_kind = kind
                    if not raw_name:
                        raw_name = t.get("name", "unnamed")
                    break

            if not self._filter_match(raw_name, tag_str, src_kind):
                continue

            # Description: first user prompt (Langfuse 'input'), truncated.
            desc = (t.get("input") or "").strip().splitlines()[0] if t.get("input") else ""
            desc = desc[:50]

            # Rich-tinted cells (age color + size weight); badge column uses emoji.
            badge = src_badge(src_kind)
            name_cell = tint(raw_name[:30], dt, size_bytes)
            desc_cell = tint(desc, dt, size_bytes) if desc else Text("—", style="dim")
            age_cell = tint(age, dt, size_bytes)
            size_cell = tint(approx_size, dt, size_bytes)

            rows.append({
                "key": t.get("id", ""),
                "cells": (badge, name_cell, desc_cell, tag_str, age_cell, size_cell, tok),
                "sort": (src_kind, raw_name.lower(), desc, tag_str,
                         dt or datetime.min.replace(tzinfo=None),
                         size_bytes,
                         tok_in + tok_out),
            })

        rows = self._apply_sort(rows)
        for r in rows:
            table.add_row(*r["cells"], key=r["key"])
        # Fire initial preview for row 0 so right pane isn't empty on first load.
        try:
            if rows:
                table.move_cursor(row=0)
        except Exception:
            pass
        flt = f" filter={self._filter!r}" if self._filter else ""
        label.update(f"Remote ({len(rows)} shown / {self._remote_total or len(self._remote_traces)} total){flt}")
        table.focus()

    # --- Local view ---

    def _render_local(self) -> None:
        self._view = "local"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Src", "Project", "Description", "Size", "Age")

        rows = []
        for i, s in enumerate(self._local_sessions):
            src_kind = s["source"]
            project = s["project"][:20]
            desc = s.get("description") or s["session_id"][:8]
            size_str = format_size(s["size"])
            age_str = format_age(s["mtime"])

            if not self._filter_match(src_kind, project, s["session_id"], desc):
                continue

            badge = src_badge(src_kind)
            proj_cell = tint(project, s["mtime"], s["size"])
            desc_cell = tint(desc[:45], s["mtime"], s["size"]) if desc else Text("—", style="dim")
            size_cell = tint(size_str, s["mtime"], s["size"])
            age_cell = tint(age_str, s["mtime"], s["size"])

            rows.append({
                "key": str(i),
                "cells": (badge, proj_cell, desc_cell, size_cell, age_cell),
                "sort": (src_kind, project.lower(), desc.lower(),
                         s["size"], s["mtime"]),
            })

        rows = self._apply_sort(rows)
        for r in rows:
            table.add_row(*r["cells"], key=r["key"])
        # Fire initial preview for row 0 so right pane isn't empty on first load.
        try:
            if rows:
                table.move_cursor(row=0)
        except Exception:
            pass
        label = self.query_one("#list-label", Static)
        flt = f" filter={self._filter!r}" if self._filter else ""
        label.update(f"Local ({len(rows)} shown / {len(self._local_sessions)} total){flt}")
        table.focus()

    # --- Sorting & filtering ---

    def _apply_sort(self, rows):
        col, desc = self._sort.get(self._view, (0, False))
        try:
            return sorted(rows, key=lambda r: r["sort"][col], reverse=desc)
        except (IndexError, TypeError):
            return rows

    def action_cycle_sort(self) -> None:
        col, desc = self._sort.get(self._view, (0, False))
        # Toggle direction on same press; arrow keys would advance column — keep simple.
        self._sort[self._view] = (col, not desc)
        self._rerender()

    def action_filter_prompt(self) -> None:
        # Minimal: toggle filter on/off via a synchronous prompt in the detail pane.
        self.push_screen(FilterPromptScreen(self._filter), self._on_filter_set)

    def _on_filter_set(self, value) -> None:
        if value is None:
            return
        self._filter = value.strip()
        self._rerender()

    def _rerender(self) -> None:
        {"remote": self._render_remote, "local": self._render_local,
         "projects": self._render_projects, "stats": self._render_stats}.get(
            self._view, self._render_remote)()

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
        badge = src_badge(s["source"])
        log.write(f"[bold]{badge} {s['project']}[/]")
        if s.get("description"):
            log.write(f"  [italic cyan]{s['description']}[/]")
        log.write(f"  Session:   {s['session_id']}")
        log.write(f"  File:      {s['file']}")
        log.write(f"  Size:      {format_size(s['size'])}    Age: {format_age(s['mtime'])}")
        log.write(f"  Modified:  {s['mtime'].strftime('%Y-%m-%d %H:%M')}")
        log.write("")

        # Preview: first user message from the JSONL, plus analyzed summary if present.
        preview = _read_first_user_message(Path(s["file"]))
        if preview:
            log.write("[bold]First prompt:[/]")
            log.write(preview[:1200])
            log.write("")

        analyzed = _find_analyzed_md(s["session_id"], s["source"])
        if analyzed:
            log.write(f"[bold]Analyzed summary:[/]  [dim]{analyzed}[/]")
            try:
                body = analyzed.read_text()
                # Skip frontmatter
                if body.startswith("---"):
                    end = body.find("---", 3)
                    if end > 0:
                        body = body[end + 3:]
                log.write(body.strip()[:2500])
            except OSError as e:
                log.write(f"(could not read: {e})")

    def _show_project_detail(self, project: str) -> None:
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        sessions = [t for t in self._remote_traces if (t.get("metadata", {}) or {}).get("project") == project and "archived" not in t.get("tags", [])]
        log.write(f"[bold]Project: {project}[/]  ({len(sessions)} sessions)")
        log.write("")
        for t in sessions:
            ts = t.get("timestamp", "")
            try:
                when = format_age(datetime.fromisoformat(ts.replace("Z", "+00:00")))
            except Exception:
                when = "?"
            log.write(f"  {when}  {t.get('name', 'unnamed')}")

    # --- Actions ---

    # --- Stats / heatmap view ---

    def _render_stats(self) -> None:
        self._view = "stats"
        table = self.query_one("#session-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Metric", "Value")

        total_r = self._remote_total or len(self._remote_traces)
        total_l = len(self._local_sessions)
        undep = max(0, total_l - total_r)

        # Per-source split of loaded remote traces
        rc_cc = sum(1 for t in self._remote_traces if "claude-code" in t.get("tags", []))
        rc_oc = sum(1 for t in self._remote_traces if "openclaw" in t.get("tags", []))
        lc_cc = sum(1 for s in self._local_sessions if s["source"] == "cc")
        lc_oc = sum(1 for s in self._local_sessions if s["source"] == "oc")

        rows = [
            ("Remote total (Langfuse)",    f"{total_r:,}"),
            ("  claude-code (loaded)",     f"{rc_cc:,}"),
            ("  openclaw (loaded)",        f"{rc_oc:,}"),
            ("Local total",                f"{total_l:,}"),
            ("  🤖 claude-code",           f"{lc_cc:,}"),
            ("  🦀 openclaw",              f"{lc_oc:,}"),
            ("Undeposited (local − remote)", f"{undep:,}"),
        ]
        for k, v in rows:
            table.add_row(k, v, key=k)

        label = self.query_one("#list-label", Static)
        label.update("Stats")

        # Heatmap in the detail pane
        self._draw_heatmap()
        table.focus()

    def _draw_heatmap(self) -> None:
        """90-day activity heatmap using daily counts of local + remote sessions."""
        log = self.query_one("#detail-log", RichLog)
        log.clear()
        log.write("[bold]Activity heatmap — last 90 days[/]")
        log.write("(each cell = 1 day; ░ ▒ ▓ █ by count; ·=0)")
        log.write("")

        from datetime import timedelta
        now = datetime.now()
        today = now.date()
        days = [today - timedelta(days=i) for i in range(89, -1, -1)]  # oldest → newest

        counts = {d: 0 for d in days}
        # Local
        for s in self._local_sessions:
            d = s["mtime"].date()
            if d in counts:
                counts[d] += 1
        # Remote (loaded)
        for t in self._remote_traces:
            ts = t.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                d = dt.date()
                if d in counts:
                    counts[d] += 1
            except Exception:
                pass

        def block(n: int) -> str:
            if n == 0:   return "·"
            if n <= 2:   return "░"
            if n <= 8:   return "▒"
            if n <= 24:  return "▓"
            return "█"

        def color(n: int) -> str:
            if n == 0:   return "bright_black"
            if n <= 2:   return "green"
            if n <= 8:   return "yellow"
            if n <= 24:  return "orange3"
            return "red"

        # Arrange as weeks × weekdays (GitHub-style)
        # Start at the Monday of the earliest day, pad with ·
        first = days[0]
        pad = first.weekday()  # 0=Mon
        padded = [None] * pad + days
        # Transpose to weekday rows
        weeks = [padded[i:i + 7] for i in range(0, len(padded), 7)]

        weekday_label = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for wd in range(7):
            cells = []
            for week in weeks:
                if wd >= len(week) or week[wd] is None:
                    cells.append(" ")
                else:
                    d = week[wd]
                    n = counts.get(d, 0)
                    cells.append(f"[{color(n)}]{block(n)}[/]")
            log.write(f"  {weekday_label[wd]:<4}" + "".join(cells))

        # Totals
        total = sum(counts.values())
        active_days = sum(1 for v in counts.values() if v > 0)
        log.write("")
        log.write(f"total activity: {total} session-days  ·  active days: {active_days}/90")

    def action_show_remote(self) -> None:
        self._render_remote()

    def action_show_local(self) -> None:
        self._render_local()

    def action_show_stats(self) -> None:
        self._render_stats()

    @work(thread=True)
    def action_refresh(self) -> None:
        """Force-refresh: bypass cache and re-fetch everything."""
        self.call_from_thread(self._update_status, "Refreshing from Langfuse (bypassing cache)…")
        traces, total = api_get_paginated("/api/public/traces",
                                          max_pages=10, limit=100, use_cache=False)
        self._remote_traces = traces
        self._remote_total = total
        self._local_sessions = fetch_local_sessions()
        self.call_from_thread(self._update_status,
            f"Refreshed  [1]Remote {len(traces)}/{total}  [2]Local {len(self._local_sessions)}  "
            f"[3]Projects [4]Stats  [s]ort [/]filter [R]efresh")
        self.call_from_thread(self._rerender)

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
