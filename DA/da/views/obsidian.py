"""Obsidian Rich view — interactive vault browser via output callbacks.

Menu: [O]bsidian  |  F3  |  /obsidian

Full interactive browser: folders, notes, markdown preview, search, tags.
All vault logic lives in da.obsidian; this file only does Rich rendering.
"""

from pathlib import Path
from typing import Callable

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from da.config import Config
from da.obsidian import (
    vault_path,
    list_folders,
    list_notes,
    recent_notes,
    search,
    read_note,
    extract_tags,
    note_info,
    NoteInfo,
    FolderInfo,
)

MENU_KEY = "O"
MENU_LABEL = "bsidian"


def _hint(text: str):
    return Text(f"  \u2192 {text}", style="dim italic")


class ObsidianView:
    """Interactive Obsidian vault browser for Rich-based UIs.

    All rendering goes through self.output(renderable).
    State is tracked so bare numbers and /back work.
    """

    def __init__(self, cfg: Config, output: Callable | None = None, clear: Callable | None = None):
        self.cfg = cfg
        self.vault = vault_path(cfg)
        self.output = output or (lambda x: None)
        self.clear = clear or (lambda: None)
        # Navigation state
        self._mode = "home"  # home | folder | note | search | tags
        self._current_folder: Path | None = None
        self._note_index: list[NoteInfo] = []
        self._folder_index: list[FolderInfo] = []

    # ── Home ──────────────────────────────────────────────────────

    def show(self) -> None:
        if not self.vault.exists():
            self.output(_hint(f"Vault not found: {self.vault}"))
            return
        self._mode = "home"
        self._show_home()

    def _show_home(self) -> None:
        self.clear()
        folders = list_folders(self.vault)
        self._folder_index = folders

        t = Table(title=f"Obsidian: {self.vault.name}", show_edge=False, pad_edge=False)
        t.add_column("#", style="dim", width=3)
        t.add_column("Folder", style="cyan bold")
        t.add_column("Notes", style="dim", justify="right", width=6)
        for i, f in enumerate(folders, 1):
            t.add_row(str(i), f.name, str(f.note_count))
        self.output(t)

        recent = recent_notes(self.vault, limit=10)
        self._note_index = recent
        if recent:
            rt = Table(title="Recent Notes", show_edge=False, pad_edge=False)
            rt.add_column("#", style="dim", width=3)
            rt.add_column("Note", style="green")
            rt.add_column("Folder", style="dim")
            rt.add_column("Modified", style="dim", width=12)
            for i, n in enumerate(recent, 1):
                rt.add_row(str(i), n.name, n.folder, n.mtime_short)
            self.output(rt)

        self.output(_hint(
            "<#> folder | <#> note | /search <q> | /tags | /recent"
        ))

    # ── Folder listing ────────────────────────────────────────────

    def _show_folder(self, folder: Path) -> None:
        self.clear()
        self._mode = "folder"
        self._current_folder = folder
        notes = list_notes(folder, self.vault)
        self._note_index = notes

        try:
            rel = folder.relative_to(self.vault)
        except ValueError:
            rel = folder
        t = Table(title=f"{rel}/", show_edge=False, pad_edge=False)
        t.add_column("#", style="dim", width=3)
        t.add_column("Note", style="green")
        t.add_column("Size", style="dim", justify="right", width=8)
        t.add_column("Modified", style="dim", width=12)
        for i, n in enumerate(notes[:50], 1):
            sz = f"{n.size:,}" if n.size < 10000 else f"{n.size // 1024}k"
            t.add_row(str(i), n.name, sz, n.mtime_short)
        self.output(t)

        # Show subfolders
        subdirs = [d for d in sorted(folder.iterdir())
                   if d.is_dir() and not d.name.startswith(".") and d.name not in (".obsidian",)]
        if subdirs:
            self.output(_hint("Subfolders: " + ", ".join(d.name for d in subdirs)))

        self.output(_hint("<#> to read | /back | /search <q>"))

    # ── Note preview ──────────────────────────────────────────────

    def _show_note(self, info: NoteInfo) -> None:
        self.clear()
        self._mode = "note"
        try:
            content = read_note(info.path)
        except Exception as e:
            self.output(_hint(f"Error: {e}"))
            return

        tags = extract_tags(content)

        # Metadata line
        meta = Text()
        meta.append(f"{info.folder}/{info.name}.md" if info.folder else f"{info.name}.md", style="dim")
        meta.append(f"  |  {info.size:,}b  |  {info.mtime_str}", style="dim")
        if tags:
            meta.append("  |  ", style="dim")
            for tag in tags[:10]:
                meta.append(f"#{tag} ", style="cyan")
        self.output(meta)

        # Markdown rendered content
        try:
            md = Markdown(content, code_theme="monokai")
            self.output(Panel(md, border_style="dim", padding=(0, 1)))
        except Exception:
            self.output(Panel(Text(content), border_style="dim", padding=(0, 1)))

        self.output(_hint("/back | <#> from previous list"))

    # ── Search ────────────────────────────────────────────────────

    def _show_search(self, query: str) -> None:
        self.clear()
        self._mode = "search"
        results = search(self.vault, query)
        self._note_index = [r.note for r in results]

        if not results:
            self.output(_hint(f"No results for: {query}"))
            return

        t = Table(title=f'Search: "{query}" ({len(results)})', show_edge=False, pad_edge=False)
        t.add_column("#", style="dim", width=3)
        t.add_column("Note", style="green")
        t.add_column("Folder", style="dim")
        t.add_column("Match", style="yellow", max_width=60)
        for i, r in enumerate(results, 1):
            t.add_row(str(i), r.note.name, r.note.folder, r.context)
        self.output(t)
        self.output(_hint("<#> to read | /back"))

    # ── Tags ──────────────────────────────────────────────────────

    def _show_tags(self) -> None:
        self.clear()
        self._mode = "tags"
        from da.obsidian import _iter_notes
        tag_counts: dict[str, int] = {}
        for p in _iter_notes(self.vault):
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                for tag in extract_tags(content):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                continue
        if not tag_counts:
            self.output(_hint("No tags found."))
            return

        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
        t = Table(title=f"Tags ({len(sorted_tags)})", show_edge=False, pad_edge=False)
        t.add_column("Tag", style="cyan")
        t.add_column("Count", style="dim", justify="right", width=5)
        for tag, count in sorted_tags[:60]:
            t.add_row(f"#{tag}", str(count))
        self.output(t)
        self.output(_hint("/tag <name> | /back"))

    def _show_tag_notes(self, tag: str) -> None:
        self.clear()
        self._mode = "search"
        from da.obsidian import _iter_notes
        notes = []
        for p in _iter_notes(self.vault):
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                if f"#{tag}" in content:
                    notes.append(note_info(p, self.vault))
            except Exception:
                continue
        self._note_index = notes
        if not notes:
            self.output(_hint(f"No notes with #{tag}"))
            return
        t = Table(title=f"#{tag} ({len(notes)})", show_edge=False, pad_edge=False)
        t.add_column("#", style="dim", width=3)
        t.add_column("Note", style="green")
        t.add_column("Folder", style="dim")
        for i, n in enumerate(notes, 1):
            t.add_row(str(i), n.name, n.folder)
        self.output(t)
        self.output(_hint("<#> to read | /back"))

    # ── Input dispatch ────────────────────────────────────────────

    def handle_input(self, text: str) -> None:
        text = text.strip()
        if not text:
            return

        # Slash commands
        if text.startswith("/"):
            parts = text.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/back":
                if self._mode in ("note", "search", "tags"):
                    if self._current_folder:
                        self._show_folder(self._current_folder)
                    else:
                        self._show_home()
                elif self._mode == "folder":
                    self._show_home()
                else:
                    self._show_home()
            elif cmd == "/search":
                if arg:
                    self._show_search(arg)
                else:
                    self.output(_hint("Usage: /search <query>"))
            elif cmd == "/tags":
                self._show_tags()
            elif cmd == "/tag":
                if arg:
                    self._show_tag_notes(arg)
                else:
                    self.output(_hint("Usage: /tag <name>"))
            elif cmd == "/recent":
                self.clear()
                notes = recent_notes(self.vault, limit=30)
                self._note_index = notes
                t = Table(title="Recent Notes", show_edge=False, pad_edge=False)
                t.add_column("#", style="dim", width=3)
                t.add_column("Note", style="green")
                t.add_column("Folder", style="dim")
                t.add_column("Modified", style="dim", width=12)
                for i, n in enumerate(notes, 1):
                    t.add_row(str(i), n.name, n.folder, n.mtime_short)
                self.output(t)
                self.output(_hint("<#> to read | /back"))
            elif cmd in ("/vault", "/home"):
                self._show_home()
            else:
                self.output(_hint(f"Unknown: {cmd}. Try /search, /tags, /recent, /back"))
            return

        # Bare number — context-dependent selection
        if text.isdigit():
            idx = int(text) - 1
            if self._mode == "home" and self._folder_index and idx < len(self._folder_index):
                self._show_folder(self._folder_index[idx].path)
            elif self._note_index and 0 <= idx < len(self._note_index):
                self._show_note(self._note_index[idx])
            else:
                self.output(_hint(f"Invalid index: {text}"))
            return

        # Folder name match from home
        if self._mode == "home":
            for f in self._folder_index:
                if f.name.lower() == text.lower():
                    self._show_folder(f.path)
                    return

        # Fallback: search
        if len(text) > 1:
            self._show_search(text)
        else:
            self.output(_hint("<#> | /search <q> | /tags | /back"))
