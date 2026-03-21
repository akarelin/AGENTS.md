"""Rich TUI view modules — one per top-level menu item.

Each view module exposes:
  - MENU_KEY: str          — shortcut letter for the menu bar
  - MENU_LABEL: str        — display label (e.g. "ДА", "Sessions", "Obsidian")
  - View class             — with handle_input(text), show(), get_prompt() methods
"""
