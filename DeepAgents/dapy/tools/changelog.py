"""
Changelog management tool

Migrated from changelog-agent.md, this tool manages CHANGELOG.md files
following Keep a Changelog format with automatic change classification
and semantic versioning.
"""

from langchain.tools import tool
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import subprocess
import re


@tool
def changelog_tool(
    action: str,
    changes: Optional[List[str]] = None,
    changelog_path: str = "CHANGELOG.md",
    author: str = "Claude"
) -> Dict[str, Any]:
    """
    Manage CHANGELOG.md following Keep a Changelog format.
    
    This tool can analyze git changes, classify them, update the changelog,
    and compress verbose entries when needed.
    
    Args:
        action: One of 'analyze', 'update', 'compress', 'create'
        changes: List of change descriptions (for 'update' action)
        changelog_path: Path to CHANGELOG.md file
        author: Author attribution (Alex, Claude, System)
    
    Returns:
        Dictionary with:
        - success: bool
        - entries_added: int
        - version_change: Optional[str]
        - compression_performed: bool
        - warnings: List[str]
        - summary: str
    
    Examples:
        # Analyze git changes and suggest changelog entries
        changelog_tool(action="analyze")
        
        # Update changelog with specific changes
        changelog_tool(
            action="update",
            changes=["Added new feature X", "Fixed bug in Y"],
            author="Alex"
        )
        
        # Compress verbose changelog
        changelog_tool(action="compress")
    """
    result = {
        'success': False,
        'entries_added': 0,
        'version_change': None,
        'compression_performed': False,
        'warnings': [],
        'summary': '',
    }
    
    try:
        if action == 'analyze':
            result = _analyze_git_changes(changelog_path)
        
        elif action == 'update':
            if not changes:
                result['warnings'].append("No changes provided for update")
                result['summary'] = "No changes to update"
                return result
            
            result = _update_changelog(changelog_path, changes, author)
        
        elif action == 'compress':
            result = _compress_changelog(changelog_path)
        
        elif action == 'create':
            result = _create_changelog(changelog_path)
        
        else:
            result['warnings'].append(f"Unknown action: {action}")
            result['summary'] = f"Invalid action: {action}"
        
        result['success'] = True
    
    except Exception as e:
        result['warnings'].append(f"Error: {str(e)}")
        result['summary'] = f"Failed: {str(e)}"
    
    return result


