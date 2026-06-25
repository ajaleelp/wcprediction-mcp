"""Offline build: fetch team articles -> chunk -> embed -> save embeddings.json.

Run this only when the corpus changes. Runtime search lives in rag.py.
"""

import json
import os
from pathlib import Path

import wikipediaapi
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
wiki = wikipediaapi.Wikipedia(user_agent="pundit-rag/0.1 (learning project)", language="en")

ROOT = Path(__file__).parent
TEAMS_PATH = ROOT / "data" / "teams.json"
KNOWLEDGE = ROOT / "data" / "knowledge"
EMBEDDINGS_PATH = ROOT / "data" / "embeddings.json"

# Teams whose Wikipedia article isn't "<name> national football team":
# men's/women's disambiguation, "soccer" naming (USA/Canada/Australia), and "&" -> "and".
OVERRIDES = {
    "USA": "United States men's national soccer team",
    "CAN": "Canada men's national soccer team",
    "AUS": "Australia men's national soccer team",
    "NZL": "New Zealand men's national football team",
    "SWE": "Sweden men's national football team",
    "BIH": "Bosnia and Herzegovina national football team",
}


def is_real_article(page):
    """Exists, is substantial, and isn't a disambiguation stub."""
    return (
        page.exists()
        and len(page.text) > 2000
        and "refer to" not in page.text[:200].lower()
    )


def chunk_text(text, size=800, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def fetch_articles():
    KNOWLEDGE.mkdir(parents=True, exist_ok=True)
    teams = json.loads(TEAMS_PATH.read_text())
    problems = []
    for team in teams:
        code = team["code"]
        title = OVERRIDES.get(code, f"{team['full_name']} national football team")
        page = wiki.page(title)
        if is_real_article(page):
            (KNOWLEDGE / f"{code}.text").write_text(page.text)
        else:
            problems.append(code)
    print("fetch problems:", problems)


def build_chunks():
    all_chunks = []
    for file in KNOWLEDGE.glob("*.text"):
        code = file.stem
        for chunk in chunk_text(file.read_text()):
            all_chunks.append({"code": code, "text": chunk})
    return all_chunks


def embed_chunks(all_chunks):
    texts = [c["text"] for c in all_chunks]
    embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(model="mistral-embed", inputs=batch)
        embeddings.extend(d.embedding for d in response.data)
        print(f"embedded {i + len(batch)} / {len(texts)}")
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb
    return all_chunks


if __name__ == "__main__":
    fetch_articles()
    chunks = embed_chunks(build_chunks())
    EMBEDDINGS_PATH.write_text(json.dumps(chunks))
    print("saved", len(chunks), "embedded chunks to", EMBEDDINGS_PATH.name)
