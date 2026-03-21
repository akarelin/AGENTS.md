"""Config Editor Rich view — YAML config browser/editor + tools/agents viewer.

Menu: [C]onfig  |  F4  |  /config

Uses gppu.tui.config_editor for file discovery and validation.
Integrates into DA TUI via Textual widgets (Tree + RichLog + TextArea).

Tree layout:
  \u2699 Tools
    \u2514 shell
      \u2514 shell_exec
    \u2514 git
      \u2514 git_status  ...
  \U0001f916 Agents
    \u2514 orchestrator
    \u2514 infra  ...
  \U0001f4c1 Config
    \u2514 config.yaml
"""

from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path

from gppu.tui.config_editor import (
    collect_yaml_targets,
    find_direct_includes,
    validate_yaml,
)

from da.config import Config
from da.tools import ALL_TOOL_DEFS, EXECUTORS
from da.agents import AGENT_TYPES

MENU_KEY = "C"
MENU_LABEL = "onfig"

# ── Tool introspection ────────────────────────────────────────────

# Map tool name -> module name (category) for grouping
_TOOL_MODULES = {
    "shell": "da.tools.shell",
    "git": "da.tools.git",
    "docker": "da.tools.docker",
    "ssh": "da.tools.ssh",
    "files": "da.tools.files",
    "search": "da.tools.search",
    "sessions": "da.tools.sessions",
}


def _tool_category(tool_name: str) -> str:
    """Derive category from executor mapping."""
    executor = EXECUTORS.get(tool_name)
    if not executor:
        return "unknown"
    mod = executor.__module__
    # da.tools.shell -> shell
    return mod.rsplit(".", 1)[-1] if "." in mod else mod


def _group_tools() -> dict[str, list[dict]]:
    """Group ALL_TOOL_DEFS by category."""
    groups: dict[str, list[dict]] = {}
    for t in ALL_TOOL_DEFS:
        cat = _tool_category(t["name"])
        groups.setdefault(cat, []).append(t)
    return groups


def _get_agent_prompt(agent_type: str) -> str | None:
    """Load system prompt for an agent type."""
    try:
        mod = importlib.import_module(f"da.agents.{agent_type}")
        return getattr(mod, "SYSTEM_PROMPT", None)
    except (ImportError, ModuleNotFoundError):
        return None


def _get_agent_prompt_func(agent_type: str):
    """Load get_system_prompt function if available."""
    try:
        mod = importlib.import_module(f"da.agents.{agent_type}")
        return getattr(mod, "get_system_prompt", None)
    except (ImportError, ModuleNotFoundError):
        return None


