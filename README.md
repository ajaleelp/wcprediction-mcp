# wcprediction-mcp

> A hands-on learning project: an AI assistant for a **World Cup 2026 prediction game**, built on
> Mistral's stack — an **MCP tool server** over the game's data, **two agent implementations**, and a
> **RAG knowledge base** over football articles embedded with `mistral-embed`.

**This is a personal, recent, build-in-the-open learning project** — I built it to get genuinely
hands-on with the modern applied-AI stack: the Model Context Protocol (MCP), Mistral's models and
Agents API, embeddings, and retrieval-augmented generation. It's AI-assisted, but built to
*understand every piece*, not just run it. Expect rough edges — the commit history is the
step-by-step build.

## The idea

A companion assistant for a **World Cup 2026 prediction game** (a separate web app where players
predict match outcomes). It answers two kinds of question:

- **Live game data** (fixtures, results, a team's matches) — via MCP tools backed by the game's
  PostgreSQL database.
- **Football-world knowledge** (team histories, World Cup records, players) — via **RAG** over
  Wikipedia articles, embedded with `mistral-embed`.

It deliberately **researches; it does not predict** — a calibrated score predictor is a
statistics-model job, not an LLM one, so the assistant sticks to grounded facts.

## Architecture

```
            ┌──────────────── Agent (Mistral) ─────────────────┐
  question →│  decides which tools to call, runs the loop       │
            └───────┬───────────────────────────┬───────────────┘
                    │ MCP                         │ MCP
            ┌───────▼─────────┐          ┌────────▼───────────────┐
            │ DB tools         │          │ search_knowledge (RAG) │
            │ list_teams,      │          │ cosine search over     │
            │ get_team,        │          │ mistral-embed vectors  │
            │ get_matches...   │          │ of Wikipedia articles  │
            └───────┬─────────┘          └────────┬───────────────┘
                    │                             │
            PostgreSQL (game data)        embeddings.json (built offline)
```

## Components

| File | What it is |
|------|------------|
| `server.py` | The **MCP server** — exposes `list_teams`, `get_team`, `get_matches_for_team` (over Postgres) and `search_knowledge` (RAG). |
| `game_data.py` | A data-access **seam** (repository) over the game's Postgres — keeps SQL out of the tools so the data source stays swappable. |
| `build_corpus.py` | Offline build: fetch team articles from Wikipedia → chunk → embed with `mistral-embed` → save `embeddings.json`. |
| `rag.py` | Runtime **retrieval** — loads the embeddings and does cosine-similarity search by meaning. |
| `agent.py` | A **hand-rolled** agent: the chat-completion tool-call loop written from scratch (to understand it). |
| `agent_native.py` | The same idea via Mistral's **native Agents API + MCP** over stdio — the SDK runs the loop. |

Building both agents was deliberate: the hand-rolled loop makes clear *what* the native Agents API
does for you under the hood.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "MISTRAL_API_KEY=your-key" > .env        # from console.mistral.ai
```

The DB-backed tools expect a local PostgreSQL database (`wcprediction_development`) belonging to the
prediction game — **not included here**. The embedding/RAG pieces run standalone with just a Mistral
API key.

## Testing each piece

```bash
# 1. Build the knowledge base (fetches Wikipedia + embeds; needs the Mistral key).
#    Generates data/embeddings.json, which the RAG pieces below load.
python build_corpus.py

# 2. RAG retrieval — semantic search over the corpus.
python rag.py                  # runs a sample query, prints the closest chunks

# 3. The MCP server — inspect/call the tools in a browser.
mcp dev server.py              # opens the MCP Inspector

# 4. The agents — ask a question.
#    (DB-backed tools need the game's Postgres; search_knowledge works without it.)
python agent.py
python agent_native.py "How did Brazil perform in past World Cups?"
```

## What this exercises

MCP server design · tool / function calling · agent orchestration (hand-rolled **and** SDK-native) ·
embeddings & semantic retrieval · RAG grounding · a clean data-access seam · and the judgment of
*which tool fits which job* (live data → DB tools; background → RAG; prediction → neither).

## Scope / future work

- **Faithfulness eval** (in progress) — an LLM-as-judge that verifies answers are grounded in the
  retrieved chunks rather than the model's own (possibly stale) knowledge.
- **Advanced RAG** — reranking, query rewriting / HyDE, smarter chunking; measure the
  retrieval-quality delta each step.
- **Live football data tools** — head-to-head, recent form, standings via a football API, with a
  caching layer ("fetch once, serve many") to stay within free rate limits.
- **Proprietary game tools** — "where am I going wrong", league prediction trends (per-user scoped,
  honoring the game's reveal-after-lock rule).
- **Production** — swap the in-memory numpy retrieval for a vector DB (e.g. `pgvector` in the
  existing Postgres); serve the assistant via a chat widget inside the game.

## License

MIT — see [`LICENSE`](LICENSE).
