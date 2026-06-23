import json
from pathlib import Path

import game_data

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


@mcp.tool()
def get_matches_for_team(code: str) -> list[dict]:
    """List a team's World Cup matches (kick-off, stage, venue, opponents, and score if played) by team code like BRA."""
    return game_data.matches_for_team(code)

if __name__ == "__main__":
    mcp.run()
    