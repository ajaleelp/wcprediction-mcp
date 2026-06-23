import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP('wcprediction')

TEAMS_PATH = Path(__file__).parent / "data" / "teams.json"


@mcp.tool()
def list_teams() -> list[dict]:
    """List all 48 teams in the 2026 World Cup, each with its code, full name, short name, and flag."""
    teams = json.loads(TEAMS_PATH.read_text())
    return teams

if __name__ == "__main__":
    mcp.run()
    