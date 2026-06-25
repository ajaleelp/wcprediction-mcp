"""Runtime retrieval: load the prebuilt embeddings and search by meaning.

The corpus is built offline by build_corpus.py; this module only reads
embeddings.json, so it never re-embeds the corpus.
"""

import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

ROOT = Path(__file__).parent
chunks = json.loads((ROOT / "data" / "embeddings.json").read_text())

# Stack all chunk vectors into one matrix and normalize each row,
# so cosine similarity reduces to a plain dot product.
matrix = np.array([c["embedding"] for c in chunks])
matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def search(query, k=5):
    """Return the k chunks whose meaning is closest to the query."""
    q = np.array(
        client.embeddings.create(model="mistral-embed", inputs=[query]).data[0].embedding
    )
    q = q / np.linalg.norm(q)
    scores = matrix @ q  # cosine similarity vs every chunk at once
    top = np.argsort(scores)[::-1][:k]
    return [
        {"code": chunks[i]["code"], "text": chunks[i]["text"], "score": float(scores[i])}
        for i in top
    ]


if __name__ == "__main__":
    for hit in search("How successful is Brazil in the World Cup?"):
        print(f"[{hit['score']:.3f}] {hit['code']}: {hit['text'][:120]}")
