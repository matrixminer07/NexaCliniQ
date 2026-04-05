from __future__ import annotations

from flask import Blueprint, jsonify

from backend.db_pg import execute


analytics_v2_bp = Blueprint("analytics_v2", __name__, url_prefix="/api/v2/analytics")


@analytics_v2_bp.route("/dashboard", methods=["GET"])
def dashboard():
    total = execute("SELECT COUNT(*) AS c FROM predictions", fetch="one") or {"c": 0}
    avg = execute("SELECT AVG(probability) AS a FROM predictions", fetch="one") or {"a": 0.0}
    recent = execute(
        "SELECT id, created_at, probability, verdict, compound_name FROM predictions ORDER BY created_at DESC LIMIT 20",
        fetch="all",
    ) or []

    # Placeholder 5-axis ADMET profile for chart bootstrap; replace with model aggregate when available.
    admet_distribution = [0.52, 0.58, 0.49, 0.47, 0.41]

    return jsonify(
        {
            "stats": {
                "totalPredictions": int(total.get("c") or 0),
                "activeModels": 3,
                "avgConfidence": round(float(avg.get("a") or 0.0) * 100, 2),
            },
            "admet_distribution": admet_distribution,
            "recent": recent,
        }
    )
