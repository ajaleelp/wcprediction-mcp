"""Data-access seam over the openfootball World Cup files in data/worldcup/.

Static public-domain JSON, one file per tournament (1930-2026), downloaded once.
There is no aggregated "winners" file, so we derive each tournament's champion from
its 'Final' match. 1950 had no final — a final round-robin group decided it — so it
is handled as a documented exception.
"""

import json
from pathlib import Path

WC_DIR = Path(__file__).parent / "data" / "worldcup"

# 1950 was decided by a final round-robin group, not a single match; FIFA recognises Uruguay.
WINNERS_WITHOUT_FINAL = {1950: "Uruguay"}

# Successor states: a query for the modern name should include its predecessor's titles.
TEAM_ALIASES = {
    "germany": {"germany", "west germany"},
}


def _winner_of(match: dict) -> str | None:
    """Return the winning team's name from a decided match, or None if undecided.

    The score is nested by resolution: penalties (p) settle extra time (et), which
    settles full time (ft). We read the most decisive level present.
    """
    score = match.get("score", {})
    for level in ("p", "et", "ft"):
        if level in score:
            team_1_goals, team_2_goals = score[level]
            if team_1_goals > team_2_goals:
                return match["team1"]
            if team_2_goals > team_1_goals:
                return match["team2"]
    return None


def world_cup_winners() -> dict[int, str]:
    """Return {year: champion_name} for every tournament on disk that has been decided."""
    winners = {}
    for path in sorted(WC_DIR.glob("*.json")):
        year = int(path.stem)
        matches = json.loads(path.read_text())["matches"]
        final = next((m for m in matches if m.get("round") == "Final"), None)
        champion = _winner_of(final) if final else WINNERS_WITHOUT_FINAL.get(year)
        if champion:
            winners[year] = champion
    return winners


def world_cup_record(team: str) -> dict:
    """Return a team's World Cup title record: {team, titles, years}.

    Case-insensitive, and aware of successor states (e.g. "Germany" includes the
    titles won as "West Germany").
    """
    names = TEAM_ALIASES.get(team.lower(), {team.lower()})
    years = sorted(y for y, champ in world_cup_winners().items() if champ.lower() in names)
    return {"team": team, "titles": len(years), "years": years}
