"""MAIN PIPELINE — run this to index your documents.

Usage:
    cd services/ingestion-service
    pip install -r requirements.txt
    python src/ingest.py

It scans data/documents/ for .pdf, .txt, and .md files, then:
    load -> chunk -> embed -> store in ChromaDB
"""

from pathlib import Path

from loaders.pdf_loader import load_pdf
from loaders.txt_loader import load_txt
from chunker import chunk_text
from embedder import store_chunks

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"

LOADERS = {
    ".pdf": load_pdf,
    ".txt": load_txt,
    ".md": load_txt,
}


def ingest_all() -> None:
    files = [f for f in DOCS_DIR.iterdir() if f.suffix.lower() in LOADERS]
    if not files:
        print(f"No documents found in {DOCS_DIR}")
        print("Drop a .pdf, .txt, or .md file there and run again.")
        return

    total_chunks = 0
    for file in files:
        print(f"Loading   {file.name} ...")
        text = LOADERS[file.suffix.lower()](file)

        print(f"Chunking  {file.name} ({len(text.split())} words) ...")
        chunks = chunk_text(text, chunk_size=500, overlap=50)

        print(f"Embedding {len(chunks)} chunks (first run downloads the model) ...")
        stored = store_chunks(chunks, source_file=file.name)
        total_chunks += stored
        print(f"Done      {file.name}: {stored} chunks stored\n")

    print(f"Ingestion complete — {total_chunks} chunks across {len(files)} file(s).")
    print("Now test retrieval:  python src/ask.py \"your question here\"")


if __name__ == "__main__":
    ingest_all()
