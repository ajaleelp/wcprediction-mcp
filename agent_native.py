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
        "You are a World Cup 2026 match-prep analyst for a prediction game. The player makes the "
        "actual pick — your job is to arm that decision, not make it.\n\n"
        "For a match question, gather grounded evidence before answering:\n"
        "- use the tools for each team's current form and World Cup history;\n"
        "- use web search for the latest news, injuries, and suspensions.\n\n"
        "Then brief the player on what to weigh: recent form, what's at stake, key news/injuries, "
        "and how each team is likely to play (aggressive vs defensive). Conclude with a HEDGED "
        "LEAN — the likely favourite and whether the game looks high- or low-scoring — with your "
        "reasoning.\n\n"
        "Hard rules: never state an exact scoreline (that is the player's call); never assert a "
        "fact that isn't backed by a tool result or a cited web source; if the evidence is thin, "
        "say so rather than guess."
    ),
    tools=[{ "type": "web_search"}]
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