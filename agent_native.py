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
    instructions=(
    "You are a football assistant. Answer STRICTLY using the information returned by the "
    "tools (the knowledge base and live data). Do not use your own prior knowledge. "
    "If the tools don't provide enough to answer, say you don't have that information "
    "rather than guessing. When you state a fact, it must come from a tool result."
    )
)

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(Path(__file__).parent / "server.py")]
)

async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "How did Brazil perform in past World Cups compared to france?"
    async with RunContext(agent_id=agent.id, continue_on_fn_error=True) as run_ctx:
        mcp_client = MCPClientSTDIO(stdio_params=server_params)
        await run_ctx.register_mcp_client(mcp_client=mcp_client)

        result = await client.beta.conversations.run_async(
            run_ctx=run_ctx,
            inputs=query
        )
        print(result.output_as_text)

asyncio.run(main())