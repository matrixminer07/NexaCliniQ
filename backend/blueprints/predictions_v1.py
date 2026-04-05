from __future__ import annotations

from flask import Blueprint, jsonify, request


predictions_v1_bp = Blueprint("predictions_v1", __name__, url_prefix="/api/v1/predictions")


@predictions_v1_bp.route("/predict", methods=["POST"])
def sync_predict_legacy():
    """Legacy v1 sync predict wrapper.

    This route keeps backward compatibility while v2 tasks are async.
    """
    data = request.get_json(silent=True) or {}
    smiles = data.get("smiles")
    if not smiles:
        return jsonify({"error": "smiles is required"}), 400

    # Legacy payload placeholder; keep non-breaking response shape.
    return jsonify(
        {
            "version": "v1",
            "smiles": smiles,
            "predictions": {"status": "legacy_sync_route"},
            "message": "Use /api/v2/predictions/predict for asynchronous production pipeline.",
        }
    ), 200
