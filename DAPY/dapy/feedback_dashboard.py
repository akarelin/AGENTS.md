"""
Feedback Dashboard

Web-based dashboard for tracking feedback submissions and resolutions.
Shows what's been submitted, ticket status, and agent activity.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

from dapy.feedback_agent import FeedbackMonitoringAgent, Ticket

app = FastAPI(
    title="DAPY Feedback Dashboard",
    description="Track feedback submissions and resolutions",
    version="0.1.0"
)

# Initialize feedback agent (read-only mode for dashboard)
agent = FeedbackMonitoringAgent()


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page."""
    return HTMLResponse(content=generate_dashboard_html())


@app.get("/api/tickets")
async def get_tickets():
    """Get all tickets."""
    tickets = agent.list_all_tickets()
    return {
        "tickets": [t.to_dict() for t in tickets],
        "count": len(tickets)
    }


@app.get("/api/tickets/open")
async def get_open_tickets():
    """Get open tickets."""
    tickets = agent.list_open_tickets()
    return {
        "tickets": [t.to_dict() for t in tickets],
        "count": len(tickets)
    }


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get specific ticket."""
    ticket = agent._load_ticket(ticket_id)
    
    if not ticket:
        return {"error": "Ticket not found"}, 404
    
    return ticket.to_dict()


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    all_tickets = agent.list_all_tickets()
    
    stats = {
        "total_tickets": len(all_tickets),
        "open_tickets": len([t for t in all_tickets if t.status == 'open']),
        "resolved_tickets": len([t for t in all_tickets if t.status == 'resolved']),
        "by_category": {},
        "by_severity": {},
        "recent_activity": []
    }
    
    # Count by category
    for ticket in all_tickets:
        stats["by_category"][ticket.category] = stats["by_category"].get(ticket.category, 0) + 1
        stats["by_severity"][ticket.severity] = stats["by_severity"].get(ticket.severity, 0) + 1
    
    # Recent activity (last 10 tickets)
    for ticket in all_tickets[:10]:
        stats["recent_activity"].append({
            "ticket_id": ticket.ticket_id,
            "description": ticket.description[:100],
            "status": ticket.status,
            "created_at": ticket.created_at
        })
    
    return stats


def generate_dashboard_html() -> str:
    """Generate dashboard HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DAPY Feedback Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            margin-bottom: 40px;
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .stat-label {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #f1f5f9;
        }
        
        .tickets-section {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 1.5rem;
            color: #f1f5f9;
        }
        
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.2s;
        }
        
        .refresh-btn:hover {
            background: #5568d3;
        }
        
        .tickets-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .tickets-table th {
            text-align: left;
            padding: 12px;
            color: #94a3b8;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid #334155;
        }
        
        .tickets-table td {
            padding: 16px 12px;
            border-bottom: 1px solid #334155;
        }
        
        .tickets-table tr:hover {
            background: #2d3748;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .status-open {
            background: #fef3c7;
            color: #92400e;
        }
        
        .status-resolved {
            background: #d1fae5;
            color: #065f46;
        }
        
        .severity-critical {
            color: #ef4444;
        }
        
        .severity-high {
            color: #f59e0b;
        }
        
        .severity-medium {
            color: #3b82f6;
        }
        
        .severity-low {
            color: #10b981;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #94a3b8;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #64748b;
        }
        
        .empty-state-icon {
            font-size: 4rem;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DAPY Feedback Dashboard</h1>
            <p class="subtitle">Track feedback submissions and agent resolutions</p>
        </header>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-label">Total Tickets</div>
                <div class="stat-value" id="total-tickets">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Open Tickets</div>
                <div class="stat-value" id="open-tickets">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Resolved</div>
                <div class="stat-value" id="resolved-tickets">-</div>
            </div>
        </div>
        
        <div class="tickets-section">
            <div class="section-header">
                <h2 class="section-title">Recent Tickets</h2>
                <button class="refresh-btn" onclick="loadData()">Refresh</button>
            </div>
            <div id="tickets-container">
                <div class="loading">Loading tickets...</div>
            </div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                // Load stats
                const statsResponse = await fetch('/api/stats');
                const stats = await statsResponse.json();
                
                document.getElementById('total-tickets').textContent = stats.total_tickets;
                document.getElementById('open-tickets').textContent = stats.open_tickets;
                document.getElementById('resolved-tickets').textContent = stats.resolved_tickets;
                
                // Load tickets
                const ticketsResponse = await fetch('/api/tickets');
                const ticketsData = await ticketsResponse.json();
                
                renderTickets(ticketsData.tickets);
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('tickets-container').innerHTML = 
                    '<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Error loading tickets</p></div>';
            }
        }
        
        function renderTickets(tickets) {
            const container = document.getElementById('tickets-container');
            
            if (tickets.length === 0) {
                container.innerHTML = 
                    '<div class="empty-state"><div class="empty-state-icon">📭</div><p>No tickets yet</p></div>';
                return;
            }
            
            const table = `
                <table class="tickets-table">
                    <thead>
                        <tr>
                            <th>Ticket ID</th>
                            <th>Description</th>
                            <th>Category</th>
                            <th>Severity</th>
                            <th>Status</th>
                            <th>Created</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tickets.map(ticket => `
                            <tr>
                                <td><strong>${ticket.ticket_id}</strong></td>
                                <td>${truncate(ticket.description, 80)}</td>
                                <td>${ticket.category}</td>
                                <td class="severity-${ticket.severity}">${ticket.severity}</td>
                                <td><span class="status-badge status-${ticket.status}">${ticket.status}</span></td>
                                <td>${formatDate(ticket.created_at)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            container.innerHTML = table;
        }
        
        function truncate(str, length) {
            return str.length > length ? str.substring(0, length) + '...' : str;
        }
        
        function formatDate(isoString) {
            const date = new Date(isoString);
            return date.toLocaleString();
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>
    """


def main():
    """Run dashboard server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8889)


if __name__ == '__main__':
    main()
