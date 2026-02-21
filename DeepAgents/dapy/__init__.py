"""
DeepAgents CLI - Production-ready personal knowledge management system

Built with LangChain 1.0 and LangGraph 1.0, featuring:
- Observability with LangSmith tracing
- Human-in-the-loop controls
- Breakpoints and snapshots for debugging
- Durable state persistence
- Multi-environment deployment (GCP, Docker, LangChain Cloud)
"""

__version__ = "0.1.0"

from deepagents.orchestrator import create_main_agent, create_specialized_agent
from deepagents.config import load_config, DEFAULT_CONFIG
from deepagents.observability import setup_tracing
from deepagents.persistence import get_checkpointer

__all__ = [
    'create_main_agent',
    'create_specialized_agent',
    'load_config',
    'DEFAULT_CONFIG',
    'setup_tracing',
    'get_checkpointer',
]
