import json
from pathlib import Path

import football_data
import game_data
import live_data
import rag

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


@mcp.tool()
def get_world_cup_record(team: str) -> dict:
    """Return a national team's all-time World Cup title record — how many titles and which
    years — by team name like 'Brazil'. Use for historical 'has X ever won the World Cup' or
    'how many World Cups has X won' questions; returns 0 titles for teams that never won."""
    return football_data.world_cup_record(team)


@mcp.tool()
def get_current_form(team: str) -> dict:
    """Return a team's form in the CURRENT 2026 World Cup — matches played so far, win/draw/loss
    record, goals for/against, and per-match results — by team name like 'Brazil'. Use for
    'how is X doing this World Cup' / current-form / recent-results questions. Fetched live from
    openfootball and refreshed around match times; NOT for all-time history (use get_world_cup_record)."""
    return live_data.current_form(team)


@mcp.tool()
def search_knowledge(query: str) -> list[dict]:
    """Search the football knowledge base (team histories, notable players, World Cup
    records, playing styles) for background passages relevant to a question. Use this for
    historical or background questions — NOT for live fixtures, results, or standings."""
    return rag.search(query)

if __name__ == "__main__":
    mcp.run()
    