"""Split document text into overlapping chunks.

Why overlap? If an answer sits at a chunk boundary, overlap ensures at
least one chunk contains the full context. Start with 500-word chunks
and 50-word overlap, then experiment — chunk size is one of the biggest
levers in RAG quality.
"""


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into word-based chunks with overlap.

    Args:
        text: Full document text.
        chunk_size: Number of words per chunk.
        overlap: Number of words shared between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if len(chunk_words) < 20 and chunks:
            # Tiny tail chunk — merge into the previous one instead
            chunks[-1] = chunks[-1] + " " + " ".join(chunk_words)
            break
        chunks.append(" ".join(chunk_words))
    return chunks


if __name__ == "__main__":
    sample = "word " * 1200
    result = chunk_text(sample)
    print(f"{len(result)} chunks, first chunk has {len(result[0].split())} words")
