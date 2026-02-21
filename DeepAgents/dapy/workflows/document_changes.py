"""
Document changes workflow

Implements the "document" command as a LangGraph state machine.
Detects changes via git diff and updates CHANGELOG.md.
"""

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Dict, Any, List
from operator import add

from deepagents.tools.git_operations import git_diff_tool, git_status_tool
from deepagents.tools.changelog import changelog_tool


class DocumentChangesState(TypedDict):
    """State for document changes workflow."""
    config: Dict[str, Any]
    git_status: Dict[str, Any]
    git_diff: Dict[str, Any]
    detected_changes: List[str]
    changelog_updated: bool
    progress_updates: Annotated[list[str], add]
    summary: str


def detect_changes_node(state: DocumentChangesState) -> DocumentChangesState:
    """
    Detect changes using git diff and status.
    
    Analyzes both staged and unstaged changes.
    """
    # Get git status
    git_status = git_status_tool()
    
    # Get git diff (unstaged)
    git_diff_unstaged = git_diff_tool(staged=False)
    
    # Get git diff (staged)
    git_diff_staged = git_diff_tool(staged=True)
    
    # Combine changed files
    all_changed_files = set(
        git_status.get('staged_files', []) +
        git_status.get('unstaged_files', []) +
        git_diff_unstaged.get('files_changed', []) +
        git_diff_staged.get('files_changed', [])
    )
    
    updates = [
        f"Detected {len(all_changed_files)} changed files",
        f"Git status: {git_status.get('summary', 'Unknown')}",
    ]
    
    return {
        'git_status': git_status,
        'git_diff': git_diff_unstaged,  # Use unstaged for analysis
        'detected_changes': list(all_changed_files),
        'progress_updates': updates,
    }


def classify_changes_node(state: DocumentChangesState) -> DocumentChangesState:
    """
    Classify detected changes into categories.
    
    Determines if changes are additions, modifications, fixes, or removals.
    """
    detected_changes = state.get('detected_changes', [])
    git_status = state.get('git_status', {})
    
    classified_changes = []
    
    # Classify based on file status
    for filepath in detected_changes:
        if filepath in git_status.get('staged_files', []):
            # Check if it's a new file
            if filepath in git_status.get('untracked_files', []):
                classified_changes.append(f"Added {filepath}")
            else:
                # Assume it's a modification
                # In production, would analyze diff content
                classified_changes.append(f"Modified {filepath}")
        else:
            classified_changes.append(f"Changed {filepath}")
    
    updates = [f"Classified {len(classified_changes)} changes"]
    
    return {
        'detected_changes': classified_changes,
        'progress_updates': updates,
    }


def update_changelog_node(state: DocumentChangesState) -> DocumentChangesState:
    """
    Update CHANGELOG.md with detected changes.
    
    Uses the changelog tool to add entries.
    """
    detected_changes = state.get('detected_changes', [])
    
    if not detected_changes:
        updates = ["No changes to document"]
        return {
            'changelog_updated': False,
            'progress_updates': updates,
        }
    
    # Update changelog
    changelog_result = changelog_tool(
        action='update',
        changes=detected_changes,
        author='Alex'  # Assume human-initiated changes
    )
    
    updates = [
        f"Updated CHANGELOG.md: {changelog_result.get('summary', 'Unknown')}",
        f"Added {changelog_result.get('entries_added', 0)} entries",
    ]
    
    return {
        'changelog_updated': changelog_result.get('success', False),
        'progress_updates': updates,
    }


def generate_summary_node(state: DocumentChangesState) -> DocumentChangesState:
    """
    Generate final summary of documentation process.
    """
    summary_parts = [
        "# Changes Documented\n",
        "\n## Detected Changes\n",
    ]
    
    detected_changes = state.get('detected_changes', [])
    for change in detected_changes[:10]:  # Show first 10
        summary_parts.append(f"- {change}")
    
    if len(detected_changes) > 10:
        summary_parts.append(f"- ... and {len(detected_changes) - 10} more")
    
    summary_parts.append("\n## Actions Taken\n")
    for update in state.get('progress_updates', []):
        summary_parts.append(f"- {update}")
    
    summary_parts.append("\n## Status\n")
    summary_parts.append(
        f"- CHANGELOG.md: {'✓ Updated' if state.get('changelog_updated') else '✗ Not updated'}"
    )
    
    summary = '\n'.join(summary_parts)
    
    return {'summary': summary}


def create_document_changes_graph() -> StateGraph:
    """
    Create the document changes workflow graph.
    
    Returns:
        Compiled LangGraph state machine
    """
    builder = StateGraph(DocumentChangesState)
    
    # Add nodes
    builder.add_node("detect_changes", detect_changes_node)
    builder.add_node("classify_changes", classify_changes_node)
    builder.add_node("update_changelog", update_changelog_node)
    builder.add_node("generate_summary", generate_summary_node)
    
    # Define edges
    builder.add_edge(START, "detect_changes")
    builder.add_edge("detect_changes", "classify_changes")
    builder.add_edge("classify_changes", "update_changelog")
    builder.add_edge("update_changelog", "generate_summary")
    builder.add_edge("generate_summary", END)
    
    return builder.compile()


def run_document_changes_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the document changes workflow.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with workflow results including summary
    """
    graph = create_document_changes_graph()
    
    # Initial state
    initial_state = {
        'config': config,
        'git_status': {},
        'git_diff': {},
        'detected_changes': [],
        'changelog_updated': False,
        'progress_updates': [],
        'summary': '',
    }
    
    # Run workflow
    result = graph.invoke(initial_state)
    
    return result
