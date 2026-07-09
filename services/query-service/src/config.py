"""Configuration — reads environment variables with sensible local defaults."""

import os

# Qdrant vector database (server, not embedded files)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.10"))
TOP_K = int(os.getenv("TOP_K", "3"))

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://raguser:ragpass@localhost:5432/ragdb",
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
