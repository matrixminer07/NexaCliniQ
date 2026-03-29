import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor


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


def _serialize_scenario(row: dict) -> dict:
    created_at = row.get("created_at")
    return {
        "id": str(row.get("id")),
        "name": row.get("name"),
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
        "inputs": row.get("inputs") or {},
        "outputs": row.get("outputs") or {},
        "tags": row.get("tags") or [],
    }


def init_db():
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id UUID PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    inputs JSONB NOT NULL,
                    outputs JSONB NOT NULL,
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
        conn.commit()


def save_scenario(name: str, inputs: dict, outputs: dict, tags: list | None = None) -> str:
    init_db()
    scenario_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scenarios (id, name, created_at, inputs, outputs, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [scenario_id, name, created_at, Json(inputs or {}), Json(outputs or {}), Json(tags or [])],
            )
        conn.commit()
    return scenario_id


def list_scenarios() -> list:
    init_db()
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS id, name, created_at, inputs, outputs, tags
                FROM scenarios
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
    return [_serialize_scenario(row) for row in rows]


def get_scenario(sid: str) -> Optional[dict]:
    init_db()
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text AS id, name, created_at, inputs, outputs, tags
                FROM scenarios
                WHERE id::text = %s
                LIMIT 1
                """,
                [sid],
            )
            row = cur.fetchone()
    if not row:
        return None
    return _serialize_scenario(row)


def delete_scenario(sid: str):
    init_db()
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM scenarios WHERE id::text = %s", [sid])
        conn.commit()
