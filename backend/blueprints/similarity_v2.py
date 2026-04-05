from __future__ import annotations

import numpy as np
from flask import Blueprint, jsonify, request


similarity_v2_bp = Blueprint("similarity_v2", __name__, url_prefix="/api/v2")


def _cosine_distance(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
    return float(1.0 - np.dot(a, b) / denom)


@similarity_v2_bp.route("/similarity", methods=["POST"])
def find_similar_molecules():
    payload = request.get_json(silent=True) or {}
    smiles = payload.get("smiles")
    limit = int(payload.get("limit", 10))
    if not smiles:
        return jsonify({"error": "smiles is required"}), 400

    # Endpoint scaffold: wire to db session + GNN embedding service in app integration.
    return jsonify(
        {
            "query_smiles": smiles,
            "limit": limit,
            "items": [],
            "message": "Similarity endpoint scaffolded; connect session + embedding generator.",
        }
    )
