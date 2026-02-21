"""
Main agent orchestrator using LangChain 1.0

Creates the primary agent with middleware, tools, and configuration.
"""

from typing import Any, Dict
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_openai import ChatOpenAI

from deepagents.middleware import (
    SnapshotMiddleware,
    BreakpointMiddleware,
    EnhancedLoggingMiddleware,
)
from deepagents.tools import get_all_tools
from deepagents.config import get_prompt


def create_main_agent(config: Dict[str, Any], checkpointer: Any = None) -> Any:
    """
    Create the main DeepAgents orchestrator agent.
    
    This agent uses LangChain 1.0's create_agent with custom middleware
    for observability, human-in-the-loop, and state management.
    
    Args:
        config: Configuration dictionary
        checkpointer: LangGraph checkpointer for state persistence
        
    Returns:
        Configured agent ready for invocation
    """
    # Load system prompt
    system_prompt = get_prompt(config, 'system_prompt')
    
    # Get all available tools
    tools = get_all_tools(config)
    
    # Create model
    model_spec = config.get('model', 'openai:gpt-4o')
    if model_spec.startswith('openai:'):
        model_name = model_spec.split(':', 1)[1]
        model = ChatOpenAI(model=model_name, temperature=0)
    else:
        raise ValueError(f"Unsupported model: {model_spec}")
    
    # Build middleware stack
    middleware = []
    
    # 1. Enhanced logging (first, to capture everything)
    if config.get('debug', False):
        middleware.append(EnhancedLoggingMiddleware(verbose=True))
    
    # 2. Breakpoints (before snapshots, for early intervention)
    if config.get('breakpoints'):
        middleware.append(BreakpointMiddleware(breakpoints=config['breakpoints']))
    
    # 3. Snapshots (before HITL, to capture pre-approval state)
    if config.get('snapshot_enabled', True):
        middleware.append(SnapshotMiddleware(
            snapshot_dir=config.get('snapshot_dir', './snapshots'),
            enabled=True
        ))
    
    # 4. Human-in-the-loop (last, for final approval)
    if not config.get('auto_approve', False):
        def requires_approval(tool_call: Any) -> bool:
            """Check if tool call requires human approval."""
            tool_name = tool_call.name if hasattr(tool_call, 'name') else str(tool_call)
            approval_tools = config.get('approval_tools', [])
            return tool_name in approval_tools
        
        middleware.append(HumanInTheLoopMiddleware(
            approval_required=requires_approval
        ))
    
    # Create agent
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
    
    return agent


def create_specialized_agent(
    config: Dict[str, Any],
    agent_type: str,
    checkpointer: Any = None
) -> Any:
    """
    Create a specialized agent for specific tasks.
    
    Args:
        config: Configuration dictionary
        agent_type: Type of specialized agent (e.g., 'changelog', 'archive')
        checkpointer: LangGraph checkpointer
        
    Returns:
        Specialized agent
    """
    # Load specialized prompt
    system_prompt = get_prompt(config, f'{agent_type}_agent')
    
    # Get tools relevant to this agent type
    from deepagents.tools import get_tools_for_agent
    tools = get_tools_for_agent(agent_type, config)
    
    # Create model
    model_spec = config.get('model', 'openai:gpt-4o')
    if model_spec.startswith('openai:'):
        model_name = model_spec.split(':', 1)[1]
        model = ChatOpenAI(model=model_name, temperature=0)
    else:
        raise ValueError(f"Unsupported model: {model_spec}")
    
    # Minimal middleware for specialized agents
    middleware = []
    if config.get('debug', False):
        middleware.append(EnhancedLoggingMiddleware(verbose=False))
    
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )
    
    return agent
