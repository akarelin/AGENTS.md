"""
Feedback Monitoring Agent

Monitors LangSmith for new user feedback, analyzes issues,
creates tickets, and tracks resolutions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import time

from langsmith import Client
from rich.console import Console

console = Console()


class Ticket:
    """Represents a feedback ticket."""
    
    def __init__(
        self,
        ticket_id: str,
        feedback_key: str,
        description: str,
        category: str,
        severity: str,
        status: str = "open",
        created_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
        resolution: Optional[str] = None
    ):
        self.ticket_id = ticket_id
        self.feedback_key = feedback_key
        self.description = description
        self.category = category
        self.severity = severity
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.resolved_at = resolved_at
        self.resolution = resolution
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary."""
        return {
            'ticket_id': self.ticket_id,
            'feedback_key': self.feedback_key,
            'description': self.description,
            'category': self.category,
            'severity': self.severity,
            'status': self.status,
            'created_at': self.created_at,
            'resolved_at': self.resolved_at,
            'resolution': self.resolution
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ticket':
        """Create ticket from dictionary."""
        return cls(**data)


class FeedbackMonitoringAgent:
    """
    Agent that monitors feedback and creates tickets.

    Runs as a background service, checking for new feedback
    periodically and creating tickets for resolution.
    """
    
    def __init__(
        self,
        project_name: str = "dapy-dev",
        tickets_dir: str = "./tickets",
        check_interval: int = 60
    ):
        """
        Initialize feedback monitoring agent.
        
        Args:
            project_name: LangSmith project name
            tickets_dir: Directory to store ticket data
            check_interval: Seconds between checks
        """
        self.client = Client()
        self.project_name = project_name
        self.tickets_dir = Path(tickets_dir)
        self.tickets_dir.mkdir(exist_ok=True, parents=True)
        self.check_interval = check_interval
        
        # Track processed feedback
        self.processed_feedback = self._load_processed_feedback()
    
    def _load_processed_feedback(self) -> set:
        """Load set of already processed feedback keys."""
        processed_file = self.tickets_dir / 'processed_feedback.json'
        
        if processed_file.exists():
            with open(processed_file) as f:
                return set(json.load(f))
        
        return set()
    
    def _save_processed_feedback(self) -> None:
        """Save processed feedback keys."""
        processed_file = self.tickets_dir / 'processed_feedback.json'
        
        with open(processed_file, 'w') as f:
            json.dump(list(self.processed_feedback), f)
    
    def check_for_new_feedback(self) -> List[Dict[str, Any]]:
        """
        Check LangSmith for new feedback.
        
        Returns:
            List of new feedback items
        """
        try:
            dataset_name = f"{self.project_name}_feedback"
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            
            examples = list(self.client.list_examples(dataset_id=dataset.id))
            
            new_feedback = []
            for example in examples:
                feedback_key = example.inputs.get('feedback_key')
                
                # Skip if already processed
                if feedback_key in self.processed_feedback:
                    continue
                
                # Check if status is still "submitted"
                status = example.metadata.get('status', 'submitted')
                if status != 'submitted':
                    continue
                
                new_feedback.append({
                    'feedback_key': feedback_key,
                    'data': example.outputs,
                    'metadata': example.metadata,
                    'example_id': example.id
                })
            
            return new_feedback
        
        except Exception as e:
            console.print(f"[red]Error checking feedback: {e}[/red]")
            return []
    
    def create_ticket(self, feedback: Dict[str, Any]) -> Ticket:
        """
        Create ticket from feedback.
        
        Args:
            feedback: Feedback data
            
        Returns:
            Created ticket
        """
        feedback_key = feedback['feedback_key']
        data = feedback['data']
        
        # Generate ticket ID
        ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create ticket
        ticket = Ticket(
            ticket_id=ticket_id,
            feedback_key=feedback_key,
            description=data.get('description', 'No description'),
            category=data.get('category', 'unknown'),
            severity=data.get('severity', 'medium'),
            status='open'
        )
        
        # Save ticket
        self._save_ticket(ticket)
        
        # Mark feedback as processed
        self.processed_feedback.add(feedback_key)
        self._save_processed_feedback()
        
        # Update feedback status in LangSmith
        self._update_feedback_status(
            feedback['example_id'],
            status='in_progress',
            ticket_id=ticket_id
        )
        
        console.print(f"[green]Created ticket {ticket_id} for feedback {feedback_key}[/green]")
        
        return ticket
    
    def _save_ticket(self, ticket: Ticket) -> None:
        """Save ticket to disk."""
        ticket_file = self.tickets_dir / f"{ticket.ticket_id}.json"
        
        with open(ticket_file, 'w') as f:
            json.dump(ticket.to_dict(), f, indent=2)
    
    def _load_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Load ticket from disk."""
        ticket_file = self.tickets_dir / f"{ticket_id}.json"
        
        if not ticket_file.exists():
            return None
        
        with open(ticket_file) as f:
            data = json.load(f)
        
        return Ticket.from_dict(data)
    
    def _update_feedback_status(
        self,
        example_id: str,
        status: str,
        ticket_id: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> None:
        """Update feedback status in LangSmith."""
        try:
            # Update example metadata
            metadata = {'status': status}
            if ticket_id:
                metadata['ticket_id'] = ticket_id
            if resolution:
                metadata['resolution'] = resolution
                metadata['resolved_at'] = datetime.now().isoformat()
            
            # Note: LangSmith doesn't have direct example update,
            # so we'll track this in our local tickets
            # In production, you might use LangSmith annotations or custom fields
        
        except Exception as e:
            console.print(f"[yellow]Could not update feedback status: {e}[/yellow]")
    
    def resolve_ticket(
        self,
        ticket_id: str,
        resolution: str
    ) -> bool:
        """
        Mark ticket as resolved.
        
        Args:
            ticket_id: Ticket identifier
            resolution: Resolution description
            
        Returns:
            True if successful
        """
        ticket = self._load_ticket(ticket_id)
        
        if not ticket:
            console.print(f"[red]Ticket not found: {ticket_id}[/red]")
            return False
        
        # Update ticket
        ticket.status = 'resolved'
        ticket.resolved_at = datetime.now().isoformat()
        ticket.resolution = resolution
        
        # Save ticket
        self._save_ticket(ticket)
        
        console.print(f"[green]Resolved ticket {ticket_id}[/green]")
        
        return True
    
    def list_open_tickets(self) -> List[Ticket]:
        """List all open tickets."""
        tickets = []
        
        for ticket_file in self.tickets_dir.glob('TICKET-*.json'):
            with open(ticket_file) as f:
                data = json.load(f)
            
            ticket = Ticket.from_dict(data)
            if ticket.status == 'open':
                tickets.append(ticket)
        
        return sorted(tickets, key=lambda t: t.created_at, reverse=True)
    
    def list_all_tickets(self) -> List[Ticket]:
        """List all tickets."""
        tickets = []
        
        for ticket_file in self.tickets_dir.glob('TICKET-*.json'):
            with open(ticket_file) as f:
                data = json.load(f)
            
            tickets.append(Ticket.from_dict(data))
        
        return sorted(tickets, key=lambda t: t.created_at, reverse=True)
    
    def run_once(self) -> int:
        """
        Run one iteration of feedback monitoring.
        
        Returns:
            Number of new tickets created
        """
        console.print("[cyan]Checking for new feedback...[/cyan]")
        
        new_feedback = self.check_for_new_feedback()
        
        if not new_feedback:
            console.print("[dim]No new feedback[/dim]")
            return 0
        
        console.print(f"[yellow]Found {len(new_feedback)} new feedback items[/yellow]")
        
        tickets_created = 0
        for feedback in new_feedback:
            try:
                self.create_ticket(feedback)
                tickets_created += 1
            except Exception as e:
                console.print(f"[red]Error creating ticket: {e}[/red]")
        
        return tickets_created
    
    def run_daemon(self) -> None:
        """
        Run as daemon, continuously monitoring feedback.
        
        Checks for new feedback every `check_interval` seconds.
        """
        console.print(f"[bold green]Feedback Agent Started[/bold green]")
        console.print(f"Project: {self.project_name}")
        console.print(f"Check interval: {self.check_interval}s")
        console.print(f"Tickets directory: {self.tickets_dir}")
        console.print()
        
        try:
            while True:
                self.run_once()
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping feedback agent...[/yellow]")


def main():
    """Main entry point for feedback agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Feedback Monitoring Agent')
    parser.add_argument('--project', default='dapy-dev', help='LangSmith project name')
    parser.add_argument('--tickets-dir', default='./tickets', help='Tickets directory')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    agent = FeedbackMonitoringAgent(
        project_name=args.project,
        tickets_dir=args.tickets_dir,
        check_interval=args.interval
    )
    
    if args.once:
        tickets_created = agent.run_once()
        console.print(f"\n[bold]Created {tickets_created} tickets[/bold]")
    else:
        agent.run_daemon()


if __name__ == '__main__':
    main()
