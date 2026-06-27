# wcprediction-mcp

> A project for exploring Mistral's applied-AI toolchain end to end, built around a real use case:
> an AI companion for a **World Cup 2026 prediction game**. It deliberately touches every layer —
> an **MCP tool server** over the game's data, **two agent implementations** (hand-rolled and
> SDK-native), a **RAG knowledge base** embedded with `mistral-embed`, and a **faithfulness eval**.

The aim is breadth: one project that walks through the Model Context Protocol (MCP), the Agents API,
embeddings, retrieval-augmented generation, and evaluation — the pieces of Mistral's stack and how
they fit together. Built in the open, commit by commit; AI-assisted, with each layer added once its
role was clear.

## The journey

A checklist of the build, layer by layer. Each step explores another part of Mistral's stack, and
earns its place by improving a measurable outcome — not by being added for its own sake. The running
judgment call throughout: *which tool fits which job* (live data → DB tools; background knowledge →
RAG; the scoreline → the user's call, never the assistant's).

**Foundation — tools, agents, retrieval**
- [x] **MCP tool server** — `list_teams`, `get_team`, `get_matches_for_team` over the game's Postgres, plus `search_knowledge`
- [x] **Data-access seam** — a repository over Postgres so the data source stays swappable
- [x] **Agent, hand-rolled** — the chat-completion tool-call loop written from scratch
- [x] **Agent, SDK-native** — the same loop via Mistral's Agents API + MCP over stdio
- [x] **Embeddings + corpus** — Wikipedia articles chunked and embedded with `mistral-embed` (offline build)
- [x] **RAG retrieval** — cosine-similarity semantic search over the embeddings

**Quality — making the answers trustworthy**
- [x] **Faithfulness + relevancy eval** — an LLM-as-judge that checks answers are grounded in the retrieved chunks (faithfulness) *and* actually address the question (relevancy), with a judge-validation set and per-question diagnostics. The measuring stick for everything below.
- [x] **Advanced RAG** — eval-driven retrieval-depth tuning (a measured faithfulness gain); reranking / HyDE / smarter chunking deferred until the eval shows they're needed

**Usefulness — real football data**
- [x] **Football-world data (openfootball)** — all-time World Cup titles and current-tournament form, with a schedule-gated live cache (refresh only around matches, not on a blind timer); routed via the agent with observable tool calls and a forgiving team resolver (code *or* name). Standings still to add.
- [x] **Head-to-head** — every World Cup meeting between two teams (year, round, score, winner) and the win/draw tally, derived from the openfootball data
- [x] **Live news & injuries** — Mistral's built-in web search on the native agent, so the read reflects current news/injuries, not just historical data
- [ ] **Proprietary game tools** — "where am I going wrong", league prediction trends (per-user scoped, honoring the game's reveal-after-lock rule)

**Going deeper on the model**
- [ ] **Fine-tuning** *(in progress)* — a QLoRA fine-tune for the assistant's core behavior: act as a grounded match-prep analyst (form, stakes, likely approach) that never fabricates a scoreline or winner, A/B'd against base+prompt on the eval
- [ ] **Inference & serving** — quantization and cost/latency trade-offs for running it cheaply at the game's scale

**Production**
- [ ] **Vector DB** — swap the in-memory numpy retrieval for `pgvector` in the existing Postgres
- [ ] **Chat widget** — serve the assistant inside the game itself

## The idea

A companion assistant for a **World Cup 2026 prediction game** (a separate web app where players
predict match outcomes). It briefs the player from three kinds of grounded source:

- **Live game data** (fixtures, results, a team's form) — via MCP tools over the game's database and openfootball.
- **Football-world knowledge** (team histories, World Cup records, players) — via **RAG** over Wikipedia articles embedded with `mistral-embed`.
- **Live news & injuries** — via Mistral's built-in **web search**, so the read reflects what's happening right now.

It is a **match-prep analyst, not a predictor**. It arms the player's pick with grounded analysis —
recent form, what's at stake, the latest news and injuries, and a read on how each team is likely to
play — then concludes with a **hedged lean**: the likely favourite and whether the game looks high-
or low-scoring. It stops there: it **never invents the exact scoreline** (that precise call is the
player's game entry) and never fabricates a stat. A *calibrated* scoreline is a statistics-model
job, not an LLM's.

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
| `agent.py` | A **hand-rolled** agent: the chat-completion tool-call loop written from scratch — the reference implementation that shows what the SDK does under the hood. |
| `agent_native.py` | The same idea via Mistral's **native Agents API + MCP** over stdio — the SDK runs the loop. |

Building both agents was deliberate: the hand-rolled loop makes explicit *what* the native Agents API
abstracts away — and clarifies when each is the right call.

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

## License

MIT — see [`LICENSE`](LICENSE).
