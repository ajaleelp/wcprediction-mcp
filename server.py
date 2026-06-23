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


@mcp.tool()
def get_team(code: str) -> dict | None:
    """Returns the code, full name, short name and flag of a team with the given code like BRA"""
    teams = json.loads(TEAMS_PATH.read_text())
    for team in teams:
        if team['code'] == code.upper():
            return team
    return None

if __name__ == "__main__":
    mcp.run()
    