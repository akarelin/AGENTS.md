"""
Knowledge base tools for markdown file operations
"""

from langchain.tools import tool
from typing import Dict, Any, List, Optional
from pathlib import Path
import re


@tool
def read_markdown_tool(filepath: str) -> Dict[str, Any]:
    """
    Read a markdown file and extract structured content.
    
    Args:
        filepath: Path to markdown file
    
    Returns:
        Dictionary with:
        - success: bool
        - content: str
        - frontmatter: Dict[str, Any]
        - headings: List[str]
        - summary: str
    """
    result = {
        'success': False,
        'content': '',
        'frontmatter': {},
        'headings': [],
        'summary': '',
    }
    
    try:
        file_path = Path(filepath)
        
        if not file_path.exists():
            result['summary'] = f"File not found: {filepath}"
            return result
        
        content = file_path.read_text()
        result['content'] = content
        
        # Extract frontmatter
        if content.startswith('---'):
            end_idx = content.find('---', 3)
            if end_idx != -1:
                frontmatter_text = content[3:end_idx].strip()
                # Simple YAML parsing (key: value)
                for line in frontmatter_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        result['frontmatter'][key.strip()] = value.strip()
        
        # Extract headings
        result['headings'] = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        
        result['success'] = True
        result['summary'] = f"Read {len(content)} characters from {filepath}"
    
    except Exception as e:
        result['summary'] = f"Error reading file: {e}"
    
    return result


@tool
def search_markdown_tool(
    query: str,
    directory: str = ".",
    file_pattern: str = "*.md"
) -> Dict[str, Any]:
    """
    Search for content in markdown files.
    
    Args:
        query: Search query (supports regex)
        directory: Directory to search in
        file_pattern: File pattern to match (default: *.md)
    
    Returns:
        Dictionary with:
        - success: bool
        - matches: List[Dict[str, Any]]
        - total_matches: int
        - summary: str
    """
    result = {
        'success': False,
        'matches': [],
        'total_matches': 0,
        'summary': '',
    }
    
    try:
        search_dir = Path(directory)
        
        if not search_dir.exists():
            result['summary'] = f"Directory not found: {directory}"
            return result
        
        # Find all matching files
        files = list(search_dir.rglob(file_pattern))
        
        # Search in each file
        pattern = re.compile(query, re.IGNORECASE)
        
        for file_path in files:
            try:
                content = file_path.read_text()
                matches = pattern.finditer(content)
                
                for match in matches:
                    # Get context around match
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end]
                    
                    result['matches'].append({
                        'file': str(file_path),
                        'match': match.group(),
                        'context': context,
                        'position': match.start(),
                    })
                    result['total_matches'] += 1
            
            except Exception as e:
                # Skip files that can't be read
                continue
        
        result['success'] = True
        result['summary'] = (
            f"Found {result['total_matches']} matches in "
            f"{len(set(m['file'] for m in result['matches']))} files"
        )
    
    except Exception as e:
        result['summary'] = f"Search failed: {e}"
    
    return result


@tool
def update_markdown_tool(
    filepath: str,
    updates: Dict[str, str],
    update_type: str = "append"
) -> Dict[str, Any]:
    """
    Update a markdown file.
    
    Args:
        filepath: Path to markdown file
        updates: Dictionary of updates to apply
        update_type: Type of update ('append', 'replace', 'frontmatter')
    
    Returns:
        Dictionary with:
        - success: bool
        - changes_made: int
        - summary: str
    
    Examples:
        # Append content
        update_markdown_tool(
            filepath="2Do.md",
            updates={"content": "- New task to complete"},
            update_type="append"
        )
        
        # Update frontmatter
        update_markdown_tool(
            filepath="project.md",
            updates={"status": "completed", "updated": "2025-11-26"},
            update_type="frontmatter"
        )
    """
    result = {
        'success': False,
        'changes_made': 0,
        'summary': '',
    }
    
    try:
        file_path = Path(filepath)
        
        # Read existing content
        if file_path.exists():
            content = file_path.read_text()
        else:
            content = ""
        
        if update_type == 'append':
            # Append new content
            new_content = updates.get('content', '')
            content += '\n' + new_content
            result['changes_made'] = 1
        
        elif update_type == 'replace':
            # Replace entire content
            content = updates.get('content', '')
            result['changes_made'] = 1
        
        elif update_type == 'frontmatter':
            # Update frontmatter
            if content.startswith('---'):
                end_idx = content.find('---', 3)
                if end_idx != -1:
                    frontmatter_text = content[3:end_idx].strip()
                    body = content[end_idx + 3:]
                else:
                    frontmatter_text = ""
                    body = content
            else:
                frontmatter_text = ""
                body = content
            
            # Parse and update frontmatter
            frontmatter_lines = []
            existing_keys = set()
            
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key = line.split(':', 1)[0].strip()
                    if key in updates:
                        frontmatter_lines.append(f"{key}: {updates[key]}")
                        existing_keys.add(key)
                        result['changes_made'] += 1
                    else:
                        frontmatter_lines.append(line)
                else:
                    frontmatter_lines.append(line)
            
            # Add new keys
            for key, value in updates.items():
                if key not in existing_keys:
                    frontmatter_lines.append(f"{key}: {value}")
                    result['changes_made'] += 1
            
            # Rebuild content
            content = (
                "---\n" +
                '\n'.join(frontmatter_lines) +
                "\n---" +
                body
            )
        
        # Write back
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        
        result['success'] = True
        result['summary'] = f"Updated {filepath} with {result['changes_made']} changes"
    
    except Exception as e:
        result['summary'] = f"Update failed: {e}"
    
    return result
