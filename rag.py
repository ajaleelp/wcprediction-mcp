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


def answer_with_rag(query, k=5):
    hits = search(query, k)
    context = "\n\n".join(h["text"] for h in hits)

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer the question using ONLY the provided context. "
                    "If the context doesn't contain the answer, say you don't know."
                ),
            },
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
    )
    return {"answer": response.choices[0].message.content, "chunks": hits}


def check_faithfulness(answer, chunks):
    context = "\n\n".join(h["text"] for h in chunks)

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict grader of FAITHFULNESS. You are given an ANSWER and a set of SOURCES. "
                    "Extract the factual claims made BY THE ANSWER ONLY — never treat the SOURCES as claims to grade. "
                    "For each claim in the answer, decide whether it is supported by the SOURCES. "
                    "Treat the SOURCES as the only ground truth; ignore your own knowledge. "
                    "If the ANSWER makes no factual claims — e.g. it says it doesn't know, or refuses — "
                    "it is trivially faithful: return faithful=true with an empty unsupported_claims list. "
                    "Respond as JSON with keys: faithful (boolean), "
                    "unsupported_claims (list of strings, each taken only from the ANSWER), reasoning (string)."
                ),
            },
            { "role": "user", "content": f"<sources>\n{context}\n</sources>\n\n<answer>\n{answer}\n</answer>" }
        ],
        temperature=0,
        response_format={ "type": "json_object" }
    )
    return json.loads(response.choices[0].message.content)

JUDGE_TESTS = [
    {"name": "abstention",
     "answer": "I don't know.",
     "sources": [{"text": "Brazil has won the FIFA World Cup five times."}],
     "expected": True},
    {"name": "grounded",
     "answer": "Brazil has won the World Cup five times.",
     "sources": [{"text": "Brazil has won the FIFA World Cup five times, more than any nation."}],
     "expected": True},
    {"name": "hallucination",
     "answer": "Brazil has won the World Cup seven times.",
     "sources": [{"text": "Brazil has won the FIFA World Cup five times."}],
     "expected": False},
]


def run_judge_tests():
    for case in JUDGE_TESTS:
        verdict = check_faithfulness(case["answer"], case["sources"])
        got = verdict.get("faithful")
        ok = "PASS" if got == case["expected"] else "FAIL"
        print(f"[{ok}] {case['name']}: expected={case['expected']} got={got}")



# if __name__ == "__main__":
#     q = "What was the attendance at the 1950 FIFA World Cup final?"
#     result = answer_with_rag(q)
#     print("ANSWER:\n", result["answer"], "\n")

#     verdict = check_faithfulness(result["answer"], result["chunks"])
#     print("FAITHFUL:", verdict["faithful"])
#     print("UNSUPPORTED:", verdict["unsupported_claims"])
#     print("REASONING:", verdict.get("reasoning", ""))

if __name__ == "__main__":
    run_judge_tests()
