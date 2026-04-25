#!/usr/bin/env python3
"""Launcher entrypoint for the SessionSkills orchestrator.

The gppu TUI launcher invokes scripts as `python <path>`, but
sessions.orchestrator uses package-relative imports. This shim adds the
repo root to sys.path so `from sessions.orchestrator import main` resolves.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sessions.orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
