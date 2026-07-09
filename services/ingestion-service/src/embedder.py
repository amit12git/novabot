"""Embed chunks with fastembed and store them in Qdrant.

Same as 5c-1, plus list_documents() for the /documents endpoint.
QDRANT_URL now matters in two contexts:
  - host script (ingest.py): http://localhost:6333  (default)
  - container (this service): http://qdrant:6333    (set by compose)
"""

import os
import uuid

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension

_embedder = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    providers=["CPUExecutionProvider"],
)

_client = QdrantClient(url=QDRANT_URL)


def _ensure_collection() -> None:
    if not _client.collection_exists(COLLECTION_NAME):
        _client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def _point_id(source_file: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_file}::chunk_{index}"))


def store_chunks(chunks: list[str], source_file: str) -> int:
    if not chunks:
        return 0
    _ensure_collection()

    vectors = list(_embedder.embed(chunks))
    points = [
        PointStruct(
            id=_point_id(source_file, i),
            vector=vector.tolist(),
            payload={"text": chunk, "source": source_file, "chunk_index": i},
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    _client.upsert(collection_name=COLLECTION_NAME, points=points)
    return len(points)


def list_documents() -> list[dict]:
    """Scroll the collection and aggregate chunk counts per source file."""
    _ensure_collection()
    counts: dict[str, int] = {}
    offset = None
    while True:
        points, offset = _client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=["source"],
            with_vectors=False,
        )
        for p in points:
            src = p.payload.get("source", "unknown")
            counts[src] = counts.get(src, 0) + 1
        if offset is None:
            break
    return [
        {"source": src, "chunks": n}
        for src, n in sorted(counts.items())
    ]


def search(query: str, top_k: int = 3) -> list[dict]:
    """Kept for the host-side ask.py test script."""
    query_vector = list(_embedder.embed([query]))[0]
    result = _client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector.tolist(),
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "text": p.payload["text"],
            "source": p.payload["source"],
            "similarity": p.score,
        }
        for p in result.points
    ]
