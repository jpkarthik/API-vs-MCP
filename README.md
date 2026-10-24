# API vs MCP: support ticket example

This demo uses a real SQLite database table called tickets and compares three approaches:

1. A manual REST API request.
2. Groq tool calling where your app defines functions and maps them to API calls.
3. Groq tool calling where an MCP server publishes tools for your app to discover.

## Data model

SQLite stores data in tickets.db beside the Python files. database.py creates a tickets table with id, customer_name, subject, description, priority, status, and created_at. The API and MCP tools operate on this same database. MCP is not another database.

## Architecture

~~~text
Manual REST: PowerShell / api_client.py -> HTTP -> FastAPI -> SQL -> tickets.db
Groq functions: agent_api.py -> Groq chooses app-defined function -> HTTP -> FastAPI -> DB
Groq + MCP: agent_mcp.py -> discovers MCP tools -> Groq chooses tool -> MCP client -> mcp_server.py -> HTTP -> FastAPI -> DB
~~~

## Run in VS Code PowerShell

Use the virtual environment's Python directly; this avoids the PowerShell activation policy issue.

Install/update packages:

~~~powershell
cd D:\002_APIvsMCP
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

Your existing .env with GROQ_API_KEY and GROQ_MODEL can stay as-is. The code also accepts your earlier TASK_API_URL setting.

### 1. Start the API — Terminal 1

~~~powershell
cd D:\002_APIvsMCP
.\.venv\Scripts\python.exe -m uvicorn api_server:app --reload
~~~

Leave Terminal 1 running. Open http://127.0.0.1:8000/docs. Startup creates tickets.db and its tickets table automatically.

Open the two-panel workbench at http://127.0.0.1:8000/ui. The Direct API panel lets you choose an HTTP method, endpoint, and JSON body. The MCP panel sends a prompt to Groq, displays discovered tools and calls, and invokes the local MCP server. Both panels use the same API and SQLite data.

### 2. Make a manual REST call — Terminal 2

This creates a ticket directly through HTTP. No Groq or MCP is involved:

~~~powershell
$body = @{
  customer_name = "Asha Kumar"
  subject = "Cannot sign in"
  description = "The password reset link expires immediately."
  priority = "high"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/tickets -ContentType "application/json" -Body $body
~~~

The API response includes the new ticket ID and status. List tickets with:

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/tickets
~~~

api_client.py makes the same kind of direct call:

~~~powershell
.\.venv\Scripts\python.exe api_client.py
~~~

### Add sample tickets with different statuses

Run this in Terminal 2:

~~~powershell
.\.venv\Scripts\python.exe seed_tickets.py
~~~

The script uses REST POST and PATCH requests to add three sample tickets and set one each to `open`, `in_progress`, and `closed`. It reuses those tickets if you run the script again.

Filter the examples directly through the REST API:

~~~powershell
Invoke-RestMethod "http://127.0.0.1:8000/tickets?status=open"
Invoke-RestMethod "http://127.0.0.1:8000/tickets?status=in_progress"
Invoke-RestMethod "http://127.0.0.1:8000/tickets?status=closed"
~~~

### 3. Use Groq with app-defined functions

~~~powershell
.\.venv\Scripts\python.exe agent_api.py
~~~

Try these prompts:

~~~text
Create a high priority ticket for Asha Kumar: she cannot sign in because the password reset link expires immediately.
List all support tickets.
Set ticket 1 to in progress.
~~~

Here the function schemas and mapping from function names to HTTP requests are written in agent_api.py.

### 4. Use Groq with MCP-discovered tools

~~~powershell
.\.venv\Scripts\python.exe agent_mcp.py
~~~

Try the same prompts. The app first displays the tools it discovered—create_ticket, list_tickets, get_ticket, update_ticket_status. The list_tickets tool accepts an optional status filter. The schemas come from mcp_server.py. That server calls the same REST API, which reads or updates the same SQLite table.

## REST endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /tickets | Read all tickets; optional `?status=open`, `?status=in_progress`, or `?status=closed` filter |
| POST | /tickets | Insert a ticket |
| GET | /tickets/{id} | Read one ticket |
| PATCH | /tickets/{id}/status | Change its status |

Manual status update:

~~~powershell
$body = @{ status = "in_progress" } | ConvertTo-Json
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:8000/tickets/1/status -ContentType "application/json" -Body $body
~~~

## What to compare

| | Manual REST / app-defined function | MCP |
|---|---|---|
| Who describes the tools? | You write schemas in agent_api.py. | MCP server publishes descriptions and schemas. |
| Who runs the selected operation? | Your Python app maps the function to an API request. | MCP client invokes the discovered server tool. |
| Where are ticket records stored? | SQLite via the REST API. | The same SQLite via the same REST API. |

**Takeaway:** The REST API reads and changes ticket rows. MCP standardizes how an AI host discovers and invokes tools that can use the API.

Troubleshooting:
- Connection refused on port 8000: start the API in Terminal 1 and leave it running.
- Groq authentication error: check GROQ_API_KEY in the local .env; never paste the key into chat.
- Ticket not found: list tickets and use an ID that exists.
- To reset demo data, stop the API and remove tickets.db. It is recreated on next startup.

References: [Groq local tool calling](https://console.groq.com/docs/tool-use/local-tool-calling), [official MCP Python SDK](https://py.sdk.modelcontextprotocol.io/).


