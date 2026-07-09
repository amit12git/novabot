"""PostgreSQL chat history.

Stores every user question and assistant answer per session,
so conversations survive restarts and can power a chat UI later.
"""

import psycopg2
import psycopg2.extras

import config


def get_conn():
    return psycopg2.connect(config.POSTGRES_DSN)


def init_db() -> None:
    """Create the chat_messages table if it doesn't exist. Called on startup."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT NOT NULL,
                role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content     TEXT NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session
                ON chat_messages (session_id, created_at);
            """
        )


def save_message(session_id: str, role: str, content: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content) "
            "VALUES (%s, %s, %s)",
            (session_id, role, content),
        )


def get_history(session_id: str, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT role, content, created_at FROM chat_messages "
                "WHERE session_id = %s ORDER BY created_at ASC LIMIT %s",
                (session_id, limit),
            )
            rows = cur.fetchall()
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
