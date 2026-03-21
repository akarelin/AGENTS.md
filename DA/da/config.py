"""Configuration management for DeepAgents."""

import os
import platform
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class HostConfig(BaseModel):
    ssh: str
    roles: list[str] = []


class SessionConfig(BaseModel):
    persist: bool = True
    db_path: str = "~/.da/sessions.db"
    history_dir: str = "~/.da/history"


class DevRootConfig(BaseModel):
    wsl: str = "~"
    linux: str = "~"
    windows: str = "D:\\Dev"


def _detect_platform() -> str:
    """Detect current platform: 'wsl', 'linux', or 'windows'."""
    if "microsoft" in platform.release().lower() or "WSL_DISTRO_NAME" in os.environ:
        return "wsl"
    if os.name == "nt":
        return "windows"
    return "linux"


class Config(BaseModel):
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    temperature: float = 0
    hosts: dict[str, HostConfig] = {}
    dev_root: DevRootConfig = DevRootConfig()
    projects: dict[str, str] = {}
    session: SessionConfig = SessionConfig()
    approval_required: list[str] = Field(default_factory=list)
    claude_history: str = ""
    debug: bool = False

    @property
    def current_dev_root(self) -> str:
        """Get dev root for current platform, expanded."""
        plat = _detect_platform()
        raw = getattr(self.dev_root, plat, self.dev_root.linux)
        return str(Path(raw).expanduser())

    @property
    def current_platform(self) -> str:
        return _detect_platform()


def load_config(config_path: str | None = None) -> Config:
    """Load config from YAML, falling back to defaults."""
    paths_to_try = [
        config_path,
        os.environ.get("DA_CONFIG"),
        str(Path.cwd() / "config.yaml"),
        str(Path.home() / ".da" / "config.yaml"),
        str(Path(__file__).parent.parent / "config.yaml"),
    ]

    for p in paths_to_try:
        if p and Path(p).exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            return Config(**data)

    return Config()
