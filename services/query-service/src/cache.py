"""Exact-match answer cache backed by Redis.

Key   = sha256 of the normalized question
Value = the full answer JSON
TTL   = 1 hour (stale answers expire; re-ingest also outlives them)
"""

import hashlib
import json
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TTL_SECONDS = 3600

_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _key(question: str) -> str:
    normalized = " ".join(question.lower().split())
    return "answer:" + hashlib.sha256(normalized.encode()).hexdigest()


def get_cached(question: str) -> dict | None:
    try:
        raw = _client.get(_key(question))
        return json.loads(raw) if raw else None
    except redis.RedisError:
        return None  # cache failure must never break the request


def set_cached(question: str, result: dict) -> None:
    try:
        _client.setex(_key(question), TTL_SECONDS, json.dumps(result))
    except redis.RedisError:
        pass
