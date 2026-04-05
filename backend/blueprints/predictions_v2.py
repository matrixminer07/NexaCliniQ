from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.tasks.prediction_tasks import batch_predict, predict_single_molecule


predictions_v2_bp = Blueprint("predictions_v2", __name__, url_prefix="/api/v2/predictions")


@predictions_v2_bp.route("/predict", methods=["POST"])
def async_predict():
    """Submit asynchronous prediction job.
    ---
    tags:
      - Predictions V2
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - smiles
          properties:
            smiles:
              type: string
              example: "CCO"
            model_version:
              type: string
              default: "v1"
    responses:
      202:
        description: Prediction task submitted
    """
    data = request.get_json(silent=True) or {}
    smiles = data.get("smiles")
    if not smiles:
        return jsonify({"error": "smiles is required"}), 400
    model_version = data.get("model_version", "v1")
    task = predict_single_molecule.delay(smiles, model_version)
    return jsonify(
        {
            "status": "submitted",
            "task_id": task.id,
            "poll_url": f"/api/v2/predictions/status/{task.id}",
        }
    ), 202


@predictions_v2_bp.route("/batch", methods=["POST"])
def async_batch_predict():
    payload = request.get_json(silent=True) or {}
    smiles_list = payload.get("smiles_list") or []
    if not isinstance(smiles_list, list) or not smiles_list:
        return jsonify({"error": "smiles_list must be a non-empty list"}), 400
    task = batch_predict.delay(smiles_list)
    return jsonify({"status": "submitted", "task_id": task.id}), 202


@predictions_v2_bp.route("/status/<task_id>", methods=["GET"])
def get_prediction_status(task_id: str):
    task = predict_single_molecule.AsyncResult(task_id)
    if task.state == "PENDING":
        return jsonify({"status": "pending"}), 200
    if task.state == "SUCCESS":
        return jsonify({"status": "completed", "result": task.result}), 200
    if task.state == "FAILURE":
        return jsonify({"status": "failed", "error": str(task.info)}), 200
    return jsonify({"status": task.state}), 200
