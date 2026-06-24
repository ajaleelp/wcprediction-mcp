import os
import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.extra.run.context import RunContext
from mistralai.extra.mcp.stdio import MCPClientSTDIO
from mcp import StdioServerParameters

load_dotenv()
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

agent = client.beta.agents.create(
    model="mistral-small-latest",
    name="wc-assistant",
    instructions="Answer the user's World Cup questions using the available tools."
)

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).parent / "server.py")]
)

async def main():
    async with RunContext(agent_id=agent.id, continue_on_fn_error=True) as run_ctx:
        mcp_client = MCPClientSTDIO(stdio_params=server_params)
        await run_ctx.register_mcp_client(mcp_client=mcp_client)

        result = await client.beta.conversations.run_async(
            run_ctx=run_ctx,
            inputs="What is the full name of team BRA, and what are France's matches?"
        )
        print(result.output_as_text)

asyncio.run(main())