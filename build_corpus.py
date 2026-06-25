import json
from pathlib import Path

import wikipediaapi

wiki = wikipediaapi.Wikipedia(user_agent="pundit-rag/0.1 (learning project)", language="en")

TEAMS_PATH = Path(__file__).parent / "data" / "teams.json"
teams = json.loads(TEAMS_PATH.read_text())

OUTPUT_PATH = Path(__file__).parent / "data" / "knowledge"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# Teams whose article isn't "<name> national football team":
# men's/women's disambiguation pages, the "soccer" naming (USA/Canada/Australia),
# and the "&" -> "and" mismatch (Bosnia).
OVERRIDES = {
    "USA": "United States men's national soccer team",
    "CAN": "Canada men's national soccer team",
    "AUS": "Australia men's national soccer team",
    "NZL": "New Zealand men's national football team",
    "SWE": "Sweden men's national football team",
    "BIH": "Bosnia and Herzegovina national football team",
}


def is_real_article(page):
    """A usable article exists, is substantial, and isn't a disambiguation stub."""
    return (
        page.exists()
        and len(page.text) > 2000
        and "refer to" not in page.text[:200].lower()
    )


problems = []
for team in teams:
    code = team["code"]
    title = OVERRIDES.get(code, f"{team['full_name']} national football team")
    page = wiki.page(title)
    if is_real_article(page):
        (OUTPUT_PATH / f"{code}.text").write_text(page.text)
    else:
        problems.append(code)

print("problems:", problems)
print("saved:", len(teams) - len(problems), "of", len(teams))
