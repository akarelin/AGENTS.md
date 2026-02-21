"""
Archive tool for code cleanup and organization

Migrated from archive-agent.md, this tool handles structured archival
of outdated code with inventory management.
"""

from langchain.tools import tool
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import shutil


@tool
def archive_tool(
    files: List[str],
    reason: str,
    archive_type: str = "legacy",
    create_inventory: bool = True
) -> Dict[str, Any]:
    """
    Archive outdated code with structured inventory.
    
    Moves files to the archive directory with proper organization
    and maintains an inventory README.md.
    
    Args:
        files: List of file paths to archive
        reason: Reason for archiving (e.g., "Replaced by new implementation")
        archive_type: Type of archive ('legacy', 'experiments', 'misc', 'docs')
        create_inventory: Whether to update archive README.md
    
    Returns:
        Dictionary with:
        - success: bool
        - archived_count: int
        - archive_path: str
        - inventory_updated: bool
        - warnings: List[str]
        - summary: str
    
    Examples:
        # Archive old implementation
        archive_tool(
            files=["old_module.py", "deprecated_utils.py"],
            reason="Replaced by refactored version",
            archive_type="legacy"
        )
        
        # Archive failed experiment
        archive_tool(
            files=["experiment_v1/"],
            reason="Approach did not work, kept for reference",
            archive_type="experiments"
        )
    """
    result = {
        'success': False,
        'archived_count': 0,
        'archive_path': '',
        'inventory_updated': False,
        'warnings': [],
        'summary': '',
    }
    
    try:
        # Validate archive type
        valid_types = ['legacy', 'experiments', 'misc', 'docs']
        if archive_type not in valid_types:
            result['warnings'].append(
                f"Invalid archive type: {archive_type}. Using 'misc'."
            )
            archive_type = 'misc'
        
        # Create archive structure
        archive_base = Path('archive')
        archive_dir = archive_base / archive_type
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped subdirectory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target_dir = archive_dir / timestamp
        target_dir.mkdir(exist_ok=True)
        
        # Archive files
        archived_files = []
        for file_path in files:
            source = Path(file_path)
            
            if not source.exists():
                result['warnings'].append(f"File not found: {file_path}")
                continue
            
            # Determine target path
            if source.is_file():
                target = target_dir / source.name
                shutil.copy2(source, target)
            else:
                target = target_dir / source.name
                shutil.copytree(source, target)
            
            archived_files.append({
                'original': str(source),
                'archived': str(target),
            })
            result['archived_count'] += 1
        
        result['archive_path'] = str(target_dir)
        
        # Update inventory
        if create_inventory and archived_files:
            _update_archive_inventory(
                archive_base,
                archived_files,
                reason,
                archive_type,
                timestamp
            )
            result['inventory_updated'] = True
        
        result['success'] = True
        result['summary'] = (
            f"Archived {result['archived_count']} items to {result['archive_path']}. "
            f"Reason: {reason}"
        )
    
    except Exception as e:
        result['warnings'].append(f"Error: {str(e)}")
        result['summary'] = f"Failed to archive: {str(e)}"
    
    return result


def _update_archive_inventory(
    archive_base: Path,
    archived_files: List[Dict[str, str]],
    reason: str,
    archive_type: str,
    timestamp: str
) -> None:
    """
    Update the archive README.md inventory.
    
    Maintains a structured inventory of all archived items.
    """
    readme_path = archive_base / 'README.md'
    
    # Read existing or create new
    if readme_path.exists():
        content = readme_path.read_text()
    else:
        content = _get_archive_readme_template()
    
    # Build new entry
    date = datetime.now().strftime('%Y-%m-%d')
    entry = f"\n## Archive Entry - {timestamp}\n\n"
    entry += f"**Date**: {date}\n"
    entry += f"**Type**: {archive_type}\n"
    entry += f"**Reason**: {reason}\n\n"
    entry += "**Files**:\n"
    
    for file_info in archived_files:
        entry += f"- `{file_info['original']}` → `{file_info['archived']}`\n"
    
    entry += "\n---\n"
    
    # Insert after the header
    header_end = content.find('\n\n') + 2
    updated_content = content[:header_end] + entry + content[header_end:]
    
    readme_path.write_text(updated_content)


def _get_archive_readme_template() -> str:
    """Get the standard archive README template."""
    return """# Archive Inventory

This directory contains archived code, experiments, and documentation.
Items are organized by type and timestamped for easy reference.

## Archive Types

- **legacy/**: Old versions of refactored code
- **experiments/**: Failed or abandoned attempts (with notes on what was tried)
- **misc/**: Miscellaneous files moved from root
- **docs/**: Outdated documentation

## Guidelines

- **Archive, don't delete**: History is valuable for learning
- **Document reason**: Always include why something was archived
- **Preserve structure**: Keep related files together
- **Add notes**: For experiments, document what was tried and why it failed

---

"""
