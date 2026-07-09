"""Query Service API.

Run:
    cd services/query-service
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000 --app-dir src

Endpoints:
    GET  /health                  -> service status
    POST /chat                    -> ask a question, get grounded answer
    GET  /history/{session_id}    -> full conversation history
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import db
import rag
import time

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("query-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()  # create tables on startup
    yield


app = FastAPI(title="RAG Query Service", version="0.1.0", lifespan=lifespan)


# ---------- Schemas ----------

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", max_length=100)


class SourceInfo(BaseModel):
    source: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    session_id: str
    cached: bool = False
    elapsed_ms: int = 0


# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "service": "query-service"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        db.save_message(request.session_id, "user", request.question)

        started = time.perf_counter()
        result = rag.answer_question(request.question)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        logger.info(                                    # ← HERE
            "chat session=%s cached=%s elapsed_ms=%d question=%r",
            request.session_id,
            result.get("cached", False),
            elapsed_ms,
            request.question[:60],
        )
        db.save_message(request.session_id, "assistant", result["answer"])
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            session_id=request.session_id,
            cached=result.get("cached", False),
            elapsed_ms=elapsed_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/history/{session_id}")
def history(session_id: str):
    return {"session_id": session_id, "messages": db.get_history(session_id)}
