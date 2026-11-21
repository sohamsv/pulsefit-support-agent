"""RAG for Pulse: chunk the help docs, embed with Gemini, store in Chroma, search top 3."""
import re
import shutil
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DOCS_PATH = ROOT / "data" / "pulsefit_help.txt"
INDEX_DIR = ROOT / "index"
COLLECTION = "pulsefit_help"
EMBED_MODEL = "gemini-embedding-001"

_client = None


def _genai():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def load_chunks(path: Path = DOCS_PATH) -> list[dict]:
    """One chunk per FAQ ('Q:' + its answer) and one per 'Policy:' section."""
    chunks = []
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("Q:"):
            current = {"source": "FAQ: " + line[2:].strip(), "lines": [line]}
            chunks.append(current)
        elif line.startswith("Policy:"):
            current = {"source": line[len("Policy:"):].strip(), "lines": [line]}
            chunks.append(current)
        elif line in ("Policies", "Frequently asked questions"):
            current = None
        elif line and current is not None:
            current["lines"].append(line)
    return [{"source": c["source"], "text": "\n".join(c["lines"])} for c in chunks]


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    for attempt in range(5):
        try:
            res = _genai().models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            return [e.values for e in res.embeddings]
        except Exception as e:  # 429 quota: wait and retry
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                time.sleep(15 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Embedding quota busy (429). Wait a minute and run build_index.py again.")


def build_index() -> int:
    """Delete and rebuild the Chroma index. Returns the number of chunks."""
    if INDEX_DIR.exists():
        shutil.rmtree(INDEX_DIR)
    chunks = load_chunks()
    embeddings = _embed([c["text"] for c in chunks], "RETRIEVAL_DOCUMENT")  # may fail: do it before touching disk
    db = chromadb.PersistentClient(path=str(INDEX_DIR))
    col = db.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[f"chunk-{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"]} for c in chunks],
        embeddings=embeddings,
    )
    return len(chunks)


def ensure_index():
    if not INDEX_DIR.exists():
        build_index()


def top_chunks(question: str, k: int = 3) -> list[dict]:
    ensure_index()
    col = chromadb.PersistentClient(path=str(INDEX_DIR)).get_collection(COLLECTION)
    q = _embed([question], "RETRIEVAL_QUERY")
    res = col.query(query_embeddings=q, n_results=k)
    return [
        {"source": m["source"], "text": d}
        for d, m in zip(res["documents"][0], res["metadatas"][0])
    ]


def search_help_docs(question: str) -> dict:
    """Search PulseFit's help docs and return the 3 best matching chunks.

    Args:
        question: the customer's question, in plain words.

    Returns:
        A dict with 'results': a list of {source, text} chunks to answer from.
    """
    return {"results": top_chunks(question, 3)}
