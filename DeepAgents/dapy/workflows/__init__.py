"""
Workflows for DeepAgents CLI

Complex multi-step workflows implemented as LangGraph state machines.
These workflows orchestrate multiple tools and handle complex logic.
"""

from deepagents.workflows.close_session import run_close_session_workflow
from deepagents.workflows.document_changes import run_document_changes_workflow
from deepagents.workflows.whats_next import run_whats_next_workflow

__all__ = [
    'run_close_session_workflow',
    'run_document_changes_workflow',
    'run_whats_next_workflow',
]
