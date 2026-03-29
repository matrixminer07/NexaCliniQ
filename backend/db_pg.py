import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pharma:password@localhost:5432/pharmanexus")


def _normalized_database_url() -> str:
    if DATABASE_URL.startswith("postgres://"):
        return "postgresql://" + DATABASE_URL[len("postgres://") :]
    return DATABASE_URL


@contextmanager
def get_conn():
    conn = psycopg2.connect(_normalized_database_url())
    try:
        yield conn
    finally:
        conn.close()


def init_db_schema() -> None:
    statements = [
        "CREATE EXTENSION IF NOT EXISTS pgcrypto",
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT,
            google_id TEXT,
            role TEXT NOT NULL DEFAULT 'researcher',
            mfa_secret TEXT,
            mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            status INTEGER NOT NULL,
            request_id TEXT,
            request_body TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            input_params JSONB NOT NULL,
            probability DOUBLE PRECISION NOT NULL,
            verdict TEXT NOT NULL,
            warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            notes TEXT NOT NULL DEFAULT '',
            compound_name TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_predictions_verdict ON predictions(verdict)",
        "CREATE INDEX IF NOT EXISTS idx_predictions_input_params ON predictions USING GIN(input_params)",
        """
        CREATE TABLE IF NOT EXISTS scenarios (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            inputs JSONB NOT NULL,
            outputs JSONB NOT NULL,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_scenarios_created_at ON scenarios(created_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS active_learning_queue (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            compound_name TEXT,
            features JSONB NOT NULL,
            uncertainty_score DOUBLE PRECISION NOT NULL,
            predicted_prob DOUBLE PRECISION NOT NULL,
            priority TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            true_label INTEGER,
            labelled_by TEXT,
            labelled_at TIMESTAMPTZ,
            notes TEXT NOT NULL DEFAULT ''
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_alq_status_prob ON active_learning_queue(status, predicted_prob)",
        """
        CREATE TABLE IF NOT EXISTS raw_bioactivity (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source TEXT NOT NULL,
            compound_smiles TEXT,
            inchikey TEXT,
            endpoint TEXT,
            value DOUBLE PRECISION,
            units TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS training_data (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            inchikey TEXT,
            smiles TEXT,
            toxicity DOUBLE PRECISION,
            bioavailability DOUBLE PRECISION,
            solubility DOUBLE PRECISION,
            binding DOUBLE PRECISION,
            molecular_weight DOUBLE PRECISION,
            label INTEGER,
            source TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_training_data_inchikey ON training_data(inchikey)",
        """
        CREATE TABLE IF NOT EXISTS model_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            version TEXT NOT NULL,
            algorithm TEXT DEFAULT 'stacked_ensemble',
            training_dataset_size INT,
            val_auc FLOAT,
            val_f1 FLOAT,
            val_brier FLOAT,
            artifact_path TEXT NOT NULL,
            sync_metadata JSONB,
            deployed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            deployed_at TIMESTAMPTZ
        )
        """,
        "ALTER TABLE model_versions ADD COLUMN IF NOT EXISTS sync_metadata JSONB",
        "CREATE INDEX IF NOT EXISTS idx_model_versions_created ON model_versions(created_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS drift_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feature_name TEXT NOT NULL,
            kl_divergence DOUBLE PRECISION NOT NULL,
            detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_drift_alerts_detected_at ON drift_alerts(detected_at DESC)",
    ]

    with get_conn() as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()


def execute(sql: str, params: Optional[Iterable[Any]] = None, fetch: str = "none"):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params or ()))
            out = None
            if fetch == "one":
                out = cur.fetchone()
            elif fetch == "all":
                out = cur.fetchall()
            conn.commit()
            return out


def log_prediction(input_params: Dict[str, Any], probability: float, verdict: str, warnings: list[Any]) -> str:
    row = execute(
        """
        INSERT INTO predictions (input_params, probability, verdict, warnings, compound_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        [Json(input_params), float(probability), verdict, Json(warnings or []), input_params.get("compound_name")],
        fetch="one",
    )
    return str(row["id"]) if row else ""


def insert_model_version(payload: Dict[str, Any]) -> Dict[str, Any]:
    row = execute(
        """
        INSERT INTO model_versions (
          version, algorithm, training_dataset_size, val_auc, val_f1, val_brier,
                    artifact_path, sync_metadata, deployed, deployed_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                    %s, CASE WHEN %s THEN NOW() ELSE NULL END)
        RETURNING *
        """,
        [
            payload.get("version"),
            payload.get("algorithm", "stacked_ensemble"),
            payload.get("training_dataset_size"),
            payload.get("val_auc"),
            payload.get("val_f1"),
            payload.get("val_brier"),
            payload.get("artifact_path"),
                        Json(payload.get("sync_metadata") or {}),
            bool(payload.get("deployed", False)),
            bool(payload.get("deployed", False)),
        ],
        fetch="one",
    )
    return dict(row or {})


def fetch_latest_deployed_model() -> Optional[Dict[str, Any]]:
    row = execute(
        "SELECT * FROM model_versions WHERE deployed = TRUE ORDER BY deployed_at DESC NULLS LAST, created_at DESC LIMIT 1",
        fetch="one",
    )
    return dict(row) if row else None


def fetch_all_model_versions() -> list[Dict[str, Any]]:
    rows = execute("SELECT * FROM model_versions ORDER BY created_at DESC", fetch="all") or []
    return [dict(r) for r in rows]


def add_drift_alert(feature_name: str, kl_divergence: float) -> Dict[str, Any]:
    row = execute(
        "INSERT INTO drift_alerts (feature_name, kl_divergence) VALUES (%s, %s) RETURNING *",
        [feature_name, float(kl_divergence)],
        fetch="one",
    )
    return dict(row or {})


def get_drift_alerts(days: int = 30) -> list[Dict[str, Any]]:
    rows = execute(
        "SELECT * FROM drift_alerts WHERE detected_at >= NOW() - (%s || ' days')::interval ORDER BY detected_at DESC",
        [int(days)],
        fetch="all",
    ) or []
    return [dict(r) for r in rows]
