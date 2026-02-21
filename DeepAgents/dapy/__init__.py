"""
DAPY - Deep Agents in PYthon

Production-ready personal knowledge management system

Built with LangChain 1.0 and LangGraph 1.0, featuring:
- Observability with LangSmith tracing
- Human-in-the-loop controls
- Breakpoints and snapshots for debugging
- Durable state persistence
- Multi-environment deployment (GCP, Docker, LangChain Cloud)
"""

__version__ = "0.1.0"

from dapy.orchestrator import create_main_agent, create_specialized_agent
from dapy.config import load_config, DEFAULT_CONFIG
from dapy.observability import setup_tracing
from dapy.persistence import get_checkpointer

__all__ = [
    'create_main_agent',
    'create_specialized_agent',
    'load_config',
    'DEFAULT_CONFIG',
    'setup_tracing',
    'get_checkpointer',
]
