"""Schedule-gated live cache over the openfootball 2026 World Cup file.

openfootball auto-regenerates the tournament JSON every few hours, so a result
lands within hours of a match ending. Rather than poll on a blind TTL or trust a
frozen download, we refresh ONLY when a match is in its active window — from
kickoff to kickoff + ACTIVE_WINDOW — and then at most once per POLL_INTERVAL.
When no match is active nothing has changed, so we serve the cache untouched
(zero fetches). A daily backstop catches rare schedule corrections.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen

WC_2026_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
LOCAL_FALLBACK = Path(__file__).parent / "data" / "worldcup" / "2026.json"

ACTIVE_WINDOW = timedelta(hours=6)      # a result can publish up to ~6h after kickoff
POLL_INTERVAL = timedelta(minutes=30)   # within an active window, refresh at most this often
BACKSTOP = timedelta(hours=24)          # refresh at least daily, for schedule corrections

_cache = {"data": None, "fetched_at": None}


def _kickoff(match):
    """Best-effort UTC kickoff for a fixture, or None if unparseable.

    openfootball stores date 'YYYY-MM-DD' and time 'HH:MM'. We assume UTC; the 6h
    active window comfortably absorbs any venue/timezone offset.
    """
    date = match.get("date")
    if not date:
        return None
    clock = match.get("time") or "12:00"
    try:
        return datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_active(now):
    """True if any fixture is currently in its [kickoff, kickoff + ACTIVE_WINDOW] window."""
    data = _cache["data"]
    if not data:
        return False
    return any(
        (k := _kickoff(m)) and k <= now <= k + ACTIVE_WINDOW
        for m in data["matches"]
    )


def _should_refresh(now):
    if _cache["data"] is None:
        return True                                   # cold start
    age = now - _cache["fetched_at"]
    if age >= BACKSTOP:
        return True                                   # daily safety net
    return _is_active(now) and age >= POLL_INTERVAL    # only poll while a match is live


def _refresh(now):
    try:
        with urlopen(WC_2026_URL, timeout=10) as resp:
            _cache["data"] = json.loads(resp.read())
    except Exception as exc:                           # network hiccup: don't crash a query
        print(f"[live_data] refresh failed ({exc}); using fallback")
        if _cache["data"] is None:                     # cold start, no network → local snapshot
            _cache["data"] = json.loads(LOCAL_FALLBACK.read_text())
    _cache["fetched_at"] = now


def _get_data():
    now = datetime.now(timezone.utc)
    if _should_refresh(now):
        _refresh(now)
    return _cache["data"]


def current_form(team):
    """Return a team's WC2026 form so far: played count, W/D/L record, goals, and
    the per-match list. Counts only matches with a full-time result; case-insensitive.
    """
    data = _get_data()
    name = team.lower()
    matches = []
    wins = draws = losses = goals_for = goals_against = 0
    for match in data["matches"]:
        ft = match.get("score", {}).get("ft")
        if not ft:
            continue
        team1, team2 = match.get("team1", ""), match.get("team2", "")
        if name == team1.lower():
            scored, conceded, opponent = ft[0], ft[1], team2
        elif name == team2.lower():
            scored, conceded, opponent = ft[1], ft[0], team1
        else:
            continue

        if scored > conceded:
            outcome = "W"
            wins += 1
        elif scored < conceded:
            outcome = "L"
            losses += 1
        else:
            outcome = "D"
            draws += 1
        goals_for += scored
        goals_against += conceded
        matches.append({
            "round": match.get("round"),
            "opponent": opponent,
            "score": f"{scored}-{conceded}",
            "result": outcome,
        })

    return {
        "team": team,
        "played": len(matches),
        "record": {"w": wins, "d": draws, "l": losses},
        "goals_for": goals_for,
        "goals_against": goals_against,
        "matches": matches,
    }
