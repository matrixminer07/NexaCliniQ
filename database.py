import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from psycopg2.extras import Json

from backend.db_pg import execute, init_db_schema, insert_model_version


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pharma:password@localhost:5432/pharmanexus")


def _as_row(value: Any) -> Optional[Dict[str, Any]]:
    return cast(Optional[Dict[str, Any]], value)


def _as_rows(value: Any) -> List[Dict[str, Any]]:
    return cast(List[Dict[str, Any]], value or [])


def _iso_or_none(value: Any) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def init_db() -> None:
    init_db_schema()


def log_prediction(data: Dict[str, Any], probability: float, verdict: str, warnings: List[str]) -> str:
    row = _as_row(execute(
        """
        INSERT INTO predictions (input_params, probability, verdict, warnings, compound_name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        [Json(data), float(probability), verdict, Json(warnings or []), data.get("compound_name")],
        fetch="one",
    ))
    return str(row["id"]) if row else ""


def get_history(limit: int = 50, verdict_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    if verdict_filter:
        rows = _as_rows(execute(
            "SELECT * FROM predictions WHERE verdict=%s ORDER BY created_at DESC LIMIT %s",
            [verdict_filter.upper(), min(limit, 1000)],
            fetch="all",
        ))
    else:
        rows = _as_rows(execute(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT %s",
            [min(limit, 1000)],
            fetch="all",
        ))

    out: List[Dict[str, Any]] = []
    for row in rows:
        params = row.get("input_params") or {}
        created_at = row.get("created_at")
        out.append(
            {
                "id": str(row["id"]),
            "timestamp": _iso_or_none(created_at),
                "toxicity": params.get("toxicity"),
                "bioavailability": params.get("bioavailability"),
                "solubility": params.get("solubility"),
                "binding": params.get("binding"),
                "molecular_weight": params.get("molecular_weight"),
                "probability": float(row.get("probability") or 0.0),
                "verdict": row.get("verdict"),
                "warnings": row.get("warnings") or [],
                "tags": row.get("tags") or [],
                "notes": row.get("notes") or "",
                "compound_name": row.get("compound_name") or params.get("compound_name") or "Unnamed",
            }
        )
    return out


def get_stats() -> Dict[str, Any]:
    total_row = _as_row(execute("SELECT COUNT(*) AS c FROM predictions", fetch="one")) or {"c": 0}
    avg_row = _as_row(execute("SELECT AVG(probability) AS a FROM predictions", fetch="one")) or {"a": 0.0}
    verdict_rows = _as_rows(execute("SELECT verdict, COUNT(*) AS count FROM predictions GROUP BY verdict", fetch="all"))
    daily_rows = _as_rows(execute(
        (
            "SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM predictions "
            "WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY day ORDER BY day"
        ),
        fetch="all",
    ))

    total = int(total_row.get("c") or 0)
    vc = {str(v["verdict"]): int(v["count"]) for v in verdict_rows}
    return {
        "total_predictions": total,
        "average_probability": round(float(avg_row.get("a") or 0.0), 3),
        "pass_rate": round(vc.get("PASS", 0) / max(total, 1) * 100, 1),
        "verdict_breakdown": vc,
        "daily_volume_7d": [{"date": str(d["day"]), "count": int(d["cnt"])} for d in daily_rows],
        "model_version": "stacked_ensemble",
        "features_monitored": 5,
        "database_type": "postgresql",
    }


def save_scenario(name: str, inputs: Dict[str, Any], outputs: Dict[str, Any], tags: Optional[List[str]] = None) -> str:
    row = _as_row(execute(
        """
        INSERT INTO scenarios (name, created_at, inputs, outputs, tags)
        VALUES (%s, NOW(), %s::jsonb, %s::jsonb, %s::jsonb)
        RETURNING id
        """,
        [name, json.dumps(inputs), json.dumps(outputs), json.dumps(tags or [])],
        fetch="one",
    ))
    return str(row["id"]) if row else ""


def list_scenarios() -> List[Dict[str, Any]]:
    rows = _as_rows(execute("SELECT * FROM scenarios ORDER BY created_at DESC", fetch="all"))
    return [
        {
            "id": str(r["id"]),
            "name": r.get("name"),
            "created_at": _iso_or_none(r.get("created_at")),
            "inputs": r.get("inputs") or {},
            "outputs": r.get("outputs") or {},
            "tags": r.get("tags") or [],
        }
        for r in rows
    ]


def get_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    row = _as_row(execute("SELECT * FROM scenarios WHERE id::text=%s LIMIT 1", [scenario_id], fetch="one"))
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "name": row.get("name"),
        "created_at": _iso_or_none(row.get("created_at")),
        "inputs": row.get("inputs") or {},
        "outputs": row.get("outputs") or {},
        "tags": row.get("tags") or [],
    }


def delete_scenario(scenario_id: str) -> bool:
    row = execute("DELETE FROM scenarios WHERE id::text=%s RETURNING id", [scenario_id], fetch="one")
    return bool(row)


def save_model_version(version: str, model_type: str, metrics: Dict[str, Any], model_path: str) -> str:
    inserted = insert_model_version(
        {
            "version": version,
            "algorithm": model_type,
            "training_dataset_size": metrics.get("n_train") or metrics.get("training_dataset_size"),
            "val_auc": metrics.get("val_auc") or metrics.get("cv_auc_mean"),
            "val_f1": metrics.get("val_f1") or metrics.get("f1"),
            "val_brier": metrics.get("val_brier"),
            "artifact_path": model_path,
            "deployed": bool(metrics.get("deployed", False)),
        }
    )
    return str(inserted.get("id", ""))


if __name__ == "__main__":
    init_db()
    print("Database schema initialized on", DATABASE_URL)
