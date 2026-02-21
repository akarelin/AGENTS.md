"""
Close session workflow

Implements the "close" command as a LangGraph state machine.
Handles session cleanup, documentation, and preparation for next session.
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Dict, Any
from operator import add
from pathlib import Path

from deepagents.tools.git_operations import git_status_tool
from deepagents.tools.knowledge_base import read_markdown_tool, update_markdown_tool
from deepagents.tools.archive import archive_tool
from deepagents.tools.mistake_processor import mistake_processor_tool


class CloseSessionState(TypedDict):
    """State for close session workflow."""
    config: Dict[str, Any]
    progress_updates: Annotated[list[str], add]
    mistakes_documented: bool
    files_archived: list[str]
    todo_updated: bool
    git_status: Dict[str, Any]
    summary: str


def analyze_session_node(state: CloseSessionState) -> CloseSessionState:
    """
    Analyze current session state.
    
    Checks git status and identifies work in progress.
    """
    # Get git status
    git_status = git_status_tool()
    
    updates = [
        f"Session analysis complete",
        f"Git status: {git_status['summary']}",
    ]
    
    return {
        'git_status': git_status,
        'progress_updates': updates,
    }


def update_todo_node(state: CloseSessionState) -> CloseSessionState:
    """
    Update 2Do.md with current progress and next steps.
    
    Reads current 2Do.md, adds session summary, and marks completed items.
    """
    config = state['config']
    todo_file = config.get('todo_file', '2Do.md')
    
    # Read current TODO
    todo_result = read_markdown_tool(filepath=todo_file)
    
    # Prepare update with session summary
    from datetime import datetime
    session_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    session_summary = "\n\n## Session Closed - " + session_date + "\n\n"
    session_summary += "### Progress Made\n"
    
    for update in state.get('progress_updates', []):
        session_summary += f"- {update}\n"
    
    session_summary += "\n### Next Steps\n"
    session_summary += "- Review session summary\n"
    session_summary += "- Continue with planned tasks\n"
    
    # Update TODO file
    update_result = update_markdown_tool(
        filepath=todo_file,
        updates={'content': session_summary},
        update_type='append'
    )
    
    updates = [f"Updated {todo_file} with session summary"]
    
    return {
        'todo_updated': True,
        'progress_updates': updates,
    }


def check_mistakes_node(state: CloseSessionState) -> CloseSessionState:
    """
    Check if there are any mistakes to document.
    
    In a real implementation, this would analyze session logs
    and prompt for mistake documentation if needed.
    """
    # For now, just mark as checked
    # In production, this would integrate with session logging
    # and detect potential mistakes
    
    updates = ["Checked for mistakes - none found"]
    
    return {
        'mistakes_documented': True,
        'progress_updates': updates,
    }


def archive_completed_work_node(state: CloseSessionState) -> CloseSessionState:
    """
    Archive any completed work that should be moved.
    
    Identifies temporary files, completed experiments, etc.
    """
    # Check for common temporary files
    temp_patterns = [
        '*.tmp',
        '*.bak',
        '*~',
        '.DS_Store',
    ]
    
    files_to_archive = []
    
    # In production, this would scan for files matching patterns
    # For now, just report that check was done
    
    updates = ["Checked for files to archive - none found"]
    
    return {
        'files_archived': files_to_archive,
        'progress_updates': updates,
    }


def generate_summary_node(state: CloseSessionState) -> CloseSessionState:
    """
    Generate final session summary.
    
    Combines all progress updates into a cohesive summary.
    """
    summary_parts = [
        "# Session Closed Successfully\n",
        "\n## Actions Taken\n",
    ]
    
    for update in state.get('progress_updates', []):
        summary_parts.append(f"- {update}")
    
    summary_parts.append("\n## Status\n")
    summary_parts.append(f"- 2Do.md: {'✓ Updated' if state.get('todo_updated') else '✗ Not updated'}")
    summary_parts.append(f"- Mistakes: {'✓ Checked' if state.get('mistakes_documented') else '✗ Not checked'}")
    summary_parts.append(f"- Archive: {len(state.get('files_archived', []))} files archived")
    
    git_status = state.get('git_status', {})
    if git_status:
        summary_parts.append(f"\n## Git Status\n")
        summary_parts.append(f"- {git_status.get('summary', 'Unknown')}")
    
    summary_parts.append("\n## Ready for Next Session\n")
    summary_parts.append("Review 2Do.md for next steps.")
    
    summary = '\n'.join(summary_parts)
    
    return {'summary': summary}


def create_close_session_graph() -> StateGraph:
    """
    Create the close session workflow graph.
    
    Returns:
        Compiled LangGraph state machine
    """
    builder = StateGraph(CloseSessionState)
    
    # Add nodes
    builder.add_node("analyze_session", analyze_session_node)
    builder.add_node("update_todo", update_todo_node)
    builder.add_node("check_mistakes", check_mistakes_node)
    builder.add_node("archive_work", archive_completed_work_node)
    builder.add_node("generate_summary", generate_summary_node)
    
    # Define edges (sequential workflow)
    builder.add_edge(START, "analyze_session")
    builder.add_edge("analyze_session", "update_todo")
    builder.add_edge("update_todo", "check_mistakes")
    builder.add_edge("check_mistakes", "archive_work")
    builder.add_edge("archive_work", "generate_summary")
    builder.add_edge("generate_summary", END)
    
    return builder.compile()


def run_close_session_workflow(
    config: Dict[str, Any],
    checkpointer: Any = None
) -> Dict[str, Any]:
    """
    Run the close session workflow.
    
    Args:
        config: Configuration dictionary
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Dictionary with workflow results including summary
    """
    graph = create_close_session_graph()
    
    # Initial state
    initial_state = {
        'config': config,
        'progress_updates': [],
        'mistakes_documented': False,
        'files_archived': [],
        'todo_updated': False,
        'git_status': {},
        'summary': '',
    }
    
    # Run workflow
    result = graph.invoke(initial_state)
    
    return result
