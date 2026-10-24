"""Expose the support-ticket API through MCP tools and a resource."""

import os
from typing import Literal

import requests
from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv()
BASE_URL = os.getenv("TICKET_API_URL", os.getenv("TASK_API_URL", "http://127.0.0.1:8000"))
mcp = MCPServer("api-vs-mcp-ticket-tools")


@mcp.tool()
def create_ticket(
    customer_name: str,
    subject: str,
    description: str,
    priority: Literal["low", "normal", "high"] = "normal",
) -> dict:
    """Create a support ticket for a customer through the Ticket API."""
    response = requests.post(
        f"{BASE_URL}/tickets",
        json={
            "customer_name": customer_name,
            "subject": subject,
            "description": description,
            "priority": priority,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def list_tickets(
    status: Literal["open", "in_progress", "closed"] | None = None,
) -> list[dict]:
    """List support tickets, optionally filtering by status."""
    params = {"status": status} if status else None
    response = requests.get(f"{BASE_URL}/tickets", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Get one support ticket by its numeric ID."""
    response = requests.get(f"{BASE_URL}/tickets/{ticket_id}", timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def update_ticket_status(
    ticket_id: int,
    status: Literal["open", "in_progress", "closed"],
) -> dict:
    """Change a ticket's status to open, in_progress, or closed."""
    response = requests.patch(
        f"{BASE_URL}/tickets/{ticket_id}/status",
        json={"status": status},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


@mcp.resource("ticket-api://overview")
def ticket_api_overview() -> str:
    """Explain the ticket fields and available statuses."""
    return (
        "The Ticket API stores customer_name, subject, description, priority, status, "
        "and created_at. Priorities: low, normal, high. Statuses: open, in_progress, closed."
    )


if __name__ == "__main__":
    # MCP uses stdio here: the AI host launches this process and exchanges
    # protocol messages over stdin/stdout. Keep print/debug output off stdout.
    mcp.run()
