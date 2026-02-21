"""
Feedback system for DAPY

Allows users to submit feedback about issues, unexpected behavior,
or suggestions. Feedback is stored in LangSmith for Manus to review
and create tickets.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import os
from pathlib import Path
import json

from langsmith import Client
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


class FeedbackManager:
    """
    Manages user feedback submission and retrieval.
    
    Uses LangSmith's feedback API to store and track feedback.
    """
    
    def __init__(self):
        """Initialize feedback manager with LangSmith client."""
        self.client = Client()
        self.project_name = os.environ.get('LANGCHAIN_PROJECT', 'dapy-dev')
    
    def submit_feedback(
        self,
        description: str,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        attach_recent_snapshots: bool = True
    ) -> str:
        """
        Submit feedback to LangSmith.
        
        Args:
            description: Free-form description of the issue
            category: Optional category (bug, feature, improvement, question)
            severity: Optional severity (low, medium, high, critical)
            context: Optional additional context
            attach_recent_snapshots: Whether to attach recent snapshot info
            
        Returns:
            Feedback ID
        """
        # Prepare feedback data
        feedback_data = {
            'description': description,
            'category': category or 'bug',
            'severity': severity or 'medium',
            'timestamp': datetime.now().isoformat(),
            'project': self.project_name,
            'status': 'submitted',
        }
        
        # Add context
        if context:
            feedback_data['context'] = context
        
        # Attach recent snapshot info if requested
        if attach_recent_snapshots:
            snapshot_info = self._get_recent_snapshot_info()
            if snapshot_info:
                feedback_data['recent_snapshots'] = snapshot_info
        
        # Submit to LangSmith as feedback
        # Note: LangSmith feedback API requires a run_id, so we'll create a dummy run
        # or use the most recent run if available
        try:
            # Create feedback key
            feedback_key = f"user_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store in LangSmith dataset for feedback tracking
            # This creates a record that Manus can query
            dataset_name = f"{self.project_name}_feedback"
            
            # Create or get dataset
            try:
                dataset = self.client.create_dataset(
                    dataset_name=dataset_name,
                    description="User feedback for DAPY"
                )
            except Exception:
                # Dataset already exists
                dataset = self.client.read_dataset(dataset_name=dataset_name)
            
            # Add feedback as example
            self.client.create_example(
                inputs={"feedback_key": feedback_key},
                outputs=feedback_data,
                dataset_id=dataset.id,
                metadata={
                    "type": "user_feedback",
                    "category": category or 'bug',
                    "severity": severity or 'medium',
                    "status": "submitted",
                    "submitted_at": datetime.now().isoformat()
                }
            )
            
            return feedback_key
        
        except Exception as e:
            console.print(f"[yellow]Warning: Could not submit to LangSmith: {e}[/yellow]")
            # Fallback: save locally
            return self._save_feedback_locally(feedback_data)
    
    def _get_recent_snapshot_info(self) -> Optional[List[Dict[str, Any]]]:
        """Get info about recent snapshots."""
        snapshot_dir = Path('./snapshots')
        
        if not snapshot_dir.exists():
            return None
        
        snapshots = sorted(
            snapshot_dir.glob('snapshot_*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:5]  # Last 5 snapshots
        
        snapshot_info = []
        for snapshot_file in snapshots:
            try:
                with open(snapshot_file) as f:
                    data = json.load(f)
                
                snapshot_info.append({
                    'file': snapshot_file.name,
                    'timestamp': data.get('timestamp'),
                    'type': data.get('type'),
                    'metadata': data.get('metadata', {})
                })
            except Exception:
                continue
        
        return snapshot_info if snapshot_info else None
    
    def _save_feedback_locally(self, feedback_data: Dict[str, Any]) -> str:
        """Fallback: save feedback locally."""
        feedback_dir = Path('./feedback')
        feedback_dir.mkdir(exist_ok=True)
        
        feedback_key = f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        feedback_file = feedback_dir / f"{feedback_key}.json"
        
        with open(feedback_file, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        
        return feedback_key
    
    def get_feedback_status(self, feedback_key: str) -> Optional[Dict[str, Any]]:
        """
        Get status of submitted feedback.
        
        Args:
            feedback_key: Feedback identifier
            
        Returns:
            Feedback status or None if not found
        """
        try:
            dataset_name = f"{self.project_name}_feedback"
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            
            # Search for feedback
            examples = list(self.client.list_examples(dataset_id=dataset.id))
            
            for example in examples:
                if example.inputs.get('feedback_key') == feedback_key:
                    return {
                        'feedback_key': feedback_key,
                        'data': example.outputs,
                        'metadata': example.metadata,
                        'created_at': example.created_at.isoformat() if example.created_at else None
                    }
            
            return None
        
        except Exception as e:
            console.print(f"[yellow]Could not retrieve feedback status: {e}[/yellow]")
            return None
    
    def list_my_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent feedback submissions.
        
        Args:
            limit: Number of recent feedback items to return
            
        Returns:
            List of feedback items
        """
        try:
            dataset_name = f"{self.project_name}_feedback"
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            
            examples = list(self.client.list_examples(dataset_id=dataset.id, limit=limit))
            
            feedback_list = []
            for example in examples:
                feedback_list.append({
                    'feedback_key': example.inputs.get('feedback_key'),
                    'description': example.outputs.get('description', 'No description'),
                    'category': example.outputs.get('category', 'unknown'),
                    'severity': example.outputs.get('severity', 'unknown'),
                    'status': example.metadata.get('status', 'submitted'),
                    'submitted_at': example.metadata.get('submitted_at', 'unknown'),
                })
            
            return feedback_list
        
        except Exception as e:
            console.print(f"[yellow]Could not list feedback: {e}[/yellow]")
            return []


