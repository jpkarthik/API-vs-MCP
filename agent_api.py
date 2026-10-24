"""Groq chooses app-defined functions; this app calls the Ticket API."""

import json
import os

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
BASE_URL = os.getenv("TICKET_API_URL", os.getenv("TASK_API_URL", "http://127.0.0.1:8000"))


def run_api_function(name: str, arguments: dict) -> dict | list[dict]:
    if name == "create_ticket":
        response = requests.post(f"{BASE_URL}/tickets", json=arguments, timeout=10)
    elif name == "list_tickets":
        params = {"status": arguments["status"]} if arguments.get("status") else None
        response = requests.get(f"{BASE_URL}/tickets", params=params, timeout=10)
    elif name == "get_ticket":
        response = requests.get(f"{BASE_URL}/tickets/{arguments['ticket_id']}", timeout=10)
    elif name == "update_ticket_status":
        ticket_id = arguments["ticket_id"]
        response = requests.patch(
            f"{BASE_URL}/tickets/{ticket_id}/status",
            json={"status": arguments["status"]},
            timeout=10,
        )
    else:
        raise ValueError(f"Unknown function: {name}")
    response.raise_for_status()
    return response.json()


def main() -> None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise SystemExit("Set GROQ_API_KEY in .env1")
    client = Groq(api_key=key)
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # The app writes these schemas by hand and maps each function to an endpoint.
    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_ticket",
                "description": "Create a support ticket for a customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                    },
                    "required": ["customer_name", "subject", "description", "priority"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_tickets",
                "description": "List support tickets, optionally filtering by status.",
                "parameters": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "enum": ["open", "in_progress", "closed"]}},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_ticket",
                "description": "Get a support ticket by numeric ID.",
                "parameters": {
                    "type": "object",
                    "properties": {"ticket_id": {"type": "integer"}},
                    "required": ["ticket_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_ticket_status",
                "description": "Change a ticket status to open, in_progress, or closed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "integer"},
                        "status": {"type": "string", "enum": ["open", "in_progress", "closed"]},
                    },
                    "required": ["ticket_id", "status"],
                },
            },
        },
    ]

    prompt = input("What should I do with support tickets? ").strip()
    messages = [{"role": "user", "content": prompt}]
    # A request may require several calls, such as listing tickets first and
    # then updating the matching ticket. Keep tools available on each round.
    for _ in range(5):
        response = client.chat.completions.create(model=model, messages=messages, tools=tools)
        assistant_message = response.choices[0].message
        calls = assistant_message.tool_calls or []
        messages.append(assistant_message)
        if not calls:
            print("\nAssistant:", assistant_message.content or "The model returned no text.")
            return

        for call in calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments)
                result = run_api_function(name, args)
            except Exception as error:
                result = {"error": str(error)}
            print(f"Your Python code called the Ticket API for {name}: {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": name,
                "content": json.dumps(result),
            })
    else:
        print("Stopped after 5 tool rounds to avoid an endless tool-call loop.")


if __name__ == "__main__":
    main()
