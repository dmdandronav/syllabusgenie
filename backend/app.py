"""
AI Web App Template — Flask backend
------------------------------------
A minimal but extensible backend for "chat with AI" style hackathon projects:
mental health check-ins, document Q&A, study assistants, accessibility helpers,
financial analysis chatbots, etc. (See README for example pivots.)

What it gives you out of the box:
  - POST /api/chat        -> talk to an LLM, with conversation history
  - POST /api/documents    -> drop .txt/.md files into ./data and they become
                              searchable context (lightweight RAG)
  - GET  /api/health       -> sanity check

Works with OpenAI OR Groq (or any OpenAI-compatible endpoint) — just change
OPENAI_BASE_URL in .env. Groq is great for hackathons because it's free-tier
friendly and very fast (used by the Hack the North 2025 winning "DUM-E" project
for low-latency multimodal inference).
"""

import os
import json
import math
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
CORS(app)  # allow the Vite dev server (localhost:5173) to call this API

# ---------------------------------------------------------------------------
# Client setup — works with OpenAI, Groq, or any OpenAI-compatible API
# ---------------------------------------------------------------------------
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL") or None,  # e.g. https://api.groq.com/openai/v1
)
MODEL = os.environ.get("MODEL_NAME", "gpt-4o-mini")
EMBED_MODEL = os.environ.get("EMBED_MODEL_NAME", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Customize this for your hackathon prompt — this is the personality/role
# of your assistant. See README for ready-made examples.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful, encouraging assistant built for a hackathon project. "
    "Keep answers concise and actionable.",
)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
INDEX_PATH = DATA_DIR / "_embeddings.json"


# ---------------------------------------------------------------------------
# Lightweight RAG — chunk local docs, embed them, retrieve by cosine similarity
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def build_index():
    """Re-embeds every .txt/.md file in ./data and saves to _embeddings.json."""
    records = []
    for path in DATA_DIR.glob("*.*"):
        if path.suffix.lower() not in (".txt", ".md"):
            continue
        text = path.read_text(errors="ignore")
        for chunk in chunk_text(text):
            records.append({"source": path.name, "text": chunk})

    if not records:
        INDEX_PATH.write_text(json.dumps([]))
        return []

    resp = client.embeddings.create(model=EMBED_MODEL, input=[r["text"] for r in records])
    for r, e in zip(records, resp.data):
        r["embedding"] = e.embedding

    INDEX_PATH.write_text(json.dumps(records))
    return records


def load_index():
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text())
    return []


def retrieve(query: str, top_k: int = 3):
    """Return the top_k most relevant chunks for `query`. Empty list if no docs."""
    records = load_index()
    if not records:
        return []
    q_emb = client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
    scored = sorted(records, key=lambda r: cosine(q_emb, r["embedding"]), reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "model": MODEL})


@app.route("/api/documents", methods=["POST"])
def add_document():
    """Upload a text/markdown file to add it to the RAG knowledge base.

    Send as multipart/form-data with field name 'file'.
    """
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    f = request.files["file"]
    save_path = DATA_DIR / f.filename
    f.save(save_path)

    records = build_index()
    return jsonify({"status": "indexed", "chunks": len(records)})


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Body: { "messages": [{"role": "user"|"assistant", "content": "..."}, ...] }
    Returns: { "reply": "...", "sources": [...] }
    """
    body = request.get_json(force=True)
    messages = body.get("messages", [])
    if not messages:
        return jsonify({"error": "messages required"}), 400

    last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    # Pull in relevant context from uploaded docs, if any exist.
    context_chunks = retrieve(last_user_msg)
    sources = sorted({c["source"] for c in context_chunks})

    chat_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context_chunks:
        context_text = "\n\n---\n\n".join(c["text"] for c in context_chunks)
        chat_messages.append({
            "role": "system",
            "content": f"Relevant context from uploaded documents:\n\n{context_text}",
        })
    chat_messages.extend(messages)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        temperature=0.7,
    )
    reply = completion.choices[0].message.content

    return jsonify({"reply": reply, "sources": sources})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
