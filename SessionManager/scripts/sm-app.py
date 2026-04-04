"""
SessionManager — TUI superapp launcher.

Top-level menu for all session management tools.

Usage:
    sm-app                    # interactive TUI launcher
    sm-app sessions           # launch sessions CLI directly
    sm-app local              # launch local manager directly
    sm-app --list             # list available apps
"""

from __future__ import annotations

from pathlib import Path

from gppu import Env
from gppu.tui import TUILauncher, launcher_main, load_app_registry

APP_DIR = Path(__file__).resolve().parent.parent


class SessionManagerLauncher(TUILauncher):
    TITLE = 'Session Manager'
    MENU_TITLE = 'Session Manager'

    CSS = TUILauncher.CSS + """
    Screen {
        align: center top;
    }
    #menu {
        width: 1fr;
        max-height: 100%;
        margin: 0;
        border: none;
        padding: 1 4;
    }
    """


def main() -> None:
    Env.from_env(name='session-manager', app_path=APP_DIR)
    apps = load_app_registry(APP_DIR)
    launcher_main(apps, SessionManagerLauncher, APP_DIR, 'Session Manager — LLM session management')


if __name__ == '__main__':
    main()
