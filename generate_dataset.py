import os
import json
from pathlib import Path

from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()
client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

ROOT = Path(__file__).parent
SEED = json.loads((ROOT / "data" / "finetune" / "seed.json").read_text())
SYSTEM, EXAMPLES = SEED["system"], SEED["examples"]
OUT_PATH = ROOT / "data" / "finetune" / "analyst.jsonl"

N = 15

PROMPT = (
    "You are generating a corpus of N fine-tuning examples for an LLM (N is given below).\n"
    "SYSTEM is the assistant's expected behaviour.\n"
    "EXAMPLES show that behaviour across cases; each example's _class is a critical objective.\n"
    "Generate N NEW examples, evenly distributed across the classes, with varied teams, phrasings, "
    "and realistic-but-varied form / head-to-head / style / news / stakes.\n"
    "Follow the behaviour exactly: recency-weighted lean, cite only relevant sources, never an exact scoreline.\n"
    "Output valid JSON: a single \"examples\" key holding an array of {\"user\": ..., \"assistant\": ...} objects.\n"
)

response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"N: {N}\nSYSTEM: {SYSTEM}\nEXAMPLES: {json.dumps(EXAMPLES)}"},
    ],
    response_format={"type": "json_object"},
    temperature=0.7,
)

generated = [
    g for g in json.loads(response.choices[0].message.content)["examples"]
    if g.get("user") and g.get("assistant")
]

# Combine the hand-written seed (gold standard) with the generated examples.
pairs = [{"user": e["user"], "assistant": e["assistant"]} for e in EXAMPLES] + generated

rows = [
    {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": p["user"]},
        {"role": "assistant", "content": p["assistant"]},
    ]}
    for p in pairs
]

with open(OUT_PATH, "w") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

print(f"wrote {len(rows)} rows to {OUT_PATH.name}  ({len(EXAMPLES)} seed + {len(generated)} generated)\n")
if generated:
    g = generated[0]
    print("--- sample generated ---")
    print("USER:", g["user"][:280], "...\n")
    print("ASSISTANT:", g["assistant"][:460], "...")
