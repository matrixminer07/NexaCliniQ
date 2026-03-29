import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pharma:password@localhost:5432/pharmanexus")


def _normalized_database_url() -> str:
    if DATABASE_URL.startswith("postgres://"):
        return "postgresql://" + DATABASE_URL[len("postgres://") :]
    return DATABASE_URL


@contextmanager
def _get_conn():
    conn = psycopg2.connect(_normalized_database_url())
    try:
        yield conn
    finally:
        conn.close()


def _serialize_annotation(row: dict) -> dict:
    created_at = row.get("created_at")
    return {
        "id": row.get("id"),
        "context": row.get("context"),
        "author": row.get("author"),
        "text": row.get("text"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
        "resolved": bool(row.get("resolved")),
    }


def init_db():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS annotations (
                    id TEXT PRIMARY KEY,
                    context TEXT,
                    author TEXT,
                    text TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    resolved BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
        conn.commit()


def add_annotation(context: str, author: str, text: str) -> dict:
    init_db()
    aid = str(uuid.uuid4())[:8]
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO annotations (id, context, author, text, created_at, resolved)
                VALUES (%s, %s, %s, %s, NOW(), FALSE)
                RETURNING id, context, author, text, created_at, resolved
                """,
                [aid, context, author, text],
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return {
            "id": aid,
            "context": context,
            "author": author,
            "text": text,
            "created_at": datetime.utcnow().isoformat(),
            "resolved": False,
        }
    return _serialize_annotation(row)


def get_annotations(context: Optional[str] = None) -> list:
    init_db()
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if context:
                cur.execute(
                    """
                    SELECT id, context, author, text, created_at, resolved
                    FROM annotations
                    WHERE context = %s
                    ORDER BY created_at DESC
                    """,
                    [context],
                )
            else:
                cur.execute(
                    """
                    SELECT id, context, author, text, created_at, resolved
                    FROM annotations
                    ORDER BY created_at DESC
                    """
                )
            rows = cur.fetchall()
    return [_serialize_annotation(row) for row in rows]


def resolve_annotation(aid: str):
    init_db()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE annotations SET resolved = TRUE WHERE id = %s", [aid])
        conn.commit()