def submit_feedback_interactive() -> Optional[str]:
    """
    Interactive feedback submission.
    
    Prompts user for feedback details and submits to LangSmith.
    
    Returns:
        Feedback ID or None if cancelled
    """
    console.print(Panel(
        "[bold cyan]Submit Feedback[/bold cyan]\n\n"
        "Help us improve DAPY by reporting issues or suggestions.",
        border_style="cyan"
    ))
    
    # Get description
    console.print("\n[bold]What went wrong or what would you like to see improved?[/bold]")
    console.print("[dim]Describe the issue in detail. Press Ctrl+D when done.[/dim]\n")
    
    description_lines = []
    try:
        while True:
            line = input()
            description_lines.append(line)
    except EOFError:
        pass
    
    description = '\n'.join(description_lines).strip()
    
    if not description:
        console.print("[yellow]Feedback cancelled - no description provided[/yellow]")
        return None
    
    # Get category
    console.print("\n[bold]Category:[/bold]")
    console.print("  1. Bug - Something isn't working")
    console.print("  2. Feature - New functionality request")
    console.print("  3. Improvement - Enhancement to existing feature")
    console.print("  4. Question - Need clarification")
    
    category_choice = Prompt.ask("Select category", choices=["1", "2", "3", "4"], default="1")
    category_map = {
        "1": "bug",
        "2": "feature",
        "3": "improvement",
        "4": "question"
    }
    category = category_map[category_choice]
    
    # Get severity
    console.print("\n[bold]Severity:[/bold]")
    console.print("  1. Low - Minor issue")
    console.print("  2. Medium - Moderate impact")
    console.print("  3. High - Significant issue")
    console.print("  4. Critical - Blocking work")
    
    severity_choice = Prompt.ask("Select severity", choices=["1", "2", "3", "4"], default="2")
    severity_map = {
        "1": "low",
        "2": "medium",
        "3": "high",
        "4": "critical"
    }
    severity = severity_map[severity_choice]
    
    # Attach snapshots?
    attach_snapshots = Confirm.ask(
        "\nAttach recent execution snapshots?",
        default=True
    )
    
    # Submit
    console.print("\n[cyan]Submitting feedback...[/cyan]")
    
    manager = FeedbackManager()
    feedback_key = manager.submit_feedback(
        description=description,
        category=category,
        severity=severity,
        attach_recent_snapshots=attach_snapshots
    )
    
    console.print(f"\n[bold green]✓[/bold green] Feedback submitted: {feedback_key}")
    console.print("\n[dim]Manus will review and create a ticket to address this.[/dim]")
    console.print(f"[dim]Track status with: dapy feedback status {feedback_key}[/dim]")
    
    return feedback_key


def show_feedback_list(limit: int = 10) -> None:
    """Show list of submitted feedback."""
    manager = FeedbackManager()
    feedback_list = manager.list_my_feedback(limit=limit)
    
    if not feedback_list:
        console.print("[yellow]No feedback found[/yellow]")
        return
    
    from rich.table import Table
    
    table = Table(title=f"Your Feedback (Last {len(feedback_list)})")
    table.add_column("Key", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Category", style="yellow")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="green")
    table.add_column("Submitted", style="dim")
    
    for item in feedback_list:
        # Truncate description
        desc = item['description'][:50] + '...' if len(item['description']) > 50 else item['description']
        
        # Format submitted time
        submitted = item['submitted_at']
        if 'T' in submitted:
            try:
                dt = datetime.fromisoformat(submitted)
                submitted = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        table.add_row(
            item['feedback_key'],
            desc,
            item['category'],
            item['severity'],
            item['status'],
            submitted
        )
    
    console.print(table)


def show_feedback_status(feedback_key: str) -> None:
    """Show status of specific feedback."""
    manager = FeedbackManager()
    status = manager.get_feedback_status(feedback_key)
    
    if not status:
        console.print(f"[yellow]Feedback not found: {feedback_key}[/yellow]")
        return
    
    console.print(Panel(
        f"[bold]Feedback Status[/bold]\n\n"
        f"Key: {feedback_key}\n"
        f"Status: {status['metadata'].get('status', 'unknown')}\n"
        f"Category: {status['data'].get('category', 'unknown')}\n"
        f"Severity: {status['data'].get('severity', 'unknown')}\n"
        f"Submitted: {status.get('created_at', 'unknown')}",
        border_style="cyan"
    ))
    
    console.print("\n[bold]Description:[/bold]")
    console.print(status['data'].get('description', 'No description'))
    
    # Show resolution if available
    if 'resolution' in status['metadata']:
        console.print("\n[bold green]Resolution:[/bold green]")
        console.print(status['metadata']['resolution'])
