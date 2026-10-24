"""Groq selects tools discovered from a local MCP server."""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq
from mcp import Client, StdioServerParameters

load_dotenv()


def get_tool_schema(tool) -> dict:
    """Convert an MCP-discovered tool to Groq's function-tool shape."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def main() -> None:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise SystemExit("Set GROQ_API_KEY in .env1")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq = Groq(api_key=key)

    # The host launches the MCP server as a subprocess. MCP handles discovery
    # and calls; the server then uses HTTP to reach the underlying Ticket API.
    server = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(os.path.dirname(__file__), "mcp_server.py")],
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    async with Client(server) as mcp_client:
        listing = await mcp_client.list_tools()
        print("Tools discovered from MCP server:", [tool.name for tool in listing.tools])
        tools = [get_tool_schema(tool) for tool in listing.tools]

        prompt = input("What should I do with support tickets? ").strip()
        messages = [{"role": "user", "content": prompt}]
        # A request may need a chain of tools, e.g. find Asha's ticket and
        # then update its status. Keep offering tools until Groq answers or
        # the safety limit is reached.
        for _ in range(5):
            response = groq.chat.completions.create(model=model, messages=messages, tools=tools)
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
                    result = await mcp_client.call_tool(name, args)
                    if result.is_error:
                        tool_output = {"error": [getattr(block, "text", "Tool failed") for block in result.content]}
                    else:
                        tool_output = result.structured_content
                        if tool_output is None:
                            tool_output = [getattr(block, "text", str(block)) for block in result.content]
                except Exception as error:
                    tool_output = {"error": str(error)}

                print(f"MCP tool {name} returned: {tool_output}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": json.dumps(tool_output),
                })
        else:
            print("Stopped after 5 tool rounds to avoid an endless tool-call loop.")


if __name__ == "__main__":
    asyncio.run(main())
