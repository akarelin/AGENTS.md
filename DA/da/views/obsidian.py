"""Obsidian view — browse and search Obsidian vault.

Menu: [O]bsidian  |  F3  |  /obsidian

TODO: To be built by another agent. Planned features:
  - Browse vault notes by folder
  - Full-text search across vault
  - Preview note content with Markdown rendering
  - Quick open / edit note
  - Tag browser
  - Recent notes
"""

from prompt_toolkit.formatted_text import HTML

from da.config import Config
from da.rich_render import console, render_tool

MENU_KEY = "O"
MENU_LABEL = "Obsidian"


class ObsidianView:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.vault_path = getattr(cfg, "obsidian_vault", None) or ""

    def get_prompt(self) -> HTML:
        return HTML("<ansimagenta><b>obsidian</b></ansimagenta> <ansigray>\u203a</ansigray> ")

    def show(self) -> None:
        """Called when switching to this view."""
        console.print(render_tool(
            "Obsidian view (stub)\n"
            f"  Vault: {self.vault_path or 'not configured'}\n"
            "  This view is a placeholder \u2014 to be built by another agent."
        ))

    def handle_input(self, text: str) -> None:
        """Handle input in Obsidian view."""
        console.print(render_tool("Obsidian view not yet implemented."))
