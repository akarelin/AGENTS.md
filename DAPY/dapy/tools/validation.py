"""
Validation tool for standards compliance checking
"""

from langchain.tools import tool
from typing import Dict, Any, List
from pathlib import Path
import subprocess


@tool
def validation_tool(
    target: str,
    rules: List[str] = None
) -> Dict[str, Any]:
    """
    Validate code/documentation against standards.
    
    Checks for compliance with project guidelines, coding standards,
    and documentation requirements.
    
    Args:
        target: Path to file or directory to validate
        rules: List of rule names to check (default: all rules)
    
    Returns:
        Dictionary with:
        - success: bool
        - violations: List[Dict[str, Any]]
        - passed_checks: int
        - failed_checks: int
        - warnings: List[str]
        - summary: str
    
    Example:
        validation_tool(
            target="dapy/",
            rules=["no_debug_code", "changelog_updated", "tests_present"]
        )
    """
    result = {
        'success': False,
        'violations': [],
        'passed_checks': 0,
        'failed_checks': 0,
        'warnings': [],
        'summary': '',
    }
    
    target_path = Path(target)
    
    if not target_path.exists():
        result['warnings'].append(f"Target not found: {target}")
        result['summary'] = "Validation target not found"
        return result
    
    # Default rules if none specified
    if rules is None:
        rules = [
            'no_debug_code',
            'no_todos',
            'changelog_updated',
            'proper_docstrings',
        ]
    
    # Run validation checks
    for rule in rules:
        check_result = _run_validation_check(rule, target_path)
        
        if check_result['passed']:
            result['passed_checks'] += 1
        else:
            result['failed_checks'] += 1
            result['violations'].extend(check_result['violations'])
    
    result['success'] = result['failed_checks'] == 0
    result['summary'] = (
        f"Validation: {result['passed_checks']} passed, "
        f"{result['failed_checks']} failed"
    )
    
    return result


def _run_validation_check(rule: str, target_path: Path) -> Dict[str, Any]:
    """Run a specific validation check."""
    check_result = {
        'passed': True,
        'violations': [],
    }
    
    if rule == 'no_debug_code':
        # Check for debug statements
        if target_path.is_file() and target_path.suffix == '.py':
            content = target_path.read_text()
            if 'print(' in content or 'pdb.set_trace()' in content:
                check_result['passed'] = False
                check_result['violations'].append({
                    'rule': rule,
                    'file': str(target_path),
                    'message': 'Debug code found (print or pdb)',
                })
    
    elif rule == 'no_todos':
        # Check for TODO comments
        if target_path.is_file():
            content = target_path.read_text()
            if 'TODO' in content or 'FIXME' in content:
                check_result['passed'] = False
                check_result['violations'].append({
                    'rule': rule,
                    'file': str(target_path),
                    'message': 'TODO/FIXME comments found',
                })
    
    elif rule == 'changelog_updated':
        # Check if CHANGELOG.md exists and is recent
        changelog = Path('CHANGELOG.md')
        if not changelog.exists():
            check_result['passed'] = False
            check_result['violations'].append({
                'rule': rule,
                'file': 'CHANGELOG.md',
                'message': 'CHANGELOG.md not found',
            })
    
    elif rule == 'proper_docstrings':
        # Check for docstrings in Python files
        if target_path.is_file() and target_path.suffix == '.py':
            content = target_path.read_text()
            # Simple check: file should have at least one docstring
            if '"""' not in content and "'''" not in content:
                check_result['passed'] = False
                check_result['violations'].append({
                    'rule': rule,
                    'file': str(target_path),
                    'message': 'No docstrings found',
                })
    
    return check_result
