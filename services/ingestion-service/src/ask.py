"""Test retrieval — ask a question against your indexed documents.

Usage:
    python src/ask.py "What is this document about?"

This is retrieval ONLY (no LLM yet). If the chunks coming back are
relevant to your question, Phase 1 is a success and you're ready for
Phase 2 (sending these chunks to an LLM to generate an answer).
"""

import sys

from embedder import search
from generator import build_prompt, generate


def main() -> None:
    print("Retrieving relevant chunks ...")
    if len(sys.argv) < 2:
        print('Usage: python src/ask.py "your question"')
        return

    question = sys.argv[1]
    print(f"\nQuestion: {question}\n" + "=" * 60)

    hits = search(question, top_k=3)
    if not hits:
        print("No results. Did you run ingest.py first?")
        return
    MIN_SIMILARITY = 0.10   # tune this — start around 0.2–0.3

    chunks = search(question, top_k=3)
    chunks = [c for c in chunks if c["similarity"] >= MIN_SIMILARITY]
    if not chunks:
        print("No relevant information found in the documents.")
        return
    # ---- A: Augment ----
    prompt = build_prompt(question, chunks)

    # ---- G: Generate ----
    print(f"Generating answer with {len(chunks)} chunks of context ...\n")
    answer = generate(prompt)

    print("=" * 60)
    print(f"Question: {question}\n")
    print(f"Answer:   {answer}\n")
    print("-" * 60)
    print("Sources used:")
    for chunk in chunks:
        similarity = chunk["similarity"]
        print(f"  - {chunk['source']} (similarity: {similarity:.3f})")


if __name__ == "__main__":
    main()
