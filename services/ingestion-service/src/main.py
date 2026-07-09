"""Ingestion Service API.

Accepts document uploads over HTTP, runs the indexing pipeline
(load -> chunk -> embed -> store in Qdrant), and reports status.

Endpoints:
    GET  /health              -> service status
    POST /upload              -> multipart file upload (.pdf, .txt, .md)
    GET  /documents           -> list indexed documents with chunk counts
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from loaders.pdf_loader import load_pdf
from loaders.txt_loader import load_txt
from chunker import chunk_text
import embedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingestion-service")

app = FastAPI(title="RAG Ingestion Service", version="0.1.0")

LOADERS = {
    ".pdf": load_pdf,
    ".txt": load_txt,
    ".md": load_txt,
}

MAX_FILE_MB = 20


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion-service"}


@app.post("/upload")
async def upload(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in LOADERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: {list(LOADERS)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_MB}MB limit")

    # Loaders read from a path, so write the upload to a temp file
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(contents)
        tmp.flush()
        try:
            text = LOADERS[suffix](tmp.name)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}") from exc

    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the file")

    chunks = chunk_text(text, chunk_size=500, overlap=50)
    stored = embedder.store_chunks(chunks, source_file=file.filename)

    logger.info("upload file=%s words=%d chunks=%d", file.filename, len(text.split()), stored)
    return {
        "filename": file.filename,
        "words": len(text.split()),
        "chunks_stored": stored,
        "status": "indexed",
    }


@app.get("/documents")
def documents():
    return {"documents": embedder.list_documents()}
