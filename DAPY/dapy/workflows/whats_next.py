"""
What's next workflow

Implements the "next" command as a LangGraph state machine.
Reads 2Do.md, ROADMAP.md, and git status to determine next steps.
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Dict, Any, List
from operator import add
from pathlib import Path

from dapy.tools.git_operations import git_status_tool
from dapy.tools.knowledge_base import read_markdown_tool


class WhatsNextState(TypedDict):
    """State for what's next workflow."""
    config: Dict[str, Any]
    todo_content: str
    roadmap_content: str
    git_status: Dict[str, Any]
    priorities: List[str]
    work_in_progress: List[str]
    next_steps: List[str]
    summary: str


def read_todo_node(state: WhatsNextState) -> WhatsNextState:
    """
    Read 2Do.md for current priorities.
    
    Extracts tasks and their status.
    """
    config = state['config']
    todo_file = config.get('todo_file', '2Do.md')
    
    todo_result = read_markdown_tool(filepath=todo_file)
    
    if todo_result.get('success'):
        content = todo_result.get('content', '')
        
        # Extract incomplete tasks (lines starting with - [ ])
        priorities = []
        for line in content.split('\n'):
            if line.strip().startswith('- [ ]'):
                task = line.strip()[6:].strip()
                priorities.append(task)
        
        return {
            'todo_content': content,
            'priorities': priorities,
        }
    else:
        return {
            'todo_content': '',
            'priorities': [],
        }


def read_roadmap_node(state: WhatsNextState) -> WhatsNextState:
    """
    Read ROADMAP.md for strategic direction.
    
    Identifies active epics and milestones.
    """
    config = state['config']
    roadmap_file = config.get('roadmap_file', 'ROADMAP.md')
    
    roadmap_result = read_markdown_tool(filepath=roadmap_file)
    
    if roadmap_result.get('success'):
        content = roadmap_result.get('content', '')
        return {'roadmap_content': content}
    else:
        return {'roadmap_content': ''}


def check_git_status_node(state: WhatsNextState) -> WhatsNextState:
    """
    Check git status for work in progress.
    
    Identifies uncommitted changes and current branch.
    """
    git_status = git_status_tool()
    
    work_in_progress = []
    
    if git_status.get('dirty'):
        work_in_progress.append(
            f"Uncommitted changes in {len(git_status.get('staged_files', []) + git_status.get('unstaged_files', []))} files"
        )
    
    if git_status.get('branch') != 'main' and git_status.get('branch') != 'master':
        work_in_progress.append(f"Working on branch: {git_status.get('branch')}")
    
    return {
        'git_status': git_status,
        'work_in_progress': work_in_progress,
    }


def determine_next_steps_node(state: WhatsNextState) -> WhatsNextState:
    """
    Determine recommended next steps.
    
    Combines priorities, roadmap, and work in progress to suggest actions.
    """
    next_steps = []
    
    # Check work in progress first
    work_in_progress = state.get('work_in_progress', [])
    if work_in_progress:
        next_steps.append("Complete work in progress:")
        next_steps.extend([f"  - {wip}" for wip in work_in_progress])
    
    # Add priorities from 2Do.md
    priorities = state.get('priorities', [])
    if priorities:
        next_steps.append("Priority tasks from 2Do.md:")
        # Show top 5 priorities
        for priority in priorities[:5]:
            next_steps.append(f"  - {priority}")
        
        if len(priorities) > 5:
            next_steps.append(f"  ... and {len(priorities) - 5} more tasks")
    
    # If no specific tasks, suggest reviewing roadmap
    if not next_steps:
        next_steps.append("Review ROADMAP.md for strategic direction")
        next_steps.append("Update 2Do.md with specific tasks")
    
    return {'next_steps': next_steps}


def generate_summary_node(state: WhatsNextState) -> WhatsNextState:
    """
    Generate summary of what's next.
    """
    summary_parts = [
        "# What's Next\n",
    ]
    
    # Work in progress
    work_in_progress = state.get('work_in_progress', [])
    if work_in_progress:
        summary_parts.append("\n## Work in Progress\n")
        for wip in work_in_progress:
            summary_parts.append(f"- {wip}")
    
    # Priorities
    priorities = state.get('priorities', [])
    if priorities:
        summary_parts.append("\n## Current Priorities\n")
        for priority in priorities[:5]:
            summary_parts.append(f"- {priority}")
        
        if len(priorities) > 5:
            summary_parts.append(f"\n*... and {len(priorities) - 5} more tasks in 2Do.md*")
    
    # Next steps
    next_steps = state.get('next_steps', [])
    if next_steps:
        summary_parts.append("\n## Recommended Next Steps\n")
        for step in next_steps:
            if not step.startswith('  '):
                summary_parts.append(f"\n**{step}**")
            else:
                summary_parts.append(step)
    
    # Git status
    git_status = state.get('git_status', {})
    if git_status:
        summary_parts.append(f"\n## Git Status\n")
        summary_parts.append(f"- Branch: {git_status.get('branch', 'unknown')}")
        summary_parts.append(f"- Status: {git_status.get('summary', 'unknown')}")
    
    summary = '\n'.join(summary_parts)
    
    return {'summary': summary}


def create_whats_next_graph() -> StateGraph:
    """
    Create the what's next workflow graph.
    
    Returns:
        Compiled LangGraph state machine
    """
    builder = StateGraph(WhatsNextState)
    
    # Add nodes
    builder.add_node("read_todo", read_todo_node)
    builder.add_node("read_roadmap", read_roadmap_node)
    builder.add_node("check_git_status", check_git_status_node)
    builder.add_node("determine_next_steps", determine_next_steps_node)
    builder.add_node("generate_summary", generate_summary_node)
    
    # Define edges (parallel reading, then sequential processing)
    builder.add_edge(START, "read_todo")
    builder.add_edge(START, "read_roadmap")
    builder.add_edge(START, "check_git_status")
    
    # All reading nodes feed into determine_next_steps
    builder.add_edge("read_todo", "determine_next_steps")
    builder.add_edge("read_roadmap", "determine_next_steps")
    builder.add_edge("check_git_status", "determine_next_steps")
    
    builder.add_edge("determine_next_steps", "generate_summary")
    builder.add_edge("generate_summary", END)
    
    return builder.compile()


def run_whats_next_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the what's next workflow.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with workflow results including summary
    """
    graph = create_whats_next_graph()
    
    # Initial state
    initial_state = {
        'config': config,
        'todo_content': '',
        'roadmap_content': '',
        'git_status': {},
        'priorities': [],
        'work_in_progress': [],
        'next_steps': [],
        'summary': '',
    }
    
    # Run workflow
    result = graph.invoke(initial_state)
    
    return result
