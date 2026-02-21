"""
Git operations tools for version control management
"""

from langchain.tools import tool
from typing import Dict, Any, Optional
import subprocess
from pathlib import Path


@tool
def git_push_tool(
    message: str = "",
    create_pr: bool = False
) -> Dict[str, Any]:
    """
    Execute git operations with changelog verification.
    
    Commits and pushes changes, optionally creating a pull request.
    Verifies that CHANGELOG.md is updated before pushing.
    
    Args:
        message: Commit message (auto-generated if empty)
        create_pr: Whether to create a pull request
    
    Returns:
        Dictionary with:
        - success: bool
        - commit_hash: str
        - push_status: str
        - pr_url: Optional[str]
        - warnings: List[str]
        - summary: str
    
    Example:
        git_push_tool(
            message="Implemented new feature X",
            create_pr=True
        )
    """
    result = {
        'success': False,
        'commit_hash': '',
        'push_status': '',
        'pr_url': None,
        'warnings': [],
        'summary': '',
    }
    
    try:
        # Check if CHANGELOG.md is updated
        changelog_path = Path('CHANGELOG.md')
        if changelog_path.exists():
            # Check if CHANGELOG.md is in staged changes
            status = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            ).stdout
            
            if 'CHANGELOG.md' not in status:
                result['warnings'].append(
                    "CHANGELOG.md not updated. Please update before pushing."
                )
                result['summary'] = "Push aborted: CHANGELOG.md not updated"
                return result
        
        # Stage all changes
        subprocess.run(['git', 'add', '-A'], check=True)
        
        # Generate commit message if not provided
        if not message:
            message = "Update: automated commit"
        
        # Commit
        commit_result = subprocess.run(
            ['git', 'commit', '-m', message],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract commit hash
        hash_result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        result['commit_hash'] = hash_result.stdout.strip()[:8]
        
        # Push
        push_result = subprocess.run(
            ['git', 'push'],
            capture_output=True,
            text=True,
            check=True
        )
        result['push_status'] = 'success'
        
        # Create PR if requested
        if create_pr:
            try:
                pr_result = subprocess.run(
                    ['gh', 'pr', 'create', '--fill'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                # Extract PR URL from output
                for line in pr_result.stdout.split('\n'):
                    if 'https://github.com' in line:
                        result['pr_url'] = line.strip()
                        break
            except subprocess.CalledProcessError as e:
                result['warnings'].append(f"PR creation failed: {e}")
        
        result['success'] = True
        result['summary'] = f"Pushed commit {result['commit_hash']}"
        if result['pr_url']:
            result['summary'] += f" and created PR: {result['pr_url']}"
    
    except subprocess.CalledProcessError as e:
        result['warnings'].append(f"Git operation failed: {e}")
        result['summary'] = f"Push failed: {e}"
    
    return result


@tool
def git_status_tool() -> Dict[str, Any]:
    """
    Get current git status.
    
    Returns:
        Dictionary with:
        - branch: str
        - dirty: bool
        - staged_files: List[str]
        - unstaged_files: List[str]
        - untracked_files: List[str]
        - summary: str
    """
    result = {
        'branch': '',
        'dirty': False,
        'staged_files': [],
        'unstaged_files': [],
        'untracked_files': [],
        'summary': '',
    }
    
    try:
        # Get branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True
        )
        result['branch'] = branch_result.stdout.strip()
        
        # Get status
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in status_result.stdout.split('\n'):
            if not line.strip():
                continue
            
            status = line[:2]
            filepath = line[3:].strip()
            
            if status[0] in ['M', 'A', 'D', 'R']:
                result['staged_files'].append(filepath)
            if status[1] in ['M', 'D']:
                result['unstaged_files'].append(filepath)
            if status == '??':
                result['untracked_files'].append(filepath)
        
        result['dirty'] = bool(
            result['staged_files'] or
            result['unstaged_files'] or
            result['untracked_files']
        )
        
        result['summary'] = (
            f"Branch: {result['branch']}, "
            f"Staged: {len(result['staged_files'])}, "
            f"Unstaged: {len(result['unstaged_files'])}, "
            f"Untracked: {len(result['untracked_files'])}"
        )
    
    except subprocess.CalledProcessError as e:
        result['summary'] = f"Not a git repository or git command failed: {e}"
    
    return result


@tool
def git_diff_tool(staged: bool = False) -> Dict[str, Any]:
    """
    Get git diff output.
    
    Args:
        staged: Whether to show staged changes (default: unstaged)
    
    Returns:
        Dictionary with:
        - diff: str
        - files_changed: List[str]
        - summary: str
    """
    result = {
        'diff': '',
        'files_changed': [],
        'summary': '',
    }
    
    try:
        cmd = ['git', 'diff']
        if staged:
            cmd.append('--cached')
        
        diff_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        result['diff'] = diff_result.stdout
        
        # Get list of changed files
        name_cmd = cmd + ['--name-only']
        name_result = subprocess.run(
            name_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        result['files_changed'] = [
            f for f in name_result.stdout.split('\n') if f.strip()
        ]
        
        result['summary'] = (
            f"{'Staged' if staged else 'Unstaged'} changes in "
            f"{len(result['files_changed'])} files"
        )
    
    except subprocess.CalledProcessError as e:
        result['summary'] = f"Git diff failed: {e}"
    
    return result
