"""Config Editor Rich view — YAML config browser/editor.

Menu: [C]onfig  |  F4  |  /config

Uses gppu.tui.config_editor for file discovery and validation.
Integrates into DA TUI via Textual widgets (Tree + RichLog + TextArea).
"""

from __future__ import annotations

import os
from pathlib import Path

from gppu.tui.config_editor import (
    collect_yaml_targets,
    find_direct_includes,
    validate_yaml,
)

from da.config import Config

MENU_KEY = "C"
MENU_LABEL = "onfig"


class ConfigEditorView:
    """YAML config editor integrated into DA TUI.

    Widget references (tree, preview, editor, status_label) are set
    by the host TUI after compose().
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._root_config: Path | None = None
        self._project_root: Path | None = None
        self._files: list[Path] = []
        self._file_map: dict[str, Path] = {}
        self._editing: Path | None = None

        # Widget refs — set by host TUI
        self.tree = None
        self.preview = None
        self.editor = None
        self.status_label = None

        self._find_config()

    # ── Config discovery ──────────────────────────────────────────

    def _find_config(self) -> None:
        paths = [
            Path(__file__).resolve().parent.parent.parent / "config.yaml",
            Path.cwd() / "config.yaml",
            Path.home() / ".da" / "config.yaml",
        ]
        env = os.environ.get("DA_CONFIG")
        if env:
            paths.insert(0, Path(env))

        for p in paths:
            if p.exists():
                self._root_config = p.resolve()
                self._project_root = p.parent
                return

    # ── Show / refresh ────────────────────────────────────────────

    def show(self) -> None:
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self._root_config or not self.tree:
            return

        self._files = collect_yaml_targets(self._root_config)
        self.tree.clear()
        self.tree.root.expand()
        self._file_map.clear()

        groups: dict[str, list[tuple[str, Path]]] = {}
        for fp in self._files:
            try:
                rel = fp.relative_to(self._project_root)
            except ValueError:
                rel = fp
            parts = str(rel).replace("\\", "/").split("/")
            if len(parts) > 1:
                group = "/".join(parts[:-1])
                name = parts[-1]
            else:
                group = "."
                name = parts[0]
            groups.setdefault(group, []).append((name, fp))

        for group, items in groups.items():
            if group == ".":
                parent = self.tree.root
            else:
                parent = self.tree.root.add(f"\U0001f4c1 {group}")
                parent.expand()
            for name, fp in items:
                node_id = f"file:{fp}"
                self._file_map[node_id] = fp
                label = name if fp.exists() else f"{name} [missing]"
                parent.add_leaf(label, data=node_id)

    # ── Preview ───────────────────────────────────────────────────

    def show_preview(self, fp: Path) -> None:
        if not self.preview:
            return
        self.preview.clear()

        try:
            rel = fp.relative_to(self._project_root)
        except ValueError:
            rel = fp
        self.preview.write(f"[bold]{rel}[/bold]")

        valid, error = validate_yaml(fp)
        if valid:
            self.preview.write("[green]\u2713 Valid YAML[/green]")
        else:
            self.preview.write(f"[red]\u2717 {error}[/red]")
        self.preview.write("")

        if not fp.exists():
            self.preview.write("[dim]File does not exist[/dim]")
            return

        try:
            content = fp.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines()[:100], 1):
                self.preview.write(f'[dim]{i:>4}[/dim]  {line.replace("[", "\\[")}')
            total = content.count("\n")
            if total > 100:
                self.preview.write(f"[dim]  ... ({total} total lines)[/dim]")
        except OSError as e:
            self.preview.write(f"[red]Error reading: {e}[/red]")

        includes = find_direct_includes(fp)
        if includes:
            self.preview.write("")
            self.preview.write("[bold]Includes:[/bold]")
            for inc in includes:
                icon = "[green]\u2713[/green]" if inc.exists() else "[red]\u2717[/red]"
                try:
                    r = inc.relative_to(self._project_root)
                except ValueError:
                    r = inc
                self.preview.write(f"  {icon} {r}")

    # ── Inline editing ────────────────────────────────────────────

    def start_edit(self, fp: Path) -> bool:
        if not self.editor or not fp.exists():
            return False

        try:
            content = fp.read_text(encoding="utf-8")
        except OSError:
            return False

        self._editing = fp
        self.editor.load_text(content)
        self.editor.add_class("visible")
        if self.preview:
            self.preview.display = False

        try:
            rel = fp.relative_to(self._project_root)
        except ValueError:
            rel = fp
        if self.status_label:
            self.status_label.update(f"Editing: {rel}  |  Esc: save & close")
        return True

    def save_and_close(self) -> tuple[bool, str]:
        if not self._editing or not self.editor:
            return False, ""

        fp = self._editing
        content = self.editor.text

        try:
            fp.write_text(content, encoding="utf-8")
        except OSError as e:
            return False, f"Save failed: {e}"

        valid, error = validate_yaml(fp)

        self._editing = None
        self.editor.remove_class("visible")
        if self.preview:
            self.preview.display = True
        self.show_preview(fp)
        if self.status_label:
            self.status_label.update("Preview")

        if valid:
            return True, f"\u2713 Saved {fp.name}"
        return False, f"\u2717 Saved {fp.name} \u2014 {error}"

    def validate_all(self) -> list[tuple[Path, bool, str | None]]:
        results = []
        for fp in self._files:
            if fp.exists():
                valid, error = validate_yaml(fp)
                results.append((fp, valid, error))
        return results

    @property
    def is_editing(self) -> bool:
        return self._editing is not None

    def get_file_for_node(self, node_data: str | None) -> Path | None:
        if node_data and node_data.startswith("file:"):
            return self._file_map.get(node_data)
        return None

    def handle_input(self, text: str) -> None:
        """Handle slash commands in config view."""
        if not text.startswith("/"):
            return
        parts = text.split(None, 1)
        cmd = parts[0].lower()

        if cmd == "/validate":
            if not self.preview:
                return
            self.preview.clear()
            self.preview.write("[bold]Validating all files...[/bold]\n")
            ok = fail = 0
            for fp, valid, error in self.validate_all():
                try:
                    rel = fp.relative_to(self._project_root)
                except ValueError:
                    rel = fp
                if valid:
                    self.preview.write(f"  [green]\u2713[/green] {rel}")
                    ok += 1
                else:
                    self.preview.write(f"  [red]\u2717[/red] {rel}: {error}")
                    fail += 1
            self.preview.write(f"\n[bold]{ok} passed, {fail} failed[/bold]")
        elif cmd == "/refresh":
            self.refresh_tree()
