import sys

import football_data
import game_data
import live_data
import rag
import teams

from mcp.server.fastmcp import FastMCP

mcp = FastMCP('wcprediction')


def _log_tool(name, **kwargs):
    """Log a tool invocation to stderr — stdout is the MCP protocol channel."""
    print(f"[tool] {name} {kwargs}", file=sys.stderr)


def _resolve_or_raise(identifier):
    """Resolve a team code/name/short to its canonical record, or raise so the agent is told."""
    team = teams.resolve(identifier)
    if not team:
        raise ValueError(f"Unknown team '{identifier}'. Use a code like BRA or a name like Brazil.")
    return team


@mcp.tool()
def list_teams() -> list[dict]:
    """List all 48 teams in the 2026 World Cup, each with its code, full name, short name, and flag."""
    _log_tool("list_teams")
    return teams.ALL


@mcp.tool()
def get_team(code: str) -> dict | None:
    """Return the code, full name, short name and flag of a team — by code, full name, or short
    name (e.g. 'BRA' or 'Brazil'). Returns null if there is no such team."""
    _log_tool("get_team", code=code)
    return teams.resolve(code)


@mcp.tool()
def get_matches_for_team(code: str) -> list[dict]:
    """List a team's matches in this World Cup from the prediction game's OWN database — kick-off,
    stage, venue, opponents, and score if played — by team code or name like 'BRA' or 'Brazil'."""
    _log_tool("get_matches_for_team", code=code)
    return game_data.matches_for_team(_resolve_or_raise(code)["code"])


@mcp.tool()
def get_world_cup_titles(team: str) -> dict:
    """Return a team's ALL-TIME World Cup title history — how many titles it has ever won and in
    which years — by team code or name like 'BRA' or 'Brazil'. Use ONLY for historical questions:
    'has X ever won', 'how many World Cups has X won', 'when did X win'. Do NOT use for how a team
    is doing in the CURRENT tournament — use get_current_form. Returns 0 titles if never won."""
    _log_tool("get_world_cup_titles", team=team)
    return football_data.world_cup_record(teams.openfootball_name(_resolve_or_raise(team)))


@mcp.tool()
def get_current_form(team: str) -> dict:
    """Return how a team is doing in the CURRENT, ongoing 2026 World Cup — matches played so far,
    win/draw/loss record, goals, per-match results — by team code or name like 'BRA' or 'Brazil'.
    Use for 'how is X doing / performing', 'X's form', 'how have they played so far', 'recent
    results this World Cup'. Do NOT use for all-time history or past titles — use get_world_cup_titles."""
    _log_tool("get_current_form", team=team)
    return live_data.current_form(teams.openfootball_name(_resolve_or_raise(team)))


@mcp.tool()
def search_knowledge(query: str) -> list[dict]:
    """Search the football knowledge base (team histories, notable players, World Cup
    records, playing styles) for background passages relevant to a question. Use this for
    historical or background questions — NOT for live fixtures, results, or standings."""
    _log_tool("search_knowledge", query=query)
    return rag.search(query)


if __name__ == "__main__":
    mcp.run()
