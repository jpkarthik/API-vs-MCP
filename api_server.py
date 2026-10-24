"""REST API for support tickets stored in SQLite."""

from typing import Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import create_ticket, get_ticket, list_tickets, update_ticket_status

app = FastAPI(title="Support Ticket API", description="REST API used in the API vs MCP demo")
UI_FILE = Path(__file__).parent / "static" / "index.html"


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    priority: Literal["low", "normal", "high"] = "normal"


class TicketStatusUpdate(BaseModel):
    status: Literal["open", "in_progress", "closed"]


class MCPPrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


@app.get("/")
def home() -> dict[str, str]:
    return {
        "message": "Support Ticket API is running. Open /ui for the dashboard or /docs for API endpoints.",
        "ui": "/ui",
        "docs": "/docs",
    }


@app.get("/ui", include_in_schema=False)
def ticket_dashboard() -> FileResponse:
    return FileResponse(UI_FILE, media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tickets")
def tickets(status: Literal["open", "in_progress", "closed"] | None = None) -> list[dict]:
    return list_tickets(status)


@app.post("/tickets", status_code=201)
def tickets_create(ticket: TicketCreate) -> dict:
    return create_ticket(ticket.model_dump())


@app.get("/tickets/{ticket_id}")
def ticket_get(ticket_id: int) -> dict:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/tickets/{ticket_id}/status")
def ticket_status_update(ticket_id: int, update: TicketStatusUpdate) -> dict:
    ticket = update_ticket_status(ticket_id, update.status)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.post("/mcp/chat", include_in_schema=False)
async def mcp_chat(request: MCPPrompt) -> dict:
    """Let the local MCP host run a Groq prompt from the browser workbench."""
    from mcp_runner import run_mcp_prompt

    try:
        return await run_mcp_prompt(request.prompt)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"MCP/Groq request failed: {error}") from error
