"""
Tools for DeepAgents CLI

Each tool is a LangChain tool migrated from the original markdown-based subagents.
Tools are organized by function and can be composed into specialized agent toolsets.
"""

from typing import Any, Dict, List
from deepagents.tools.changelog import changelog_tool
from deepagents.tools.archive import archive_tool
from deepagents.tools.mistake_processor import mistake_processor_tool
from deepagents.tools.validation import validation_tool
from deepagents.tools.git_operations import git_push_tool, git_status_tool, git_diff_tool
from deepagents.tools.knowledge_base import (
    read_markdown_tool,
    search_markdown_tool,
    update_markdown_tool,
)


def get_all_tools(config: Dict[str, Any]) -> List[Any]:
    """
    Get all available tools for the main agent.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of all LangChain tools
    """
    return [
        # Changelog management
        changelog_tool,
        
        # Code archival
        archive_tool,
        
        # Mistake processing
        mistake_processor_tool,
        
        # Validation
        validation_tool,
        
        # Git operations
        git_push_tool,
        git_status_tool,
        git_diff_tool,
        
        # Knowledge base
        read_markdown_tool,
        search_markdown_tool,
        update_markdown_tool,
    ]


def get_tools_for_agent(agent_type: str, config: Dict[str, Any]) -> List[Any]:
    """
    Get tools for a specialized agent.
    
    Args:
        agent_type: Type of agent ('changelog', 'archive', 'validation', etc.)
        config: Configuration dictionary
        
    Returns:
        List of tools relevant to this agent type
    """
    tool_sets = {
        'changelog': [
            changelog_tool,
            git_status_tool,
            git_diff_tool,
            read_markdown_tool,
            update_markdown_tool,
        ],
        'archive': [
            archive_tool,
            git_status_tool,
            read_markdown_tool,
            update_markdown_tool,
        ],
        'validation': [
            validation_tool,
            read_markdown_tool,
            git_diff_tool,
        ],
        'push': [
            git_push_tool,
            git_status_tool,
            changelog_tool,
            read_markdown_tool,
        ],
        'mistake_review': [
            mistake_processor_tool,
            read_markdown_tool,
            update_markdown_tool,
        ],
    }
    
    return tool_sets.get(agent_type, get_all_tools(config))


__all__ = [
    'get_all_tools',
    'get_tools_for_agent',
    'changelog_tool',
    'archive_tool',
    'mistake_processor_tool',
    'validation_tool',
    'git_push_tool',
    'git_status_tool',
    'git_diff_tool',
    'read_markdown_tool',
    'search_markdown_tool',
    'update_markdown_tool',
]
