"""Team identity resolver.

Accepts a code, full name, or short name (case-insensitive) and returns the canonical
team record from data/teams.json, or None if unrecognised. Used at the tool boundary so
every team-keyed tool accepts either 'MEX' or 'Mexico' — the agent can't mis-pass an
identifier format, and an unknown identifier fails loudly instead of returning empty.

openfootball spells a few teams differently from the game seed, so openfootball_name()
maps a resolved team to the name openfootball uses, and those spellings also resolve.
"""

import json
from pathlib import Path

TEAMS_PATH = Path(__file__).parent / "data" / "teams.json"
ALL = json.loads(TEAMS_PATH.read_text())

# Seed full_name -> the name openfootball uses for the same team.
_OPENFOOTBALL_NAME = {
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Türkiye": "Turkey",
}

# Index every team by each of its identifiers (and openfootball's spelling), lowercased.
_BY_KEY = {}
for _team in ALL:
    for _key in (_team["code"], _team["full_name"], _team["short_name"]):
        if _key:
            _BY_KEY[_key.lower()] = _team
    _alt = _OPENFOOTBALL_NAME.get(_team["full_name"])
    if _alt:
        _BY_KEY[_alt.lower()] = _team


def resolve(identifier):
    """Return the team dict matching a code / full name / short name, or None."""
    if not identifier:
        return None
    return _BY_KEY.get(identifier.strip().lower())


def openfootball_name(team):
    """The name openfootball uses for a resolved team (differs from the seed for a few)."""
    return _OPENFOOTBALL_NAME.get(team["full_name"], team["full_name"])