class ConfigEditorView:
    """YAML config editor + tools/agents browser for DA TUI.

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
        if not self.tree:
            return

        self.tree.clear()
        self.tree.root.expand()
        self._file_map.clear()

        # ── Tools section ──
        tools_node = self.tree.root.add("\u2699\ufe0f Tools")
        tools_node.expand()
        tool_groups = _group_tools()
        for cat in sorted(tool_groups):
            cat_node = tools_node.add(f"\U0001f4e6 {cat}")
            for t in tool_groups[cat]:
                name = t["name"]
                cat_node.add_leaf(name, data=f"tool:{name}")

        # ── Agents section ──
        agents_node = self.tree.root.add("\U0001f916 Agents")
        agents_node.expand()
        for agent_type in AGENT_TYPES:
            has_impl = _get_agent_prompt(agent_type) is not None
            label = agent_type if has_impl else f"{agent_type} [dim](stub)[/dim]"
            agents_node.add_leaf(label, data=f"agent:{agent_type}")

        # ── Config files section ──
        if self._root_config:
            self._files = collect_yaml_targets(self._root_config)
            config_node = self.tree.root.add("\U0001f4c1 Config")
            config_node.expand()

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
                    parent = config_node
                else:
                    parent = config_node.add(f"\U0001f4c1 {group}")
                    parent.expand()
                for name, fp in items:
                    node_id = f"file:{fp}"
                    self._file_map[node_id] = fp
                    label = name if fp.exists() else f"{name} [missing]"
                    parent.add_leaf(label, data=node_id)

    # ── Node dispatch ─────────────────────────────────────────────

    def show_node(self, node_data: str | None) -> None:
        """Show preview for any tree node type."""
        if not node_data:
            return
        if node_data.startswith("tool:"):
            self._show_tool(node_data[5:])
        elif node_data.startswith("agent:"):
            self._show_agent(node_data[6:])
        elif node_data.startswith("file:"):
            fp = self._file_map.get(node_data)
            if fp:
                self.show_preview(fp)

    # ── Tool preview ──────────────────────────────────────────────

    def _show_tool(self, name: str) -> None:
        if not self.preview:
            return
        self.preview.clear()

        tool_def = next((t for t in ALL_TOOL_DEFS if t["name"] == name), None)
        if not tool_def:
            self.preview.write(f"[red]Tool not found: {name}[/red]")
            return

        cat = _tool_category(name)
        self.preview.write(f"[bold cyan]\u2699 {name}[/bold cyan]  [dim]({cat})[/dim]")
        self.preview.write("")
        self.preview.write(f"[bold]Description:[/bold] {tool_def['description']}")
        self.preview.write("")

        # Source module
        executor = EXECUTORS.get(name)
        if executor:
            mod = executor.__module__
            try:
                src = Path(inspect.getfile(inspect.getmodule(executor)))
                self.preview.write(f"[dim]Source: {src.name}[/dim]")
            except (TypeError, AttributeError):
                self.preview.write(f"[dim]Module: {mod}[/dim]")

        # Input schema
        schema = tool_def.get("input_schema", {})
        props = schema.get("properties", {})
        required = set(schema.get("required", []))

        if props:
            self.preview.write("")
            self.preview.write("[bold]Parameters:[/bold]")
            for pname, pdef in props.items():
                req = "[red]*[/red]" if pname in required else " "
                ptype = pdef.get("type", "any")
                desc = pdef.get("description", "")
                default = pdef.get("default")
                line = f"  {req} [cyan]{pname}[/cyan] [dim]({ptype})[/dim]"
                if default is not None:
                    line += f" [dim]= {default}[/dim]"
                self.preview.write(line)
                if desc:
                    self.preview.write(f"      [dim]{desc}[/dim]")

            self.preview.write("")
            self.preview.write("[dim]  * = required[/dim]")

    # ── Agent preview ─────────────────────────────────────────────

    def _show_agent(self, agent_type: str) -> None:
        if not self.preview:
            return
        self.preview.clear()

        self.preview.write(f"[bold magenta]\U0001f916 {agent_type}[/bold magenta]")
        self.preview.write("")

        # Check for implementation
        prompt = _get_agent_prompt(agent_type)
        prompt_func = _get_agent_prompt_func(agent_type)

        if prompt is None and prompt_func is None:
            self.preview.write("[yellow]Not implemented[/yellow] \u2014 stub entry in agent registry")
            self.preview.write("")
            self.preview.write("[dim]Agent types defined in da/agents/__init__.py[/dim]")
            return

        # Source file
        try:
            mod = importlib.import_module(f"da.agents.{agent_type}")
            src = Path(inspect.getfile(mod))
            self.preview.write(f"[dim]Source: {src.name}[/dim]")
        except (ImportError, TypeError):
            pass

        if prompt_func:
            self.preview.write("[dim]Has dynamic prompt: get_system_prompt(config)[/dim]")

        # Show system prompt
        if prompt:
            self.preview.write("")
            self.preview.write("[bold]System Prompt:[/bold]")
            self.preview.write("")
            for i, line in enumerate(prompt.splitlines()[:80], 1):
                self.preview.write(
                    f'[dim]{i:>4}[/dim]  {line.replace("[", "\\[")}'
                )
            total = prompt.count("\n")
            if total > 80:
                self.preview.write(f"[dim]  ... ({total} total lines)[/dim]")

    # ── Config file preview ───────────────────────────────────────

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

    # ── Inline editing (config files only) ────────────────────────

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

    def get_node_data(self, node_data: str | None) -> str | None:
        """Return node data if it's a recognized type."""
        if not node_data:
            return None
        if node_data.startswith(("tool:", "agent:", "file:")):
            return node_data
        return None

    def get_file_for_node(self, node_data: str | None) -> Path | None:
        if node_data and node_data.startswith("file:"):
            return self._file_map.get(node_data)
        return None

    def is_editable_node(self, node_data: str | None) -> bool:
        """Only config file nodes are editable."""
        return bool(node_data and node_data.startswith("file:"))

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
