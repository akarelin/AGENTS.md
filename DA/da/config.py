"""Configuration management for DeepAgents."""

import os
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


class Config(BaseModel):
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    temperature: float = 0
    hosts: dict[str, HostConfig] = {}
    projects: dict[str, str] = {}
    session: SessionConfig = SessionConfig()
    approval_required: list[str] = Field(default_factory=list)
    claude_history: str = ""
    debug: bool = False


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