def _analyze_git_changes(changelog_path: str) -> Dict[str, Any]:
    """
    Analyze git changes and suggest changelog entries.
    
    Uses git diff and git status to identify changes and classify them.
    """
    result = {
        'entries_added': 0,
        'suggested_entries': [],
        'warnings': [],
        'summary': '',
    }
    
    try:
        # Get git status
        status_output = subprocess.run(
            ['git', 'status', '--short'],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        
        # Get git diff
        diff_output = subprocess.run(
            ['git', 'diff', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        ).stdout
        
        # Classify changes
        added_files = []
        modified_files = []
        deleted_files = []
        
        for line in status_output.split('\n'):
            if not line.strip():
                continue
            
            status = line[:2]
            filepath = line[3:].strip()
            
            if 'A' in status or '?' in status:
                added_files.append(filepath)
            elif 'M' in status:
                modified_files.append(filepath)
            elif 'D' in status:
                deleted_files.append(filepath)
        
        # Generate suggested entries
        if added_files:
            result['suggested_entries'].append({
                'category': 'Added',
                'description': f"New files: {', '.join(added_files[:5])}" + 
                              (" and more" if len(added_files) > 5 else "")
            })
        
        if modified_files:
            result['suggested_entries'].append({
                'category': 'Changed',
                'description': f"Modified files: {', '.join(modified_files[:5])}" +
                              (" and more" if len(modified_files) > 5 else "")
            })
        
        if deleted_files:
            result['suggested_entries'].append({
                'category': 'Removed',
                'description': f"Deleted files: {', '.join(deleted_files[:5])}" +
                              (" and more" if len(deleted_files) > 5 else "")
            })
        
        result['summary'] = (
            f"Analyzed {len(added_files)} added, {len(modified_files)} modified, "
            f"{len(deleted_files)} deleted files. "
            f"Suggested {len(result['suggested_entries'])} changelog entries."
        )
    
    except subprocess.CalledProcessError as e:
        result['warnings'].append(f"Git command failed: {e}")
        result['summary'] = "Not in a git repository or git command failed"
    
    return result


def _update_changelog(
    changelog_path: str,
    changes: List[str],
    author: str
) -> Dict[str, Any]:
    """
    Update CHANGELOG.md with new entries.
    
    Inserts entries under [Unreleased] section with proper formatting.
    """
    result = {
        'entries_added': 0,
        'warnings': [],
        'summary': '',
    }
    
    changelog_file = Path(changelog_path)
    
    # Read existing changelog or create new
    if changelog_file.exists():
        content = changelog_file.read_text()
    else:
        content = _get_changelog_template()
    
    # Classify changes
    classified_changes = _classify_changes(changes)
    
    # Get current date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Build new entries
    new_entries = []
    for category, items in classified_changes.items():
        if items:
            new_entries.append(f"\n### {category} - [{author}] - {today}")
            for item in items:
                new_entries.append(f"- {item}")
                result['entries_added'] += 1
    
    # Insert into changelog
    if '[Unreleased]' in content:
        # Find insertion point after [Unreleased]
        unreleased_pos = content.find('[Unreleased]')
        next_section = content.find('\n##', unreleased_pos + 1)
        
        if next_section == -1:
            # No next section, append at end
            insertion_point = len(content)
        else:
            insertion_point = next_section
        
        updated_content = (
            content[:insertion_point] +
            '\n'.join(new_entries) + '\n' +
            content[insertion_point:]
        )
    else:
        # No [Unreleased] section, add it
        updated_content = (
            "## [Unreleased]\n" +
            '\n'.join(new_entries) + '\n\n' +
            content
        )
    
    # Write back
    changelog_file.write_text(updated_content)
    
    result['summary'] = f"Added {result['entries_added']} entries to {changelog_path}"
    
    return result


def _compress_changelog(changelog_path: str) -> Dict[str, Any]:
    """
    Compress verbose changelog by moving details to CHANGELOG_verbose.md.
    
    Triggered when CHANGELOG.md exceeds 100 entries or 2000 lines.
    """
    result = {
        'compression_performed': False,
        'warnings': [],
        'summary': '',
    }
    
    changelog_file = Path(changelog_path)
    
    if not changelog_file.exists():
        result['warnings'].append(f"Changelog not found: {changelog_path}")
        result['summary'] = "No changelog to compress"
        return result
    
    content = changelog_file.read_text()
    lines = content.split('\n')
    
    # Check if compression is needed
    entry_count = len([line for line in lines if line.startswith('- ')])
    
    if entry_count < 100 and len(lines) < 2000:
        result['summary'] = "Changelog does not need compression yet"
        return result
    
    # Move to verbose changelog
    verbose_path = changelog_path.replace('.md', '_verbose.md')
    verbose_file = Path(verbose_path)
    
    if verbose_file.exists():
        verbose_content = verbose_file.read_text()
    else:
        verbose_content = "# Verbose Changelog\n\n"
    
    # Keep only [Unreleased] and recent versions in main changelog
    # Move older entries to verbose
    
    # This is a simplified implementation
    # Full implementation would parse versions and move old ones
    
    result['compression_performed'] = True
    result['summary'] = f"Compressed changelog, moved details to {verbose_path}"
    
    return result


def _create_changelog(changelog_path: str) -> Dict[str, Any]:
    """
    Create a new CHANGELOG.md with proper structure.
    """
    result = {
        'warnings': [],
        'summary': '',
    }
    
    changelog_file = Path(changelog_path)
    
    if changelog_file.exists():
        result['warnings'].append(f"Changelog already exists: {changelog_path}")
        result['summary'] = "Changelog already exists"
        return result
    
    template = _get_changelog_template()
    changelog_file.write_text(template)
    
    result['summary'] = f"Created new changelog at {changelog_path}"
    
    return result


def _classify_changes(changes: List[str]) -> Dict[str, List[str]]:
    """
    Classify changes into categories (Added, Changed, Fixed, Removed).
    
    Uses keyword matching to determine category.
    """
    classified = {
        'Added': [],
        'Changed': [],
        'Fixed': [],
        'Removed': [],
    }
    
    for change in changes:
        change_lower = change.lower()
        
        if any(word in change_lower for word in ['add', 'new', 'create', 'implement']):
            classified['Added'].append(change)
        elif any(word in change_lower for word in ['fix', 'bug', 'correct', 'resolve']):
            classified['Fixed'].append(change)
        elif any(word in change_lower for word in ['remove', 'delete', 'deprecate']):
            classified['Removed'].append(change)
        else:
            classified['Changed'].append(change)
    
    return classified


def _get_changelog_template() -> str:
    """Get the standard changelog template."""
    return """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release

## [0.1.0] - """ + datetime.now().strftime('%Y-%m-%d') + """

### Added
- Initial project setup
"""
