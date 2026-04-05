from __future__ import annotations

import os
from typing import Dict, List

from celery import group

from backend.celery_app import celery_app
from backend.ml.gnn.inference import GNNPredictor


_PREDICTOR = None


def _get_predictor() -> GNNPredictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        model_path = os.getenv("GNN_MODEL_PATH", "backend/ta_models/gnn_property.pt")
        _PREDICTOR = GNNPredictor(model_path=model_path, device=os.getenv("GNN_DEVICE", "cpu"))
    return _PREDICTOR


@celery_app.task(bind=True, max_retries=3)
def predict_single_molecule(self, smiles: str, model_version: str = "v1"):
    try:
        predictor = _get_predictor()
        result = predictor.cache.get(predictor._key(smiles))
        if result is None:
            import asyncio

            result = asyncio.run(predictor.predict_properties([smiles]))["results"][0]
        return {
            "smiles": smiles,
            "model_version": model_version,
            "predictions": result.get("predictions", {}),
            "task_id": self.request.id,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def batch_predict(smiles_list: List[str]) -> Dict:
    job = group(predict_single_molecule.s(smiles) for smiles in smiles_list)
    result = job.apply_async()
    return {"job_id": result.id, "total": len(smiles_list)}
