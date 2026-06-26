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


# k iterated to 10 after eval runs.
def search(query, k=10):
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


def answer_with_rag(query, k=10):
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
        temperature=0
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


EVAL_QUESTIONS = [
    "How many times has Brazil won the World Cup?",
    "Who won the 1950 World Cup?",
    "What was the attendance at the deciding match of the 1950 World Cup?",
    "How has Germany performed across World Cup history?",
    "Has Canada ever won the World Cup?",
    "Which country hosted and won the 1998 World Cup?",
]


def check_answer_relevancy(question, answer):
    prompt = (
        "You are an evaluator scoring ANSWER RELEVANCY: how well an ANSWER addresses "
        "the QUESTION that was asked.\n\n"
        "Judge ONLY whether the answer is on-topic and actually responds to the question. "
        "Do NOT judge whether the answer is factually correct, and do NOT use any outside "
        "knowledge — correctness is graded separately. An answer can even be wrong but still "
        "relevant if it directly addresses the question.\n\n"
        "Score from 0.0 to 1.0 using this scale:\n"
        "- 1.0  — directly and completely answers the exact question asked.\n"
        "- 0.7-0.9 — answers the question but is partial, hedged, or padded with irrelevant material.\n"
        "- 0.4-0.6 — loosely related: addresses the topic, or answers a different question.\n"
        "- 0.0-0.3 — does not answer at all: declines, says it doesn't know, is empty, or off-topic.\n\n"
        "Respond as JSON with keys: relevancy (number between 0 and 1), reasoning (string, one sentence)."
    )
    messages=[
        { "role": "system", "content": prompt },
        { "role": "user", "content": f"QUESTION: {question}\n\n ANSWER: {answer}" }
    ]
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=messages,
        response_format={ "type": "json_object" },
        temperature=0
    )

    return json.loads(response.choices[0].message.content)


def run_system_eval():
    faithful_count = 0
    relevancy_sum = 0
    for question in EVAL_QUESTIONS:
        response = answer_with_rag(question)

        faithfulness_verdict = check_faithfulness(response["answer"], response["chunks"])
        is_faithful = faithfulness_verdict.get("faithful")

        relevancy_verdict = check_answer_relevancy(question, response["answer"])
        relevancy_sum += relevancy_verdict.get("relevancy")


        if is_faithful:
            faithful_count += 1

        status = "faithful" if is_faithful else "NOT faithful"
        print(f"[{status}] {question}")
        print(f"    -> {response['answer'][:200]}")
        if not is_faithful:
            print(f"    unsupported: {faithfulness_verdict.get('unsupported_claims')}")
    faithfulness_score = faithful_count / len(EVAL_QUESTIONS)
    avg_relevancy = relevancy_sum / len(EVAL_QUESTIONS)

    print(f"\nFaithfulness: {faithfulness_score:.0%} ({faithful_count}/{len(EVAL_QUESTIONS)})")
    print(f"\nRelevancy Score: {avg_relevancy:.0%}")


if __name__ == "__main__":
    run_system_eval()
