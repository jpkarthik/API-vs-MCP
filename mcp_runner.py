"""Run a Groq prompt using tools discovered from the local ticket MCP server."""

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from mcp import Client, StdioServerParameters

load_dotenv()
PROJECT_DIR = Path(__file__).parent


def get_tool_schema(tool: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def run_mcp_prompt(prompt: str) -> dict[str, Any]:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("Set GROQ_API_KEY in your local .env file")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq = Groq(api_key=key)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_DIR / "mcp_server.py")],
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    tool_calls: list[dict[str, Any]] = []
    async with Client(server) as mcp_client:
        listing = await mcp_client.list_tools()
        tools = [get_tool_schema(tool) for tool in listing.tools]
        messages: list[Any] = [{"role": "user", "content": prompt}]

        for _ in range(5):
            response = groq.chat.completions.create(model=model, messages=messages, tools=tools)
            assistant_message = response.choices[0].message
            calls = assistant_message.tool_calls or []
            messages.append(assistant_message)
            if not calls:
                return {
                    "tools": [tool.name for tool in listing.tools],
                    "tool_calls": tool_calls,
                    "answer": assistant_message.content or "The model returned no text.",
                }

            for call in calls:
                name = call.function.name
                arguments: dict[str, Any] = {}
                try:
                    arguments = json.loads(call.function.arguments)
                    result = await mcp_client.call_tool(name, arguments)
                    if result.is_error:
                        output: Any = {
                            "error": [getattr(block, "text", "Tool failed") for block in result.content]
                        }
                    else:
                        output = result.structured_content
                        if output is None:
                            output = [getattr(block, "text", str(block)) for block in result.content]
                except Exception as error:
                    output = {"error": str(error)}

                tool_calls.append({"name": name, "arguments": arguments, "result": output})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": json.dumps(output, default=str),
                })

    return {
        "tools": [],
        "tool_calls": tool_calls,
        "answer": "Stopped after 5 tool rounds to avoid an endless tool-call loop.",
    }
