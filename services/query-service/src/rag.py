"""RAG core: Retrieve -> Augment -> Generate. Now backed by Qdrant.

The retrieval section is the only part that changed from the Chroma
version: we embed the question explicitly (fastembed) and search Qdrant
over HTTP. Augment and Generate are untouched.
"""

from fastembed import TextEmbedding # type: ignore
from qdrant_client import QdrantClient # type: ignore
from llm import generate

import cache
import config

# ---------- RETRIEVE ----------

_embedder = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    providers=["CPUExecutionProvider"],
)
_client = QdrantClient(url=config.QDRANT_URL)


def retrieve(question: str) -> list[dict]:
    query_vector = list(_embedder.embed([question]))[0]
    result = _client.query_points(
        collection_name=config.COLLECTION_NAME,
        query=query_vector.tolist(),
        limit=config.TOP_K,
        with_payload=True,
    )
    # Qdrant score IS cosine similarity (higher = better)
    return [
        {
            "text": p.payload["text"],
            "source": p.payload["source"],
            "similarity": p.score,
        }
        for p in result.points
        if p.score >= config.MIN_SIMILARITY
    ]


# ---------- AUGMENT ----------

PROMPT_TEMPLATE = """You are a helpful assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't have that information in the documents."

Context:
{context}

Question: {question}

Answer:"""


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Source {i}: {c['source']}]\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)



# ---------- FULL PIPELINE ----------

def answer_question(question: str) -> dict:
    cached = cache.get_cached(question)
    if cached:
        cached["cached"] = True
        return cached

    chunks = retrieve(question)
    if not chunks:
        return {
            "answer": "I don't have relevant information in the documents.",
            "sources": [],
            "cached": False,
        }

    prompt = build_prompt(question, chunks)
    answer = generate(prompt)
    result = {
        "answer": answer,
        "sources": [
            {"source": c["source"], "similarity": round(c["similarity"], 3)}
            for c in chunks
        ],
        "cached": False,
    }
    cache.set_cached(question, result)
    return result
