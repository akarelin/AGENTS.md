"""
Mistake processing tool for learning from errors

Migrated from mistake-review-agent.md, this tool documents mistakes
and analyzes patterns to prevent recurrence.
"""

from langchain.tools import tool
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


@tool
def mistake_processor_tool(
    context: str,
    what_happened: str,
    why_wrong: str,
    lesson_learned: str,
    fix_applied: str,
    mistakes_file: str = "AGENTS_mistakes.md"
) -> Dict[str, Any]:
    """
    Document and learn from mistakes.
    
    Records mistakes in AGENTS_mistakes.md with full context for learning
    and pattern detection.
    
    Args:
        context: Context in which the mistake occurred
        what_happened: Factual description of the error
        why_wrong: Impact and violation of guidelines
        lesson_learned: Key takeaway to prevent recurrence
        fix_applied: How it was or should be corrected
        mistakes_file: Path to mistakes documentation file
    
    Returns:
        Dictionary with:
        - success: bool
        - documented: bool
        - similar_patterns: List[str]
        - warnings: List[str]
        - summary: str
    
    Example:
        mistake_processor_tool(
            context="During archive operation",
            what_happened="Deleted files without creating backup",
            why_wrong="Violated production safety rule - always backup before delete",
            lesson_learned="Always create backup before any destructive operation",
            fix_applied="Restored from git history, updated archive tool to backup first"
        )
    """
    result = {
        'success': False,
        'documented': False,
        'similar_patterns': [],
        'warnings': [],
        'summary': '',
    }
    
    try:
        mistakes_path = Path(mistakes_file)
        
        # Read existing or create new
        if mistakes_path.exists():
            content = mistakes_path.read_text()
        else:
            content = _get_mistakes_template()
        
        # Check for similar patterns
        result['similar_patterns'] = _find_similar_patterns(
            content,
            what_happened,
            lesson_learned
        )
        
        # Build new entry
        date = datetime.now().strftime('%Y-%m-%d %H:%M')
        entry = f"\n## Mistake - {date}\n\n"
        entry += f"**Context**: {context}\n\n"
        entry += f"**What Happened**: {what_happened}\n\n"
        entry += f"**Why It Was Wrong**: {why_wrong}\n\n"
        entry += f"**Lesson Learned**: {lesson_learned}\n\n"
        entry += f"**Fix Applied**: {fix_applied}\n\n"
        
        if result['similar_patterns']:
            entry += "**Similar Past Mistakes**:\n"
            for pattern in result['similar_patterns']:
                entry += f"- {pattern}\n"
            entry += "\n"
        
        entry += "---\n"
        
        # Append to file
        updated_content = content + entry
        mistakes_path.write_text(updated_content)
        
        result['documented'] = True
        result['success'] = True
        result['summary'] = f"Documented mistake in {mistakes_file}"
        
        if result['similar_patterns']:
            result['summary'] += f". Found {len(result['similar_patterns'])} similar past mistakes."
    
    except Exception as e:
        result['warnings'].append(f"Error: {str(e)}")
        result['summary'] = f"Failed to document mistake: {str(e)}"
    
    return result


def _find_similar_patterns(
    content: str,
    what_happened: str,
    lesson_learned: str
) -> List[str]:
    """
    Find similar mistakes in the history.
    
    Uses keyword matching to identify patterns.
    """
    similar = []
    
    # Extract keywords from current mistake
    keywords = set(what_happened.lower().split() + lesson_learned.lower().split())
    keywords = {w for w in keywords if len(w) > 4}  # Only meaningful words
    
    # Parse existing mistakes
    sections = content.split('## Mistake - ')
    
    for section in sections[1:]:  # Skip header
        if not section.strip():
            continue
        
        # Extract date and content
        lines = section.split('\n')
        date = lines[0].strip()
        section_text = ' '.join(lines).lower()
        
        # Check for keyword overlap
        matches = sum(1 for keyword in keywords if keyword in section_text)
        
        if matches >= 2:  # At least 2 keyword matches
            similar.append(f"Similar issue on {date}")
    
    return similar


def _get_mistakes_template() -> str:
    """Get the standard mistakes file template."""
    return """# Agent Mistakes Documentation

This file documents mistakes made during agent operations to enable learning
and pattern detection. Each entry includes full context, impact, lessons learned,
and fixes applied.

## Purpose

- **Learning Repository**: Not just a log, but a teaching tool
- **Pattern Detection**: Identify repeated error types
- **Instruction Improvement**: Feed back into agent guidelines
- **Continuity**: Help future sessions avoid past mistakes

## Guidelines

- Document mistakes AS THEY HAPPEN, not after being asked
- Include full context and impact
- Focus on lessons learned and prevention
- Cross-reference similar past mistakes

---

"""
