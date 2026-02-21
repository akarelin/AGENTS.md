"""
Configuration management for DeepAgents CLI

Follows zero-configuration philosophy with sensible defaults
and optional YAML overrides.
"""

import yaml
from pathlib import Path
from typing import Any, Dict
import os

# Default configuration with sensible defaults
DEFAULT_CONFIG: Dict[str, Any] = {
    # Model configuration
    'model': os.environ.get('DEEPAGENTS_MODEL', 'openai:gpt-4o'),
    
    # Observability
    'debug': False,
    'trace': True,
    'snapshot_enabled': True,
    'snapshot_dir': './snapshots',
    
    # Persistence
    'persistence_backend': 'sqlite',
    'db_path': './deepagents.db',
    'postgres_conn_string': os.environ.get('POSTGRES_CONN_STRING'),
    
    # Human-in-the-loop
    'auto_approve': False,
    'approval_tools': [
        'git_push_tool',
        'archive_tool',
    ],
    
    # Breakpoints
    'breakpoints': [],
    
    # Paths
    'repo_root': os.getcwd(),
    'todo_file': '2Do.md',
    'roadmap_file': 'ROADMAP.md',
    'changelog_file': 'CHANGELOG.md',
    'changelog_verbose_file': 'CHANGELOG_verbose.md',
    'mistakes_file': 'AGENTS_mistakes.md',
    
    # Prompts
    'prompts_dir': Path(__file__).parent / 'prompts',
    
    # Git
    'git_auto_detect': True,
    'git_require_changelog': True,
}


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Configuration dictionary with defaults merged
    """
    config = DEFAULT_CONFIG.copy()
    
    with open(config_path, 'r') as f:
        user_config = yaml.safe_load(f)
    
    if user_config:
        config.update(user_config)
    
    return config


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save YAML file
    """
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_prompt(config: Dict[str, Any], prompt_name: str) -> str:
    """
    Load a prompt from the prompts directory.
    
    Args:
        config: Configuration dictionary
        prompt_name: Name of the prompt file (without .md extension)
        
    Returns:
        Prompt content as string
    """
    prompts_dir = Path(config['prompts_dir'])
    prompt_path = prompts_dir / f"{prompt_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    
    return prompt_path.read_text()


def get_tool_prompt(config: Dict[str, Any], tool_name: str) -> str:
    """
    Load a tool-specific prompt.
    
    Args:
        config: Configuration dictionary
        tool_name: Name of the tool
        
    Returns:
        Tool prompt content as string
    """
    prompts_dir = Path(config['prompts_dir'])
    prompt_path = prompts_dir / 'tools' / f"{tool_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Tool prompt not found: {prompt_path}")
    
    return prompt_path.read_text()


def get_workflow_prompt(config: Dict[str, Any], workflow_name: str) -> str:
    """
    Load a workflow-specific prompt.
    
    Args:
        config: Configuration dictionary
        workflow_name: Name of the workflow
        
    Returns:
        Workflow prompt content as string
    """
    prompts_dir = Path(config['prompts_dir'])
    prompt_path = prompts_dir / 'workflows' / f"{workflow_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Workflow prompt not found: {prompt_path}")
    
    return prompt_path.read_text()
