import os
import json
import asyncio
from dotenv import load_dotenv
from mistralai import Mistral

import server

load_dotenv()
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

mcp_tools = asyncio.run(server.mcp.list_tools())

tools = [
    {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.inputSchema,
        },
    }
    for t in mcp_tools
]

messages = [
    {
        "role": "user",
        "content": "What is the full name of team BRA, and what are France's matches?",
    }
]

while True:
    response = client.chat.complete(
        model="mistral-small-latest", messages=messages, tools=tools
    )
    message = response.choices[0].message
    messages.append(message)

    tool_calls = message.tool_calls
    if tool_calls:
        for tool_call in tool_calls:
            args = json.loads(tool_call.function.arguments)
            _blocks, result = asyncio.run(
                server.mcp.call_tool(tool_call.function.name, args)
            )
            messages.append(
                {
                    "role": "tool",
                    "name": tool_call.function.name,
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )
    else:
        print(message.content)
        break
